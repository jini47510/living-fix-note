import { execFileSync } from "node:child_process";
import path from "node:path";
import { google } from "googleapis";
import { readPost, validatePost, writeMetadata } from "./lib.js";

const required = [
  "BLOGGER_BLOG_ID",
  "GOOGLE_CLIENT_ID",
  "GOOGLE_CLIENT_SECRET",
  "GOOGLE_REFRESH_TOKEN"
];

for (const name of required) {
  if (!process.env[name]) throw new Error(`${name} GitHub Secret이 없습니다.`);
}

const before = process.env.BEFORE_SHA;
const current = process.env.CURRENT_SHA || "HEAD";

let changed;
if (!before || /^0+$/.test(before)) {
  changed = execFileSync("git", ["ls-files", "posts/ready/*/post.json"], { encoding: "utf8" });
} else {
  changed = execFileSync(
    "git",
    ["diff", "--name-only", before, current, "--", "posts/ready"],
    { encoding: "utf8" }
  );
}

const dirs = [...new Set(
  changed.split("\n")
    .filter(Boolean)
    .map((file) => {
      const match = file.match(/^(posts\/ready\/[^/]+)\//);
      return match ? match[1] : null;
    })
    .filter(Boolean)
)].sort();

if (dirs.length === 0) {
  console.log("이번 병합에서 게시할 글이 없습니다.");
  process.exit(0);
}

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET
);
oauth2Client.setCredentials({ refresh_token: process.env.GOOGLE_REFRESH_TOKEN });

const blogger = google.blogger({ version: "v3", auth: oauth2Client });

for (const dir of dirs) {
  const post = readPost(dir);
  const errors = validatePost(post);
  if (errors.length) throw new Error(errors.join("\n"));

  if (post.metadata.status === "published" || post.metadata.blogger_post_id) {
    console.log(`건너뜀: ${post.metadata.title} (이미 게시됨)`);
    continue;
  }

  if (post.metadata.status !== "ready") {
    console.log(`건너뜀: ${post.metadata.title} (status=${post.metadata.status})`);
    continue;
  }

  const requestBody = {
    title: post.metadata.title,
    content: post.content,
    labels: post.metadata.labels
  };

  const response = await blogger.posts.insert({
    blogId: process.env.BLOGGER_BLOG_ID,
    isDraft: false,
    requestBody
  });

  const published = response.data;
  const updated = {
    ...post.metadata,
    status: "published",
    blogger_post_id: published.id,
    published_url: published.url,
    published_at: published.published || new Date().toISOString()
  };
  writeMetadata(post, updated);
  console.log(`게시 완료: ${post.metadata.title} → ${published.url}`);
}
