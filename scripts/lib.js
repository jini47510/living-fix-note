import fs from "node:fs";
import path from "node:path";

export function listPostDirectories(base = "posts/ready") {
  if (!fs.existsSync(base)) return [];
  return fs.readdirSync(base, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(base, entry.name))
    .sort();
}

export function readPost(dir) {
  const metadataPath = path.join(dir, "post.json");
  const contentPath = path.join(dir, "content.html");

  if (!fs.existsSync(metadataPath)) {
    throw new Error(`${metadataPath} 파일이 없습니다.`);
  }
  if (!fs.existsSync(contentPath)) {
    throw new Error(`${contentPath} 파일이 없습니다.`);
  }

  const metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"));
  const content = fs.readFileSync(contentPath, "utf8").trim();

  return { dir, metadataPath, contentPath, metadata, content };
}

export function validatePost(post) {
  const errors = [];
  const { metadata, content, dir } = post;

  if (!metadata.title || typeof metadata.title !== "string") {
    errors.push(`${dir}: title이 필요합니다.`);
  }
  if (!metadata.slug || !/^[a-z0-9-]+$/.test(metadata.slug)) {
    errors.push(`${dir}: slug는 영문 소문자, 숫자, 하이픈만 사용할 수 있습니다.`);
  }
  if (!Array.isArray(metadata.labels) || metadata.labels.length < 1) {
    errors.push(`${dir}: labels 배열에 카테고리를 하나 이상 넣어야 합니다.`);
  }
  if (!["ready", "published"].includes(metadata.status)) {
    errors.push(`${dir}: status는 ready 또는 published여야 합니다.`);
  }
  if (!content || content.length < 500) {
    errors.push(`${dir}: content.html 본문이 너무 짧습니다(최소 500자).`);
  }
  if (metadata.status === "published" && !metadata.blogger_post_id) {
    errors.push(`${dir}: published 상태에는 blogger_post_id가 필요합니다.`);
  }
  return errors;
}

export function writeMetadata(post, metadata) {
  fs.writeFileSync(
    post.metadataPath,
    JSON.stringify(metadata, null, 2) + "\n",
    "utf8"
  );
}
