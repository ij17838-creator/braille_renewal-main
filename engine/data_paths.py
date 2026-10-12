"""JSON 규칙 파일 경로 해석.

JSON은 data/ 아래에 과목별로 나뉘어 있다.
  data/ko          한글 점자 규칙·어휘
  data/en          영어(UEB) 점자 규칙·어휘
  data/common      한/영 공통(숫자)
  data/curriculum  단원표·퀴즈 문제은행
예전 구조(루트, data/en_data 등)도 함께 찾는다.
"""

from __future__ import annotations

import os
from typing import Iterable, List, Optional


DATA_SUBDIRS = ("ko", "en", "common", "curriculum")


def project_dir() -> str:
    """저장소 루트 (engine/ 의 상위 폴더)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    extras.extend(os.path.join(root, "data", sub) for sub in DATA_SUBDIRS)
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
