#!/bin/bash
# _raw/<주제>/ 의 노션 원문(저장소에 안 올림)을 <주제>/ 마크다운으로 덮어쓰고 README 목차를 갱신한다.
# 이미 있는 다른 글은 지우지 않는다. 노션에서 옮길 때만 쓰는 도구다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
for d in _raw/*/; do
  name="$(basename "$d")"
  python3 tools/notion2gfm.py "_raw/$name" "$name"
done
python3 tools/build_index.py "$ROOT"
