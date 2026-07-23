from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from publish_changed import obtain_access_token, require_env

PAGES_DIR = Path("site/pages")
CLEANUP_PATH = Path("site/cleanup.json")


def api_request(
    url: str,
    *,
    method: str = "GET",
    access_token: str,
    body: dict[str, Any] | None = None,
    ignore_not_found: bool = False,
) -> dict[str, Any]:
    data = None
    headers = {"Authorization": f"Bearer {access_token}"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    request = urllib.request.Request(
        url,
        method=method,
        headers=headers,
        data=data,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
            return json.loads(payload.decode("utf-8")) if payload else {}
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        if ignore_not_found and exc.code in {404, 410}:
            return {}
        raise RuntimeError(
            f"Google API 오류 {exc.code}: {response_body}"
        ) from exc


def list_pages(blog_id: str, access_token: str) -> list[dict[str, Any]]:
    endpoint = (
        f"https://www.googleapis.com/blogger/v3/blogs/"
        f"{urllib.parse.quote(blog_id)}/pages"
        "?fetchBodies=false&status=live&view=ADMIN"
    )
    pages: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        url = endpoint
        if page_token:
            url += "&pageToken=" + urllib.parse.quote(page_token)
        result = api_request(url, access_token=access_token)
        pages.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            return pages


def sync_pages(blog_id: str, access_token: str) -> None:
    existing = {
        str(page.get("title", "")).strip(): page
        for page in list_pages(blog_id, access_token)
    }

    for metadata_path in sorted(PAGES_DIR.glob("*.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        content_path = metadata_path.with_suffix(".html")
        content = content_path.read_text(encoding="utf-8").strip()
        title = str(metadata["title"]).strip()
        body = {
            "kind": "blogger#page",
            "title": title,
            "content": content,
        }

        current = existing.get(title)
        if current and current.get("id"):
            page_id = urllib.parse.quote(str(current["id"]))
            endpoint = (
                f"https://www.googleapis.com/blogger/v3/blogs/"
                f"{urllib.parse.quote(blog_id)}/pages/{page_id}"
            )
            result = api_request(
                endpoint,
                method="PUT",
                access_token=access_token,
                body=body,
            )
            print(f"페이지 업데이트: {title} → {result.get('url')}")
        else:
            endpoint = (
                f"https://www.googleapis.com/blogger/v3/blogs/"
                f"{urllib.parse.quote(blog_id)}/pages"
            )
            result = api_request(
                endpoint,
                method="POST",
                access_token=access_token,
                body=body,
            )
            print(f"페이지 생성: {title} → {result.get('url')}")


def clean_up_posts(blog_id: str, access_token: str) -> None:
    if not CLEANUP_PATH.exists():
        return

    cleanup = json.loads(CLEANUP_PATH.read_text(encoding="utf-8"))
    for item in cleanup.get("trash_posts", []):
        post_id = urllib.parse.quote(str(item["blogger_post_id"]))
        endpoint = (
            f"https://www.googleapis.com/blogger/v3/blogs/"
            f"{urllib.parse.quote(blog_id)}/posts/{post_id}?useTrash=true"
        )
        api_request(
            endpoint,
            method="DELETE",
            access_token=access_token,
            ignore_not_found=True,
        )
        print(f"테스트 글 휴지통 이동 완료: {item.get('title', post_id)}")


def main() -> None:
    blog_id = require_env("BLOGGER_BLOG_ID")
    access_token = obtain_access_token(
        require_env("GOOGLE_CLIENT_ID"),
        require_env("GOOGLE_CLIENT_SECRET"),
        require_env("GOOGLE_REFRESH_TOKEN"),
    )
    sync_pages(blog_id, access_token)
    clean_up_posts(blog_id, access_token)


if __name__ == "__main__":
    main()
