# Living Fix Note

## Purpose

This repository publishes Korean practical home-appliance troubleshooting articles to Blogger.

## Post workflow

When asked to create a post:

1. Create a branch named `post/<english-slug>`.
2. Add exactly these files:
   - `posts/ready/<english-slug>/post.json`
   - `posts/ready/<english-slug>/content.html`
3. Run `python scripts/validate_posts.py`.
4. Commit the new post and open a pull request to `main`.
5. Never merge the pull request. The user approves and merges it.

Merging to `main` publishes the post through `.github/workflows/publish-blogger.yml`.

## Content requirements

- Write in clear, natural Korean.
- Solve one specific household or appliance problem.
- Use reliable manufacturer or public-institution sources for factual claims.
- Give safe checks first and clearly state when the reader should stop and call a professional.
- Do not invent specifications, repair procedures, statistics, or sources.
- Avoid thin or repetitive SEO content.
- `content.html` must contain at least 500 Korean characters and use simple Blogger-compatible HTML.
- Use `<h2>` for major sections. Do not include `<html>`, `<head>`, or `<body>`.

## Metadata format

`post.json` must follow this shape:

```json
{
  "title": "Korean post title",
  "slug": "lowercase-english-slug",
  "labels": ["카테고리"],
  "status": "ready"
}
```

Do not add Blogger credentials or other secrets to the repository.
