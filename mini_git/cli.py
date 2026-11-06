"""CLI 문법 해석, 결과 형식과 대화형 입출력."""

from collections.abc import Sequence
import shlex

from mini_git.repository import Commit, MiniGitError, Repository


def format_commits(commits: Sequence[Commit], empty: str = "No commits") -> str:
    """커밋 메타데이터를 입출력 없이 일관된 텍스트로 변환한다."""
    if not commits:
        return empty
    return "\n".join(
        f"commit {commit.hash} ({commit.author}, "
        f"{commit.timestamp.isoformat(timespec='seconds')})\n{commit.message}"
        for commit in commits
    )


def _require_args(args: list[str], count: int) -> None:
    if len(args) != count or any(not argument.strip() for argument in args):
        raise MiniGitError("Invalid args")


def execute(line: str, repository: Repository) -> str | None:
    """명령 결과를 반환한다. 빈 입력은 빈 문자열, 종료 명령은 None이다."""
    try:
        tokens = shlex.split(line)
    except ValueError:
        raise MiniGitError("Invalid args") from None
    if not tokens:
        return ""
    command = tokens[0].upper()
    args = tokens[1:]

    if command in {"EXIT", "QUIT"}:
        _require_args(args, 0)
        return None
    if command == "INIT":
        _require_args(args, 1)
        repository.initialize(args[0])
        return ("Initialized repository.\nCurrent branch: main\n"
                f"Current user: {repository.author}")
    if command == "BRANCH":
        _require_args(args, 1)
        repository.create_branch(args[0])
        return f"Created branch: {args[0]}"
    if command == "SWITCH":
        _require_args(args, 1)
        repository.switch(args[0])
        return f"Switched to branch: {args[0]}"
    if command == "COMMIT":
        _require_args(args, 1)
        commit = repository.commit(args[0])
        return f"[{repository.current_branch} {commit.hash}] {commit.message}"
    if command == "LOG":
        if not args:
            return format_commits(repository.log())
        _require_args(args, 1)
        if args[0] not in {"--sort-by=date", "--sort-by=author"}:
            raise MiniGitError("Invalid args")
        return format_commits(repository.log(args[0].split("=", 1)[1]))
    if command == "PATH":
        _require_args(args, 2)
        path = repository.path(args[0], args[1])
        return "Path: " + " -> ".join(path) if path is not None else "No path"
    if command == "ANCESTORS":
        _require_args(args, 1)
        return format_commits(repository.ancestors(args[0]), empty="No ancestors")
    if command == "SEARCH":
        _require_args(args, 1)
        if args[0].startswith("--author="):
            matches = repository.search_author(args[0].split("=", 1)[1])
        elif args[0].startswith("--"):
            raise MiniGitError("Invalid args")
        else:
            matches = repository.search_keyword(args[0])
        if not matches:
            return "No commits found"
        suffix = "" if len(matches) == 1 else "s"
        return f"Found {len(matches)} commit{suffix}:\n" + format_commits(matches)
    raise MiniGitError(f"Unknown command: {tokens[0]}")


def run() -> None:
    """REPL을 실행하고 입력 오류 뒤에도 같은 저장소 세션을 유지한다."""
    repository = Repository()
    while True:
        try:
            line = input("mini-git> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        try:
            output = execute(line, repository)
        except MiniGitError as error:
            print(error)
            continue
        if output is None:
            break
        if output:
            print(output)
