# 생활해결노트 자동 게시 시스템 v2

이 버전은 **Node.js와 npm을 전혀 사용하지 않습니다.**  
게시 프로그램은 GitHub Actions의 Python 환경에서 실행됩니다.

## 최종 작동 방식

```text
게시글 파일 추가
→ Pull Request
→ 사용자가 Merge 승인
→ GitHub Actions
→ Blogger 자동 게시
→ 게시 URL과 글 ID 기록
```

## 기존 저장소에서 교체할 파일

기존 저장소의 아래 항목을 삭제합니다.

- `package.json`
- `package-lock.json`
- 기존 `.github` 폴더
- 기존 `scripts` 폴더

그다음 이 패키지의 아래 항목을 업로드합니다.

- `.github`
- `scripts`
- `posts`
- `.gitignore`
- `README.md`

## 최초 설정: Refresh Token 발급

로컬 프로그램 설치 없이 Google OAuth 2.0 Playground를 사용합니다.

1. `https://developers.google.com/oauthplayground/`를 엽니다.
2. 오른쪽 위 톱니바퀴를 누릅니다.
3. **Use your own OAuth credentials**를 체크합니다.
4. Google Cloud에서 받은 Client ID와 Client Secret을 입력합니다.
5. 왼쪽 Step 1의 입력란에 아래 범위를 직접 입력합니다.

```text
https://www.googleapis.com/auth/blogger
```

6. **Authorize APIs**를 누릅니다.
7. 생활해결노트 Blogger를 소유한 Google 계정으로 승인합니다.
8. Step 2에서 **Exchange authorization code for tokens**를 누릅니다.
9. 표시되는 **Refresh token**을 복사합니다.

> OAuth Playground 자체 기본 자격 증명을 사용하면 refresh token이 24시간 후 취소될 수 있습니다. 반드시 톱니바퀴에서 본인의 OAuth Client ID와 Client Secret을 입력합니다.

## GitHub Secrets 네 개

저장소에서 다음으로 이동합니다.

`Settings → Secrets and variables → Actions → New repository secret`

| 이름 | 값 |
|---|---|
| `BLOGGER_BLOG_ID` | `1324155537003326281` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |
| `GOOGLE_REFRESH_TOKEN` | OAuth Playground에서 받은 Refresh token |

## 게시글 파일 형식

폴더:

```text
posts/ready/washing-machine-smell/
```

`post.json`:

```json
{
  "title": "세탁기에서 쉰 냄새가 나는 이유와 해결 방법",
  "slug": "washing-machine-musty-smell",
  "labels": ["세탁·건조"],
  "status": "ready"
}
```

`content.html`:

```html
<p>본문 요약...</p>
<h2>원인</h2>
<p>본문...</p>
```

## 승인 방식

1. 글 파일을 별도 브랜치에 올립니다.
2. Pull Request를 만듭니다.
3. 자동 검사 통과 여부와 글 내용을 확인합니다.
4. Merge하면 자동 게시됩니다.
5. 게시가 성공하면 `post.json`이 `published` 상태로 바뀌고 공개 URL이 기록됩니다.

## 보안

- Client ID, Client Secret, Refresh token을 저장소 파일에 적지 않습니다.
- 위 세 값은 GitHub Secrets에만 입력합니다.
- 이 채팅에도 비밀값을 보내지 않습니다.
- 게시용 비밀값은 `main`에 Merge된 후 실행되는 워크플로우에서만 사용됩니다.
