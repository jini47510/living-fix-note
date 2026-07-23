from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import read_post, validate_post, write_metadata


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} GitHub Secret이 없습니다.")
    return value


def changed_directories(before_sha: str, current_sha: str) -> list[Path]:
    if not before_sha or set(before_sha) == {"0"}:
        command = ["git", "ls-files", "posts/ready/*/post.json"]
    else:
        command = [
            "git", "diff", "--name-only", before_sha, current_sha, "--", "posts/ready"
        ]

    output = subprocess.check_output(command, text=True)
    directories: set[Path] = set()

    for line in output.splitlines():
        parts = Path(line).parts
        if len(parts) >= 4 and parts[0:2] == ("posts", "ready"):
            directory = Path(parts[0]) / parts[1] / parts[2]
            if directory.exists():
                directories.add(directory)

    return sorted(directories)


def site_files_changed(before_sha: str, current_sha: str) -> bool:
    if not before_sha or set(before_sha) == {"0"}:
        return Path("site").exists()

    result = subprocess.run(
        ["git", "diff", "--quiet", before_sha, current_sha, "--", "site"],
        check=False,
    )
    return result.returncode == 1


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        method=method,
        headers=headers or {},
        data=data,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google API 오류 {exc.code}: {body}") from exc


def obtain_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")

    response = request_json(
        "https://oauth2.googleapis.com/token",
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=payload,
    )

    access_token = response.get("access_token")
    if not access_token:
        raise RuntimeError(f"Access token 발급 실패: {response}")
    return str(access_token)


def publish_post(
    blog_id: str,
    access_token: str,
    metadata: dict[str, Any],
    content: str,
) -> dict[str, Any]:
    endpoint = (
        f"https://www.googleapis.com/blogger/v3/blogs/"
        f"{urllib.parse.quote(blog_id)}/posts/"
    )
    body = json.dumps(
        {
            "kind": "blogger#post",
            "title": metadata["title"],
            "content": content,
            "labels": metadata["labels"],
        },
        ensure_ascii=False,
    ).encode("utf-8")

    return request_json(
        endpoint,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        data=body,
    )


def main() -> None:
    blog_id = require_env("BLOGGER_BLOG_ID")
    client_id = require_env("GOOGLE_CLIENT_ID")
    client_secret = require_env("GOOGLE_CLIENT_SECRET")
    refresh_token = require_env("GOOGLE_REFRESH_TOKEN")
    before_sha = os.environ.get("BEFORE_SHA", "")
    current_sha = os.environ.get("CURRENT_SHA", "HEAD")

    directories = changed_directories(before_sha, current_sha)
    sync_site = site_files_changed(before_sha, current_sha)
    if not directories and not sync_site:
        print("이번 병합에서 게시할 글이 없습니다.")
        return

    access_token = obtain_access_token(client_id, client_secret, refresh_token)

    if sync_site:
        from sync_blogger_site import clean_up_posts, sync_pages
        from validate_site import main as validate_site

        validate_site()
        sync_pages(blog_id, access_token)
        clean_up_posts(blog_id, access_token)

    for directory in directories:
        metadata, content = read_post(directory)
        errors = validate_post(directory, metadata, content)
        if errors:
            raise RuntimeError("\n".join(errors))

        if metadata.get("status") == "published" or metadata.get("blogger_post_id"):
            print(f"건너뜀: {metadata.get('title')} — 이미 게시됨")
            continue

        if metadata.get("status") != "ready":
            print(f"건너뜀: {metadata.get('title')} — status가 ready가 아님")
            continue

        result = publish_post(blog_id, access_token, metadata, content)
        updated = {
            **metadata,
            "status": "published",
            "blogger_post_id": result.get("id"),
            "published_url": result.get("url"),
            "published_at": result.get("published")
            or datetime.now(timezone.utc).isoformat(),
        }
        write_metadata(directory, updated)
        print(f"게시 완료: {metadata['title']} → {result.get('url')}")


if __name__ == "__main__":
    main()
