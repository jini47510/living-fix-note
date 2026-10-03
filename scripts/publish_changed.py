from __future__ import annotations

import html
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import read_post, validate_post, write_metadata


RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}
RETRY_DELAYS_SECONDS = (10, 30, 60, 120)
POST_INTERVAL_SECONDS = 10
IMAGE_UPDATE_MANIFEST = Path("posts/ready/_maintenance/post-image-updates.json")


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
            if directory.exists() and not directory.name.startswith("_"):
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


def image_updates_changed(before_sha: str, current_sha: str) -> bool:
    if not IMAGE_UPDATE_MANIFEST.exists():
        return False
    if not before_sha or set(before_sha) == {"0"}:
        return True
    result = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            before_sha,
            current_sha,
            "--",
            str(IMAGE_UPDATE_MANIFEST),
        ],
        check=False,
    )
    return result.returncode == 1


def public_image_url(path: Path) -> str:
    repository = os.environ.get("GITHUB_REPOSITORY", "jini47510/living-fix-note")
    encoded_path = urllib.parse.quote(path.as_posix(), safe="/")
    return f"https://raw.githubusercontent.com/{repository}/main/{encoded_path}"


def attach_local_thumbnail(directory: Path, metadata: dict[str, Any], content: str) -> str:
    images = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    if not images:
        return content

    image = images[0]
    image_url = public_image_url(image)
    updated = content
    for local_name in (image.name, f"./{image.name}"):
        updated = updated.replace(f'src="{local_name}"', f'src="{image_url}"')
        updated = updated.replace(f"src='{local_name}'", f"src='{image_url}'")

    if image_url not in updated:
        alt = html.escape(str(metadata.get("title", "대표 이미지")), quote=True)
        figure = (
            '<figure style="margin:0 0 24px;text-align:center">'
            f'<img src="{image_url}" alt="{alt}" '
            'style="max-width:100%;height:auto" loading="eager">'
            "</figure>"
        )
        updated = figure + updated
    return updated


def apply_post_image_updates(blog_id: str, access_token: str) -> None:
    payload = json.loads(IMAGE_UPDATE_MANIFEST.read_text(encoding="utf-8"))
    updates = payload.get("updates", [])
    if not isinstance(updates, list):
        raise RuntimeError("이미지 보정 파일의 updates는 배열이어야 합니다.")

    for item in updates:
        post_id = str(item.get("post_id", "")).strip()
        image_path = Path(str(item.get("image_path", "")))
        alt = str(item.get("alt", "대표 이미지")).strip()
        if not post_id or not image_path.is_file():
            raise RuntimeError(f"이미지 보정 항목 오류: {item}")

        image_url = public_image_url(image_path)
        endpoint = (
            f"https://www.googleapis.com/blogger/v3/blogs/"
            f"{urllib.parse.quote(blog_id)}/posts/{urllib.parse.quote(post_id)}"
        )
        post = request_json(
            endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        content = str(post.get("content", ""))
        if image_url in content:
            print(f"이미지 보정 건너뜀: {post.get('title')} — 이미 연결됨")
            continue

        figure = (
            '<figure style="margin:0 0 24px;text-align:center">'
            f'<img src="{image_url}" alt="{html.escape(alt, quote=True)}" '
            'style="max-width:100%;height:auto" loading="eager">'
            "</figure>"
        )
        body = json.dumps({"content": figure + content}, ensure_ascii=False).encode(
            "utf-8"
        )
        request_json(
            endpoint,
            method="PATCH",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            data=body,
        )
        print(f"이미지 보정 완료: {post.get('title')} → {image_url}")


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> dict[str, Any]:
    for attempt in range(len(RETRY_DELAYS_SECONDS) + 1):
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
            if exc.code not in RETRYABLE_HTTP_CODES or attempt >= len(
                RETRY_DELAYS_SECONDS
            ):
                raise RuntimeError(f"Google API 오류 {exc.code}: {body}") from exc

            retry_after = exc.headers.get("Retry-After")
            try:
                delay = int(retry_after) if retry_after else RETRY_DELAYS_SECONDS[attempt]
            except ValueError:
                delay = RETRY_DELAYS_SECONDS[attempt]
            delay = max(delay, RETRY_DELAYS_SECONDS[attempt])
            print(
                f"Google API 요청 제한({exc.code}). {delay}초 후 "
                f"{attempt + 2}번째 시도를 합니다."
            )
            time.sleep(delay)


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

    publish_at = metadata.get("publish_at")
    insert_endpoint = endpoint + ("?isDraft=true" if publish_at else "")
    result = request_json(
        insert_endpoint,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        data=body,
    )

    if not publish_at:
        return result

    post_id = result.get("id")
    if not post_id:
        raise RuntimeError(f"Blogger 임시글 ID가 없습니다: {result}")
    schedule_endpoint = (
        f"https://www.googleapis.com/blogger/v3/blogs/"
        f"{urllib.parse.quote(blog_id)}/posts/{urllib.parse.quote(str(post_id))}/publish?"
        + urllib.parse.urlencode({"publishDate": str(publish_at)})
    )
    return request_json(
        schedule_endpoint,
        method="POST",
        headers={"Authorization": f"Bearer {access_token}"},
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
    update_images = image_updates_changed(before_sha, current_sha)
    if not directories and not sync_site and not update_images:
        print("이번 병합에서 게시할 글이 없습니다.")
        return

    access_token = obtain_access_token(client_id, client_secret, refresh_token)

    if sync_site:
        from sync_blogger_site import clean_up_posts, sync_pages
        from validate_site import main as validate_site

        validate_site()
        sync_pages(blog_id, access_token)
        clean_up_posts(blog_id, access_token)

    if update_images:
        apply_post_image_updates(blog_id, access_token)

    publishable_posts = []
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

        publishable_posts.append((directory, metadata, content))

    for index, (directory, metadata, content) in enumerate(publishable_posts):
        if index:
            print(f"다음 글 등록 전 {POST_INTERVAL_SECONDS}초 대기합니다.")
            time.sleep(POST_INTERVAL_SECONDS)
        content = attach_local_thumbnail(directory, metadata, content)
        result = publish_post(blog_id, access_token, metadata, content)
        scheduled = bool(metadata.get("publish_at"))
        updated = {
            **metadata,
            "status": "scheduled" if scheduled else "published",
            "blogger_post_id": result.get("id"),
            "published_url": result.get("url"),
            "published_at": result.get("published") or metadata.get("publish_at")
            or datetime.now(timezone.utc).isoformat(),
        }
        write_metadata(directory, updated)
        action = "예약 완료" if scheduled else "게시 완료"
        print(f"{action}: {metadata['title']} → {result.get('url')}")


if __name__ == "__main__":
    main()
