"""JSON 규칙 파일 경로 해석.

예전 VS Code 워크스페이스는 core/ + data/en_data + data/common 구조였고,
현재 배포본은 모든 JSON이 프로젝트 루트에 있다. 둘 다 찾는다.
"""

from __future__ import annotations

import os
from typing import Iterable, List, Optional


def project_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _unique(paths: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for path in paths:
        normalized = os.path.normpath(path)
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out


def candidate_dirs(base_dir: Optional[str] = None) -> List[str]:
    root = project_dir()
    extras: List[str] = []
    if base_dir:
        extras.extend(
            [
                base_dir,
                os.path.join(base_dir, "data"),
                os.path.join(base_dir, "en_data"),
                os.path.join(base_dir, "common"),
                os.path.join(base_dir, "data", "en_data"),
                os.path.join(base_dir, "data", "common"),
            ]
        )
    extras.extend(
        [
            root,
            os.path.join(root, "data"),
            os.path.join(root, "en_data"),
            os.path.join(root, "common"),
            os.path.join(root, "data", "en_data"),
            os.path.join(root, "data", "common"),
        ]
    )
    return _unique(extras)


def find_data_file(filename: str, base_dir: Optional[str] = None) -> str:
    for directory in candidate_dirs(base_dir):
        path = os.path.join(directory, filename)
        if os.path.isfile(path):
            return path
    searched = ", ".join(candidate_dirs(base_dir))
    raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {filename} (검색: {searched})")


def resolve_data_root(base_dir: Optional[str] = None) -> str:
    markers = ("ko.json", "lexicon_en.json", "numbers.json")
    for directory in candidate_dirs(base_dir):
        if any(os.path.isfile(os.path.join(directory, name)) for name in markers):
            return directory
    return project_dir()
