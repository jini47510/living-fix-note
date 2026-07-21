from common import post_directories, read_post, validate_post


def main() -> None:
    directories = post_directories()
    if not directories:
        print("검사할 게시글이 없습니다.")
        return

    errors: list[str] = []
    for directory in directories:
        try:
            metadata, content = read_post(directory)
            errors.extend(validate_post(directory, metadata, content))
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        print("게시글 검증 실패:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"{len(directories)}개 게시글 검증 완료.")


if __name__ == "__main__":
    main()
