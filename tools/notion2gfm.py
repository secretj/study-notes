#!/usr/bin/env python3
"""노션 원문(Notion-flavored Markdown)을 GitHub 마크다운으로 바꾼다.

사용: notion2gfm.py <raw 폴더> <출력 폴더>
  raw 폴더:  _raw/<주제>/<NN-제목>.notion.md (+ images/, 하위 폴더)
  출력 폴더: <주제>/<NN-제목>.md (+ images/)

- 노션 페이지 사이 링크(mention, page)는 같은 저장소 안의 상대 경로로 바꾼다.
- 노션 이미지(notion-file-block://<블록ID>/...)는 images/<블록ID>.* 로 바꾼다.
- 옮길 수 없는 블록(<unknown>)은 경고 인용문으로 남긴다.
"""
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

CONTAINERS = ["callout", "toggle", "details", "quote", "columns", "column", "ul", "ol",
              "li", "table", "tabs", "tab", "synced-block", "synced-block-reference",
              "meeting-notes", "p", "todo", "h1", "h2", "h3", "h4"]
HEAD = {"h1": "#", "h2": "##", "h3": "###", "h4": "####"}
PAGE_ID = re.compile(r"([0-9a-f]{32})|([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")


def enc(path):
    """마크다운 링크에서 깨지는 문자만 인코딩한다 (한글은 그대로 둔다)."""
    for a, b in ((" ", "%20"), ("(", "%28"), (")", "%29"), ("#", "%23"), ("<", "%3C"), (">", "%3E")):
        path = path.replace(a, b)
    return path


def norm_id(s):
    m = PAGE_ID.search(s.replace("-", "") if s else "")
    return m.group(0).replace("-", "") if m else None


def attrs_of(tag_text):
    return dict(re.findall(r'([\w:-]+)="([^"]*)"', tag_text))


class Ctx:
    def __init__(self, src_file, out_file, out_root, page_map, img_dirs):
        self.src, self.out, self.root = src_file, out_file, out_root
        self.page_map, self.img_dirs = page_map, img_dirs
        self.warn = []

    def rel(self, target):
        return enc(os.path.relpath(target, self.out.parent).replace(os.sep, "/"))

    def link_for(self, url):
        pid = norm_id(url.split("?")[0].split("#")[0]) if url else None
        if pid and pid in self.page_map:
            return self.rel(self.page_map[pid])
        return url

    def image_for(self, src):
        if src.startswith("notion-file-block://"):
            bid = src[len("notion-file-block://"):].split("/")[0]
            for d in self.img_dirs:
                hits = sorted(d.glob(bid + ".*"))
                if hits:
                    return self.rel(hits[0])
            self.warn.append(f"이미지 없음: {bid}")
            return src
        if src.startswith("http"):
            h = hashlib.sha1(src.encode()).hexdigest()[:12]
            for d in self.img_dirs:
                hits = sorted(d.glob(f"ext-{h}.*"))
                if hits:
                    return self.rel(hits[0])
            if "X-Amz-" in src:
                self.warn.append("만료되는 S3 이미지 주소가 남음")
        return src


def find_close(lines, i, tag):
    depth = 0
    open_re = re.compile(rf"<{tag}(\s[^>]*)?>")
    close_re = re.compile(rf"</{tag}>")
    for j in range(i, len(lines)):
        s = lines[j]
        depth += len(open_re.findall(s)) - len(re.findall(rf"<{tag}(\s[^>]*)?/>", s))
        depth -= len(close_re.findall(s))
        if depth <= 0:
            return j
    return len(lines) - 1


def dedent(lines):
    ind = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    n = min(ind) if ind else 0
    return [l[n:] for l in lines]


def convert_lines(lines, ctx):
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        indent = line[: len(line) - len(line.lstrip())]
        if s.startswith("```") or s.startswith("~~~"):
            fence = re.match(r"^(`{3,}|~{3,})", s).group(1)
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith(fence):
                j += 1
            block = [l[len(indent):] if l.startswith(indent) else l for l in lines[i:j + 1]]
            lang = block[0].strip()[len(fence):].strip()
            if lang == "plain text":
                block[0] = fence
            out.extend(indent + b for b in block)
            i = j + 1
            continue
        m = re.match(r"^<([a-z0-9-]+)(\s[^>]*)?>(.*)$", s)
        if m and m.group(1) in CONTAINERS and not s.endswith("/>"):
            tag, at, rest = m.group(1), attrs_of(m.group(2) or ""), m.group(3)
            # 한 줄에 열고 닫는 경우
            if re.search(rf"</{tag}>\s*$", rest):
                inner = [re.sub(rf"</{tag}>\s*$", "", rest)]
                j = i
            else:
                j = find_close(lines, i, tag)
                inner = ([rest] if rest.strip() else []) + lines[i + 1:j]
                last = lines[j]
                tail = re.sub(rf"</{tag}>\s*$", "", last.strip())
                if j != i and tail.strip():
                    inner.append(tail)
            inner = dedent(inner)
            rendered = render(tag, at, inner, ctx)
            out.extend((indent + r) if r else "" for r in rendered)
            i = j + 1
            continue
        out.append(line)
        i += 1
    return out


def body_and_title(inner, ctx):
    conv = convert_lines(inner, ctx)
    while conv and not conv[0].strip():
        conv.pop(0)
    title = conv[0] if conv else ""
    rest = conv[1:]
    while rest and not rest[0].strip():
        rest.pop(0)
    return title, rest


def render(tag, at, inner, ctx):
    if tag in ("columns", "column", "synced-block", "synced-block-reference", "meeting-notes", "tabs"):
        return convert_lines(inner, ctx) + [""]
    if tag == "p":
        return [" ".join(l.strip() for l in convert_lines(inner, ctx) if l.strip()), ""]
    if tag in HEAD:
        return [HEAD[tag] + " " + " ".join(l.strip() for l in inner if l.strip()), ""]
    if tag == "tab":
        title, rest = body_and_title(inner, ctx)
        return [f"**{title.strip()}**", ""] + rest + [""]
    if tag in ("callout", "quote"):
        conv = convert_lines(inner, ctx)
        while conv and not conv[-1].strip():
            conv.pop()
        icon = at.get("icon", "")
        icon = icon if icon and not icon.startswith(("/", "http")) else ("💡" if tag == "callout" else "")
        res = []
        for k, l in enumerate(conv):
            pre = f"{icon} " if k == 0 and icon else ""
            res.append(("> " + pre + l).rstrip() if l.strip() or k == 0 else ">")
        return res + [""]
    if tag in ("toggle", "details"):
        if tag == "details":
            joined = "\n".join(inner)
            sm = re.search(r"<summary>(.*?)</summary>", joined, re.S)
            title = sm.group(1).strip() if sm else "더 보기"
            rest = convert_lines(re.sub(r"<summary>.*?</summary>", "", joined, count=1, flags=re.S).split("\n"), ctx)
        else:
            title, rest = body_and_title(inner, ctx)
        title = md_inline_to_html(inline(title.strip(), ctx))
        if at.get("heading") in HEAD:
            title = f"<b>{title}</b>"
        return ["<details>", f"<summary>{title}</summary>", ""] + rest + ["", "</details>", ""]
    if tag in ("ul", "ol"):
        res = convert_lines(inner, ctx)
        if tag == "ol":
            n = 0
            fixed = []
            for l in res:
                if l.startswith("- "):
                    n += 1
                    fixed.append(f"{n}. " + l[2:])
                elif l.startswith("  ") and n:
                    fixed.append(" " + l)
                else:
                    fixed.append(l)
            res = fixed
        return res + [""]
    if tag == "li":
        conv = convert_lines(inner, ctx)
        while conv and not conv[0].strip():
            conv.pop(0)
        while conv and not conv[-1].strip():
            conv.pop()
        if not conv:
            return ["- "]
        return ["- " + conv[0]] + [("  " + l) if l.strip() else "" for l in conv[1:]]
    if tag == "todo":
        mark = "x" if at.get("checked") == "true" else " "
        text = " ".join(l.strip() for l in convert_lines(inner, ctx) if l.strip())
        return [f"- [{mark}] {text}"]
    if tag == "table":
        joined = "\n".join(inner)
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", joined, re.S)
        table = []
        for r in rows:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)
            cells = [c.strip().replace("\n", "<br>").replace("|", "\\|") for c in cells]
            table.append(cells)
        if not table:
            return inner
        width = max(len(r) for r in table)
        lines = []
        for k, r in enumerate(table):
            r = r + [""] * (width - len(r))
            lines.append("| " + " | ".join(r) + " |")
            if k == 0:
                lines.append("|" + "---|" * width)
        return lines + [""]
    return inner


def md_inline_to_html(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def inline(s, ctx):
    # 블록형 자기 닫힘 태그
    s = re.sub(r"<table-of-contents[^>]*/>", "", s)
    s = re.sub(r"<empty-block\s*/>", "", s)
    s = re.sub(r"<p\s*/>", "", s)

    def unknown(m):
        a = attrs_of(m.group(0))
        return f"> ⚠️ 노션에서만 보이는 블록({a.get('alt', '알 수 없음')})이라 옮기지 못했어요. [노션 원본]({a.get('url', '')})"
    s = re.sub(r"<unknown[^>]*/>", unknown, s)

    def media(m):
        tag, a, cap = m.group(1), attrs_of(m.group(2)), (m.group(4) or "").strip()
        src = a.get("source") or a.get("url") or ""
        if tag == "image":
            cap = re.sub(r"<[^>]+>", "", cap).replace("[", "").replace("]", "")
            return f"![{cap}]({ctx.image_for(src)})"
        target = ctx.image_for(src) if src.startswith("notion-file-block://") else src
        label = cap or a.get("name") or src
        return f"[{tag}: {label}]({target})"
    s = re.sub(r"<(image|file|pdf|video|audio|bookmark|embed)(\s[^>]*?)(/>|>(.*?)</\1>)", media, s, flags=re.S)
    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda m: f"![{m.group(1)}]({ctx.image_for(m.group(2))})", s)

    def pg(m):
        a, title = attrs_of(m.group(2)), (m.group(4) or "").strip()
        icon = "📄" if m.group(1) == "page" else "🗂"
        return f"{icon} [{title or '하위 페이지'}]({ctx.link_for(a.get('url', ''))})"
    s = re.sub(r"<(page|database)(\s[^>]*?)(/>|>(.*?)</\1>)", pg, s, flags=re.S)

    def mention(m):
        a, label = attrs_of(m.group(1)), (m.group(3) or "").strip()
        url = a.get("url", "")
        if url.startswith("user://"):
            return label or "@사용자"
        return f"[{label or '링크'}]({ctx.link_for(url)})"
    s = re.sub(r"<mention(\s[^>]*?)(/>|>(.*?)</mention>)", mention, s, flags=re.S)
    s = re.sub(r'<mention-(?:page|database)\s+url="([^"]*)"\s*>(.*?)</mention-(?:page|database)>',
               lambda m: f"[{m.group(2)}]({ctx.link_for(m.group(1))})", s)
    s = re.sub(r"<date([^>]*)/>", lambda m: attrs_of(m.group(1)).get("start", ""), s)
    s = re.sub(r"<link-preview([^>]*)/>", lambda m: attrs_of(m.group(1)).get("url", ""), s)
    s = re.sub(r"<equation[^>]*>(.*?)</equation>", r"\n$$\n\1\n$$\n", s, flags=re.S)
    # 서식
    for _ in range(3):
        s = re.sub(r"<span(\s[^>]*)?>(.*?)</span>", r"\2", s, flags=re.S)
    # 굵게 끝에 붙은 줄바꿈은 밖으로 뺀다 (GitHub 는 **…<br>** 를 굵게로 못 읽음)
    s = re.sub(r"((?:<br\s*/?>)+)(\s*)</b>", r"</b>\1\2", s)
    s = re.sub(r"<b>(\s*)((?:<br\s*/?>)+)", r"\1\2<b>", s)
    s = re.sub(r"<b>(\s*)(.*?)(\s*)</b>", lambda m: f"{m.group(1)}**{m.group(2)}**{m.group(3)}" if m.group(2) else m.group(1), s, flags=re.S)
    s = re.sub(r"<i>(\s*)(.*?)(\s*)</i>", lambda m: f"{m.group(1)}*{m.group(2)}*{m.group(3)}" if m.group(2) else m.group(1), s, flags=re.S)
    s = re.sub(r"<s>(.*?)</s>", r"~~\1~~", s, flags=re.S)
    s = re.sub(r"<u>(.*?)</u>", r"<ins>\1</ins>", s, flags=re.S)
    s = re.sub(r"<br\s*/?>", "<br>", s)
    s = re.sub(r'\s*\{color="[^"]*"\}\s*$', "", s, flags=re.M)
    s = re.sub(r"^(\s*)<li[^>]*>\s*$", r"\1", s, flags=re.M)
    return s


def convert_text(text, ctx):
    # 코드 블록은 인라인 변환에서 보호
    lines = convert_lines(text.split("\n"), ctx)
    out, buf, in_code, fence = [], [], False, ""
    for l in lines:
        st = l.strip()
        if not in_code and (st.startswith("```") or st.startswith("~~~")):
            out.append(inline("\n".join(buf), ctx))
            buf = []
            in_code, fence = True, re.match(r"^(`{3,}|~{3,})", st).group(1)
            out.append(l)
            continue
        if in_code:
            out.append(l)
            if st.startswith(fence) and st.strip("`~") == "":
                in_code = False
            continue
        buf.append(l)
    out.append(inline("\n".join(buf), ctx))
    text = "\n".join(out)
    text = re.sub(r"[ \t]+\n", lambda m: "  \n" if m.group(0).startswith("  ") else "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


# 노션에서 대소문자만 다르게 쓴 태그를 하나로 모은다
TAG_ALIASES = {"spring": "Spring", "java": "JAVA", "cs": "CS", "network": "네트워크", "c#": "C#",
               "github": "GitHub", "mysql": "MySQL", "oracle": "ORACLE", "pocu": "POCU"}


def parse_tags(v):
    v = v.strip().strip("[]")
    out = []
    for t in v.split(","):
        t = t.strip().strip('"').strip("'").strip()
        t = TAG_ALIASES.get(t.lower(), t)
        if t and t not in out:
            out.append(t)
    return out


def front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, text[m.end():]


def main():
    raw, out = Path(sys.argv[1]), Path(sys.argv[2])
    files = sorted(raw.rglob("*.notion.md"))
    page_map, metas = {}, {}
    for f in files:
        meta, _ = front_matter(f.read_text(encoding="utf-8"))
        target = out / f.relative_to(raw).with_suffix("").with_suffix(".md")
        metas[f] = (meta, target)
        pid = norm_id(meta.get("notion_url", ""))
        if pid:
            page_map[pid] = target
    if (raw / "images").exists():
        shutil.copytree(raw / "images", out / "images", dirs_exist_ok=True)
    img_dirs = [out / "images"]
    metas_by_url = {norm_id(m.get("notion_url", "")): m for m, _ in metas.values() if m.get("notion_url")}
    warns = 0
    for f in files:
        meta, target = metas[f]
        _, body = front_matter(f.read_text(encoding="utf-8"))
        ctx = Ctx(f, target, out, page_map, img_dirs)
        md = convert_text(body, ctx)
        title = meta.get("title", f.stem).strip().strip('"')
        created, tags = meta.get("created", ""), parse_tags(meta.get("tags", ""))
        parent = metas_by_url.get(norm_id(meta.get("parent", "")) or "")
        if parent:  # 하위 페이지는 날짜·태그가 없으면 부모 것을 쓴다
            created = created or parent.get("created", "")
            tags = tags or parse_tags(parent.get("tags", ""))
        fm = ["---", f"title: {json.dumps(title, ensure_ascii=False)}"]
        if created:
            fm.append(f"date: {created[:10]}")
        fm.append(f"tags: {json.dumps(tags, ensure_ascii=False)}")
        if meta.get("notion_url"):
            fm.append(f"source: {meta['notion_url']}")
        fm += ["---", "", f"# {title}", ""]
        head = fm
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(head) + "\n" + md, encoding="utf-8")
        for w in sorted(set(ctx.warn)):
            warns += 1
            print(f"WARN {target.relative_to(out)}: {w}", file=sys.stderr)
    print(f"{out}: {len(files)} pages, {warns} warnings")


if __name__ == "__main__":
    main()
