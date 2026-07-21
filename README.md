# 생활해결노트 자동 게시 MVP

Pull Request를 승인하여 `main` 브랜치에 Merge하면 GitHub Actions가 Blogger API로 글을 자동 게시합니다.

## 작동 방식

1. `posts/ready/<글-slug>/`에 `post.json`과 `content.html`을 추가합니다.
2. 별도 브랜치에서 Pull Request를 만듭니다.
3. PR 검증이 통과한 뒤 사용자가 Merge합니다.
4. Merge 후 GitHub Actions가 `status: ready`인 변경 글을 Blogger에 게시합니다.
5. 게시 성공 시 `post.json`에 Blogger 글 ID, URL, 게시 시간이 기록됩니다.
6. 이미 게시된 글은 다시 게시하지 않습니다.

> **중요:** `posts/ready/example-post`는 형식 예시입니다. 최초 Merge 전에 반드시 삭제하거나 실제 글로 교체하세요.

## 1. GitHub 저장소 만들기

새 비공개 저장소를 만들고 이 폴더의 전체 파일을 업로드합니다. 기본 브랜치는 `main`으로 설정합니다.

저장소 설정에서 다음을 권장합니다.

- Settings → Branches → Add branch protection rule
- Branch name pattern: `main`
- Require a pull request before merging
- Require status checks to pass before merging
- 상태 검사로 `validate` 선택
- 직접 push를 막으려면 Do not allow bypassing 설정

## 2. Google Cloud 설정

1. Google Cloud Console에서 프로젝트를 만듭니다.
2. APIs & Services → Library에서 **Blogger API v3**를 활성화합니다.
3. OAuth consent screen을 설정합니다.
4. 테스트 단계라면 본인의 Google 계정을 Test users에 추가합니다.
5. Credentials → Create credentials → OAuth client ID를 선택합니다.
6. Application type은 **Desktop app**으로 만듭니다.
7. Client ID와 Client secret을 안전하게 보관합니다.

## 3. Refresh token 한 번 발급하기

로컬 컴퓨터에 Node.js 20 이상을 설치한 뒤 저장소 폴더에서 실행합니다.

```bash
npm install
export GOOGLE_CLIENT_ID="발급받은-client-id"
export GOOGLE_CLIENT_SECRET="발급받은-client-secret"
npm run oauth
```

Windows PowerShell:

```powershell
npm install
$env:GOOGLE_CLIENT_ID="발급받은-client-id"
$env:GOOGLE_CLIENT_SECRET="발급받은-client-secret"
npm run oauth
```

터미널에 표시되는 Google 승인 주소를 브라우저에서 열고, Blogger를 소유한 계정으로 승인합니다. 승인 후 터미널에 출력되는 refresh token을 복사합니다.

## 4. GitHub Secrets 등록

저장소에서 Settings → Secrets and variables → Actions → New repository secret으로 다음 네 개를 만듭니다.

| Secret 이름 | 값 |
|---|---|
| `BLOGGER_BLOG_ID` | `1324155537003326281` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client secret |
| `GOOGLE_REFRESH_TOKEN` | 앞 단계에서 받은 refresh token |

## 5. 게시글 형식

`post.json`

```json
{
  "title": "세탁기에서 쉰 냄새가 나는 이유와 해결 방법",
  "slug": "washing-machine-musty-smell",
  "labels": ["세탁·건조"],
  "status": "ready"
}
```

`content.html`

```html
<p>본문 요약...</p>
<h2>원인</h2>
<p>본문...</p>
```

## 6. 승인 및 게시

1. 새 브랜치를 만듭니다.
2. 게시글 폴더를 추가합니다.
3. Pull Request를 생성합니다.
4. `Validate post PR`이 통과했는지 확인합니다.
5. 내용을 확인하고 Merge합니다.
6. Actions 탭에서 `Publish approved posts to Blogger` 실행 결과를 확인합니다.

## 안전 원칙

- OAuth 값과 refresh token을 파일에 적거나 커밋하지 않습니다.
- 외부 포크의 PR에는 게시용 Secrets를 제공하지 않습니다.
- `main` Merge 이후에만 게시 워크플로우가 실행됩니다.
- 게시 후 기록된 `blogger_post_id`로 중복 게시를 방지합니다.
- refresh token이 취소되거나 만료되면 다시 발급하여 Secret만 교체합니다.

## 현재 MVP 범위

포함:
- PR 검증
- Merge 승인
- Blogger 자동 게시
- 게시 URL과 글 ID 기록
- 중복 게시 방지

제외:
- 이미지 호스팅 자동화
- 예약 발행
- 기존 글 자동 수정
- Search Console 자동 제출
- Analytics 자동 분석

이 기능들은 첫 게시 자동화가 안정적으로 작동한 뒤에만 추가합니다.
