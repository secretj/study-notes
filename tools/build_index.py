#!/usr/bin/env python3
"""주제 폴더들을 훑어 README.md 목차를 만든다. 사용: build_index.py <저장소 루트>"""
import sys
from pathlib import Path

TOPICS = [  # (폴더, 표시 이름, 묶음)
    ("go", "Go 학습", "언어"),
    ("java-basics", "JAVA 기본 지식", "언어"),
    ("csharp-basics", "실무형 C# 기초", "언어"),
    ("comp2200-c", "COMP2200: C 언매니지드 프로그래밍", "언어"),
    ("spring", "Spring 공부", "프레임워크"),
    ("spring-advanced", "스프링 핵심원리 고급편", "프레임워크"),
    ("codeigniter4", "CodeIgniter4", "프레임워크"),
    ("ddd", "도메인 주도 개발 (DDD)", "설계"),
    ("traffic-experience", "트래픽 경험", "설계"),
    ("cs", "CS 지식", "기초"),
    ("network", "네트워크", "기초"),
    ("comp3500-algorithm", "COMP3500: 알고리듬 및 자료구조 (Java)", "기초"),
    ("oracle", "오라클 ORACLE", "기초"),
    ("info-processing-engineer", "정보처리기사", "기초"),
    ("github", "Github", "도구"),
    ("jenkins", "젠킨스 Jenkins", "도구"),
    ("project-nplit", "프로젝트 NPLIT", "프로젝트·업무"),
    ("dreamsys-training", "드림시스 업무 교육", "프로젝트·업무"),
]


def title_of(md):
    for line in md.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return md.stem


def link(p, root):
    path = str(p.relative_to(root))
    for a, b in ((" ", "%20"), ("(", "%28"), (")", "%29"), ("#", "%23"), ("<", "%3C"), (">", "%3E")):
        path = path.replace(a, b)
    return path


def main():
    root = Path(sys.argv[1])
    out = ["# 공부 기록", "",
           "공부하면서 정리한 내용을 모아 두는 저장소예요. 예전에 노션 「꽉 채울거야! 지식 창고」에 쓰던 글을 옮겨 왔고, 새 글은 여기에 바로 써요.", ""]
    total = 0
    group = None
    for folder, name, grp in TOPICS:
        d = root / folder
        pages = sorted((p for p in d.rglob("*.md") if p.name != "README.md"), key=lambda p: p.with_suffix("").parts) if d.exists() else []
        if not pages:
            continue
        if grp != group:
            out += [f"## {grp}", ""]
            group = grp
        out += [f"<details>", f"<summary><b>{name}</b> · {len(pages)}개</summary>", ""]
        for p in pages:
            depth = len(p.relative_to(d).parts) - 1
            out.append("  " * depth + f"- [{title_of(p)}]({link(p, root)})")
        out += ["", "</details>", ""]
        total += len(pages)
    known = {t[0] for t in TOPICS}
    extra = [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith((".", "_")) and d.name not in known | {"tools"}]
    if extra:
        print("README 에 없는 폴더:", extra, file=sys.stderr)
    out += ["---", "", "## 정리하는 방식", "",
            "- 주제마다 폴더 하나, 글 하나에 파일 하나예요. 파일 이름은 `NN-제목.md` 예요.",
            "- 그림은 각 주제 폴더의 `images/` 에 둬요.",
            "- 노션에서 옮긴 글 맨 위에는 노션 원본 링크가 있어요. 노션에서만 보이는 블록은 ⚠️ 표시로 남겨 뒀어요.",
            "- 새 글을 추가하면 `python3 tools/build_index.py .` 로 이 목차를 다시 만들어요.", ""]
    (root / "README.md").write_text("\n".join(out), encoding="utf-8")
    print(f"README.md: {total} pages")


if __name__ == "__main__":
    main()
