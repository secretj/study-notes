#!/usr/bin/env python3
"""글의 front matter 를 모아 index.json 과 README.md 목차를 만든다.

사용: build_index.py <저장소 루트>

- index.json 은 사이트(study-notes-site)가 목록·태그·연도 분류에 쓴다.
  사이트도 저장할 때 같은 형식으로 고쳐 쓰므로, 키 순서와 들여쓰기를 바꾸지 않는다.
- 주제 이름(topics)은 index.json 에 있는 값을 먼저 쓰고, 없으면 DEFAULT_TOPICS, 그래도 없으면 폴더 이름을 쓴다.
- topics 의 order 는 사이트의 「주제 순서」가 매긴다. 작은 것부터 보여 주고, 같으면 이름순이다. order 가 없으면 0 으로 본다.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_TOPICS = {  # 폴더: (표시 이름, 묶음)
    "go": ("Go 학습", "언어"),
    "java-basics": ("JAVA 기본 지식", "언어"),
    "csharp-basics": ("실무형 C# 기초", "언어"),
    "comp2200-c": ("COMP2200: C 언매니지드 프로그래밍", "언어"),
    "spring": ("Spring 공부", "프레임워크"),
    "spring-advanced": ("스프링 핵심원리 고급편", "프레임워크"),
    "codeigniter4": ("CodeIgniter4", "프레임워크"),
    "ddd": ("도메인 주도 개발 (DDD)", "설계"),
    "traffic-experience": ("트래픽 경험", "설계"),
    "cs": ("CS 지식", "기초"),
    "network": ("네트워크", "기초"),
    "comp3500-algorithm": ("COMP3500: 알고리듬 및 자료구조 (Java)", "기초"),
    "oracle": ("오라클 ORACLE", "기초"),
    "info-processing-engineer": ("정보처리기사", "기초"),
    "github": ("Github", "도구"),
    "jenkins": ("젠킨스 Jenkins", "도구"),
    "project-nplit": ("프로젝트 NPLIT", "프로젝트·업무"),
    "dreamsys-training": ("드림시스 업무 교육", "프로젝트·업무"),
}
GROUP_ORDER = ["언어", "프레임워크", "설계", "기초", "도구", "프로젝트·업무", "기타"]
SKIP_DIRS = {"tools", "_raw", ".git", ".github"}


def parse_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    meta = {}
    if m:
        for line in m.group(1).split("\n"):
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "tags":
                try:
                    meta[k] = [str(t) for t in json.loads(v)] if v.startswith("[") else [t.strip() for t in v.split(",") if t.strip()]
                except json.JSONDecodeError:
                    meta[k] = [t.strip().strip('"\'') for t in v.strip("[]").split(",") if t.strip()]
            elif k == "title" and v.startswith('"'):
                try:
                    meta[k] = json.loads(v)
                except json.JSONDecodeError:
                    meta[k] = v.strip('"')
            else:
                meta[k] = v
    if "title" not in meta:
        h = re.search(r"^# (.+)$", text, re.M)
        if h:
            meta["title"] = h.group(1).strip()
    return meta


def enc(path):
    for a, b in ((" ", "%20"), ("(", "%28"), (")", "%29"), ("#", "%23"), ("<", "%3C"), (">", "%3E")):
        path = path.replace(a, b)
    return path


def collect(root):
    pages = []
    for p in sorted(root.rglob("*.md"), key=lambda p: p.with_suffix("").parts):
        rel = p.relative_to(root)
        if len(rel.parts) < 2 or rel.parts[0] in SKIP_DIRS or rel.parts[0].startswith("."):
            continue
        meta = parse_front_matter(p.read_text(encoding="utf-8"))
        pages.append({
            "path": rel.as_posix(),
            "title": meta.get("title") or p.stem,
            "date": meta.get("date", ""),
            "tags": meta.get("tags", []),
        })
    return pages


def topics_for(root, pages):
    old = {}
    idx = root / "index.json"
    if idx.exists():
        old = json.loads(idx.read_text(encoding="utf-8")).get("topics", {})
    topics = {}
    for folder in sorted({p["path"].split("/")[0] for p in pages}):
        if folder in old:
            topics[folder] = old[folder]
        elif folder in DEFAULT_TOPICS:
            name, group = DEFAULT_TOPICS[folder]
            topics[folder] = {"name": name, "group": group}
        else:
            topics[folder] = {"name": folder, "group": "기타"}
    return topics


def readme(pages, topics):
    by_topic = defaultdict(list)
    for p in pages:
        by_topic[p["path"].split("/")[0]].append(p)
    groups = sorted({t["group"] for t in topics.values()},
                    key=lambda g: GROUP_ORDER.index(g) if g in GROUP_ORDER else len(GROUP_ORDER))
    out = ["# 공부 기록", "",
           "공부하면서 정리한 내용을 모아 두는 저장소예요. 예전에 노션 「꽉 채울거야! 지식 창고」에 쓰던 글을 옮겨 왔고, 새 글은 여기에 바로 써요.",
           "", f"글 {len(pages)}개 · 주제 {len(topics)}개", ""]
    for g in groups:
        out += [f"## {g}", ""]
        for folder, t in sorted(topics.items(), key=lambda kv: (kv[1].get("order", 0), kv[1]["name"])):
            if t["group"] != g:
                continue
            items = by_topic[folder]
            out += ["<details>", f"<summary><b>{t['name']}</b> · {len(items)}개</summary>", ""]
            for p in items:
                depth = len(p["path"].split("/")) - 2
                date = f" <sub>{p['date']}</sub>" if p["date"] else ""
                out.append("  " * depth + f"- [{p['title']}]({enc(p['path'])}){date}")
            out += ["", "</details>", ""]
    tag_count = defaultdict(int)
    year_count = defaultdict(int)
    for p in pages:
        for t in p["tags"]:
            tag_count[t] += 1
        year_count[p["date"][:4] or "날짜 없음"] += 1
    out += ["## 태그", "", " · ".join(f"{t} ({n})" for t, n in sorted(tag_count.items(), key=lambda x: (-x[1], x[0]))), ""]
    out += ["## 연도", "", " · ".join(f"{y} ({n})" for y, n in sorted(year_count.items(), reverse=True)), ""]
    out += ["---", "", "## 정리하는 방식", "",
            "- 주제마다 폴더 하나, 글 하나에 파일 하나예요. 파일 이름은 `NN-제목.md` 예요.",
            "- 글 맨 위 front matter 에 `title`, `date`, `tags` 를 적어요. 사이트의 태그·연도 분류가 이 값을 써요.",
            "- 그림은 각 주제 폴더의 `images/` 에 둬요.",
            "- 노션에서 옮긴 글은 `source` 에 노션 원본 주소가 있어요. 노션에서만 보이는 블록은 ⚠️ 표시로 남겨 뒀어요.",
            "- `index.json` 과 이 README 는 `python3 tools/build_index.py .` 로 다시 만들어요. push 하면 GitHub Actions 가 알아서 돌려요.", ""]
    return "\n".join(out)


def main():
    root = Path(sys.argv[1])
    pages = collect(root)
    topics = topics_for(root, pages)
    index = {"topics": topics, "pages": pages}
    (root / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "README.md").write_text(readme(pages, topics), encoding="utf-8")
    print(f"index.json, README.md: {len(pages)} pages, {len(topics)} topics")


if __name__ == "__main__":
    main()
