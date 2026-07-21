import { listPostDirectories, readPost, validatePost } from "./lib.js";

const directories = listPostDirectories();
if (directories.length === 0) {
  console.log("검사할 게시글이 없습니다.");
  process.exit(0);
}

const errors = [];
for (const dir of directories) {
  try {
    const post = readPost(dir);
    errors.push(...validatePost(post));
  } catch (error) {
    errors.push(error.message);
  }
}

if (errors.length > 0) {
  console.error("\n게시글 검증 실패:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log(`${directories.length}개 게시글 검증 완료.`);
