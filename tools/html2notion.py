#!/usr/bin/env python3
"""기술 메모 body.html(#memo) → Notion-flavored Markdown.

사용: html2notion.py <body.html> [--wiki-base URL]  → stdout
위키 내부 링크(/confluence/...)는 --wiki-base 를 붙여 절대 주소로 바꾼다.
SVG 그림은 옮기지 않고 .claim / .notes 텍스트만 남긴다.
"""
import argparse
import html
import re
import sys
from html.parser import HTMLParser

VOID = {"br", "img", "hr", "meta", "input", "col"}


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent, self.kids = tag, dict(attrs), parent, []

    @property
    def cls(self):
        return set((self.attrs.get("class") or "").split())


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", [])
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.kids.append(data)


def text_of(n):
    return "".join(k if isinstance(k, str) else text_of(k) for k in n.kids)


class Conv:
    def __init__(self, wiki_base):
        self.wiki = wiki_base.rstrip("/")

    # ---------- inline ----------
    def inline(self, n, in_table=False):
        out = []
        for k in n.kids:
            if isinstance(k, str):
                t = re.sub(r"\s+", " ", k)
                t = t.replace("<", "&lt;").replace(">", "&gt;")
                out.append(t)
                continue
            if k.tag == "code":
                c = text_of(k)
                tick = "``" if "`" in c else "`"
                pad = " " if c.startswith("`") or c.endswith("`") else ""
                out.append(f"{tick}{pad}{c}{pad}{tick}")
            elif k.tag in ("b", "strong"):
                inner = self.inline(k, in_table).strip()
                if "v" in k.cls:  # 좋다/보통/나쁘다 배지
                    color = {"good": "green", "mid": "yellow", "bad": "red"}.get(
                        next(iter(k.cls - {"v"}), ""), "default")
                    out.append(f'<span color="{color}">**{inner}**</span>')
                else:
                    out.append(f"**{inner}**" if inner else "")
            elif k.tag == "a":
                href = k.attrs.get("href", "")
                if href.startswith("/"):
                    href = self.wiki + href
                label = self.inline(k, in_table).strip().replace("[", "\\[").replace("]", "\\]")
                out.append(f"[{label}]({href})")
            elif k.tag == "br":
                out.append("<br />" if in_table else " ")
            elif k.tag == "span" and "sub2" in k.cls:
                out.append(("<br />" if in_table else " — ") + self.inline(k, in_table).strip())
            elif k.tag == "i":
                continue
            else:
                out.append(self.inline(k, in_table))
        s = "".join(out)
        if in_table:
            s = s.replace("|", "\\|")
        return re.sub(r" {2,}", " ", s)

    # ---------- block ----------
    def blocks(self, n):
        out = []
        for k in n.kids:
            if isinstance(k, str):
                if k.strip():
                    out.append(k.strip())
                continue
            r = self.block(k)
            if r:
                out.append(r)
        return "\n\n".join(out)

    def block(self, n):
        c, t = n.cls, n.tag
        if t in ("style", "svg", "script") or "toc-mobile" in c or "legend" in c or "mxlegend" in c:
            return ""
        if t == "header":
            return self.header(n)
        if t == "section":
            return self.section(n)
        if t == "footer":
            return f'<span color="gray">{self.inline(n).strip()}</span>'
        if "sec-head" in c:
            return ""
        if t in ("h2", "h3", "h4"):
            level = {"h2": "##", "h3": "###", "h4": "####"}[t]
            return f"{level} {self.inline(n).strip()}"
        if t == "p":
            s = self.inline(n).strip()
            return s or ""
        if t in ("ul", "ol"):
            mark = "-" if t == "ul" else "1."
            items = [f"{mark} {self.inline(li).strip()}" for li in n.kids
                     if not isinstance(li, str) and li.tag == "li"]
            return "\n".join(items)
        if t == "pre":
            code = text_of(n).rstrip("\n")
            return f"```{guess_lang(code)}\n{code}\n```"
        if "essence" in c:
            return f'<callout icon="💡" color="blue_bg">\n{self.inline(n).strip()}\n</callout>'
        if "verdict" in c:
            return self.verdict(n)
        if "mx" in c:
            return self.table(n)
        if "fig" in c:
            return self.fig(n)
        if "steps" in c:
            return self.steps(n)
        if t == "details":
            return self.details(n)
        return self.blocks(n)

    def header(self, n):
        parts = []
        for k in n.kids:
            if isinstance(k, str):
                continue
            if "eyebrow" in k.cls:
                parts.append(f'<span color="blue">**{self.inline(k).strip()}**</span>')
            elif k.tag == "h1":
                continue  # 제목은 페이지 title 로
            elif "lead" in k.cls:
                parts.append(self.inline(k).strip())
            elif "meta-table" in k.cls:
                rows = []
                for r in k.kids:
                    if isinstance(r, str):
                        continue
                    dt = next(x for x in r.kids if not isinstance(x, str) and x.tag == "dt")
                    dd = next(x for x in r.kids if not isinstance(x, str) and x.tag == "dd")
                    rows.append(f"| {self.inline(dt, True).strip()} | {self.inline(dd, True).strip()} |")
                parts.append("| 항목 | 내용 |\n|---|---|\n" + "\n".join(rows))
        parts.append("<table-of-contents color=\"gray\" />")
        return "\n\n".join(parts)

    def section(self, n):
        head = next((k for k in n.kids if not isinstance(k, str) and "sec-head" in k.cls), None)
        title = ""
        if head:
            chip = next((k for k in head.kids if not isinstance(k, str) and "chip" in k.cls), None)
            h2 = next((k for k in head.kids if not isinstance(k, str) and k.tag == "h2"), None)
            num = text_of(chip).strip() if chip else ""
            title = f"## {num}. {self.inline(h2).strip()}" if h2 else ""
        body = self.blocks(n)
        return f"{title}\n\n{body}".strip()

    def verdict(self, n):
        cols = []
        for card in n.kids:
            if isinstance(card, str):
                continue
            lbl = pick = desc = ""
            for k in card.kids:
                if isinstance(k, str):
                    continue
                if "lbl" in k.cls:
                    lbl = self.inline(k).strip()
                elif "pick" in k.cls:
                    pick = self.inline(k).strip()
                elif k.tag == "p":
                    desc = self.inline(k).strip()
            cols.append(f'<column>\n<callout icon="📌" color="gray_bg">\n<span color="gray">{lbl}</span>\\\n**{pick}**\\\n{desc}\n</callout>\n</column>')
        return "<columns>\n" + "\n".join(cols) + "\n</columns>"

    def table(self, n):
        rows = [r for r in n.kids if not isinstance(r, str) and "row" in r.cls]
        lines = []
        for i, r in enumerate(rows):
            cells = [self.inline(c, True).strip() for c in r.kids if not isinstance(c, str)]
            lines.append("| " + " | ".join(cells) + " |")
            if i == 0:
                lines.append("|" + "---|" * len(cells))
        return "\n".join(lines)

    def fig(self, n):
        parts = []
        for k in n.kids:
            if isinstance(k, str):
                continue
            if "claim" in k.cls:
                parts.append(f'<callout icon="🖼️" color="gray_bg">\n{self.inline(k).strip()}\n</callout>')
            elif "notes" in k.cls:
                items = []
                for li in self._lis(k):
                    items.append(li)
                parts.append("\n".join(items))
        return "\n\n".join(p for p in parts if p)

    def _lis(self, n):
        out = []
        for k in n.kids:
            if isinstance(k, str):
                continue
            if k.tag == "li":
                spans = [x for x in k.kids if not isinstance(x, str)]
                num = text_of(spans[0]).strip() if spans else ""
                body = self.inline(spans[-1]).strip() if spans else ""
                out.append(f"{num}. {body}")
            else:
                out.extend(self._lis(k))
        return out

    def steps(self, n):
        out = []
        for i, st in enumerate([s for s in n.kids if not isinstance(s, str)], 1):
            inner = next((x for x in st.kids if not isinstance(x, str)), st)
            h3 = next((x for x in inner.kids if not isinstance(x, str) and x.tag == "h3"), None)
            rest = Node("div", [])
            rest.kids = [x for x in inner.kids if x is not h3]
            title = self.inline(h3).strip() if h3 else ""
            body = self.blocks(rest)
            out.append(f"#### {i}. {title}" + (f"\n\n{body}" if body else ""))
        return "\n\n".join(out)

    def details(self, n):
        summ = next((x for x in n.kids if not isinstance(x, str) and x.tag == "summary"), None)
        rest = Node("div", [])
        rest.kids = [x for x in n.kids if x is not summ]
        label = self.inline(summ).strip() if summ else "더 보기"
        return f"<toggle>\n{label}\n\n{self.blocks(rest)}\n</toggle>"


def guess_lang(code):
    if "[Unit]" in code or "[Service]" in code:
        return "ini"
    if re.search(r"^\s*(spring|server):", code, re.M):
        return "yaml"
    if re.search(r"^\$ |systemctl |^sudo ", code, re.M):
        return "bash"
    if re.search(r"\bfunc\b|:=|\bpackage\b", code):
        return "go"
    if "@Transactional" in code or "public class" in code:
        return "java"
    if "<?php" in code or re.search(r"\$\w+\s*=", code):
        return "php"
    return "plain text"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("body")
    ap.add_argument("--wiki-base", default="https://wiki.mailplug.co.kr")
    a = ap.parse_args()
    t = Tree()
    t.feed(open(a.body, encoding="utf-8").read())
    memo = t.root
    conv = Conv(a.wiki_base)
    md = conv.blocks(memo)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    sys.stdout.write(md)


if __name__ == "__main__":
    main()
