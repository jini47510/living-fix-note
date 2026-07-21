from __future__ import annotations

import json
from pathlib import Path
from typing import Any

POSTS_DIR = Path("posts/ready")


def post_directories() -> list[Path]:
    if not POSTS_DIR.exists():
        return []
    return sorted(path for path in POSTS_DIR.iterdir() if path.is_dir())


def read_post(directory: Path) -> tuple[dict[str, Any], str]:
    metadata_path = directory / "post.json"
    content_path = directory / "content.html"

    if not metadata_path.exists():
        raise ValueError(f"{metadata_path}: 파일이 없습니다.")
    if not content_path.exists():
        raise ValueError(f"{content_path}: 파일이 없습니다.")

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{metadata_path}: JSON 형식 오류 — {exc}") from exc

    content = content_path.read_text(encoding="utf-8").strip()
    return metadata, content


def validate_post(directory: Path, metadata: dict[str, Any], content: str) -> list[str]:
    errors: list[str] = []

    title = metadata.get("title")
    slug = metadata.get("slug")
    labels = metadata.get("labels")
    status = metadata.get("status")

    if not isinstance(title, str) or not title.strip():
        errors.append(f"{directory}: title이 필요합니다.")

    if not isinstance(slug, str) or not slug:
        errors.append(f"{directory}: slug가 필요합니다.")
    elif any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in slug):
        errors.append(f"{directory}: slug는 영문 소문자·숫자·하이픈만 사용할 수 있습니다.")

    if not isinstance(labels, list) or not labels or not all(isinstance(x, str) and x.strip() for x in labels):
        errors.append(f"{directory}: labels 배열에 카테고리를 하나 이상 넣어야 합니다.")

    if status not in {"ready", "published"}:
        errors.append(f"{directory}: status는 ready 또는 published여야 합니다.")

    if len(content) < 500:
        errors.append(f"{directory}: content.html 본문이 너무 짧습니다. 최소 500자입니다.")

    if status == "published" and not metadata.get("blogger_post_id"):
        errors.append(f"{directory}: published 상태에는 blogger_post_id가 필요합니다.")

    return errors


def write_metadata(directory: Path, metadata: dict[str, Any]) -> None:
    path = directory / "post.json"
    path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
