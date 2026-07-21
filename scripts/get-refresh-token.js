import http from "node:http";
import { URL } from "node:url";
import { google } from "googleapis";

const clientId = process.env.GOOGLE_CLIENT_ID;
const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
const port = Number(process.env.OAUTH_PORT || 3000);
const redirectUri = `http://localhost:${port}/oauth2callback`;

if (!clientId || !clientSecret) {
  console.error("GOOGLE_CLIENT_ID와 GOOGLE_CLIENT_SECRET 환경변수를 먼저 설정하세요.");
  process.exit(1);
}

const oauth2Client = new google.auth.OAuth2(clientId, clientSecret, redirectUri);
const scopes = ["https://www.googleapis.com/auth/blogger"];

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, redirectUri);
    if (url.pathname !== "/oauth2callback") {
      res.writeHead(404).end("Not found");
      return;
    }

    const code = url.searchParams.get("code");
    if (!code) throw new Error("인증 코드가 없습니다.");

    const { tokens } = await oauth2Client.getToken(code);
    res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("승인이 완료되었습니다. 터미널에서 refresh token을 확인하세요.");

    console.log("\nGOOGLE_REFRESH_TOKEN:");
    console.log(tokens.refresh_token || "(반환되지 않음: 기존 앱 권한을 철회한 뒤 다시 시도하세요.)");
  } catch (error) {
    res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(`오류: ${error.message}`);
  } finally {
    setTimeout(() => server.close(), 500);
  }
});

server.listen(port, () => {
  const authUrl = oauth2Client.generateAuthUrl({
    access_type: "offline",
    prompt: "consent",
    scope: scopes
  });
  console.log(`\n브라우저에서 아래 주소를 여세요:\n${authUrl}\n`);
});
