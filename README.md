# 생활해결노트 자동 게시

승인된 글을 GitHub Actions와 Blogger API로 자동 게시하는 저장소입니다.

## 앞으로의 사용 방법

Codex에 다음처럼 요청합니다.

> 생활해결노트에 세탁기 쉰 냄새 해결 글을 작성하고 PR을 만들어줘.

Codex가 글 작성, 파일 검사, 브랜치와 Pull Request 생성을 처리합니다. 사용자는 Pull Request 내용을 확인하고 **Merge**만 누릅니다.

```text
글 요청 → Codex가 PR 생성 → 사용자 Merge → Blogger 자동 게시
```

게시가 끝나면 GitHub Actions가 공개 URL과 Blogger 글 ID를 `post.json`에 기록합니다.

## 게시글 구조

```text
posts/ready/<english-slug>/
├── post.json
└── content.html
```

`post.json` 예시:

```json
{
  "title": "세탁기에서 쉰 냄새가 나는 이유와 해결 방법",
  "slug": "washing-machine-musty-smell",
  "labels": ["세탁·건조"],
  "status": "ready"
}
```

## 자동 검사와 게시

- Pull Request: `scripts/validate_posts.py`가 모든 게시글의 형식을 검사합니다.
- `main`에 Merge: 변경된 `ready` 글만 Blogger에 게시합니다.
- 게시 성공: `status`, 공개 URL, 글 ID, 게시 시각을 저장소에 기록합니다.

## 보안

다음 값은 저장소 파일에 넣지 않고 GitHub Actions Secrets에만 보관합니다.

- `BLOGGER_BLOG_ID`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
