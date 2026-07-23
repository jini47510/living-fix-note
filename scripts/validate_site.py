from __future__ import annotations

import json
from pathlib import Path

PAGES_DIR = Path("site/pages")
CLEANUP_PATH = Path("site/cleanup.json")


def main() -> None:
    errors: list[str] = []
    page_metadata = sorted(PAGES_DIR.glob("*.json"))

    if not page_metadata:
        errors.append("site/pages에 페이지 메타데이터가 없습니다.")

    for metadata_path in page_metadata:
        content_path = metadata_path.with_suffix(".html")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{metadata_path}: JSON을 읽을 수 없습니다 — {exc}")
            continue

        title = metadata.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{metadata_path}: title이 필요합니다.")

        if not content_path.exists():
            errors.append(f"{content_path}: 페이지 본문 파일이 없습니다.")
            continue

        content = content_path.read_text(encoding="utf-8").strip()
        if len(content) < 500:
            errors.append(f"{content_path}: 본문이 너무 짧습니다. 최소 500자입니다.")
        if "<script" in content.lower():
            errors.append(f"{content_path}: script 태그는 사용할 수 없습니다.")

    try:
        cleanup = json.loads(CLEANUP_PATH.read_text(encoding="utf-8"))
        for item in cleanup.get("trash_posts", []):
            if not str(item.get("blogger_post_id", "")).isdigit():
                errors.append(
                    f"{CLEANUP_PATH}: blogger_post_id는 숫자로 된 문자열이어야 합니다."
                )
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{CLEANUP_PATH}: 정리 설정을 읽을 수 없습니다 — {exc}")

    if errors:
        print("사이트 페이지 검증 실패:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{len(page_metadata)}개 필수 페이지 검증 완료.")


if __name__ == "__main__":
    main()
