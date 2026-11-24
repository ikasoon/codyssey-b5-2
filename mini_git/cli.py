"""CLI 문법 해석, 결과 형식과 대화형 입출력."""

from collections.abc import Mapping, Sequence

from mini_git.commands import (
    AncestorsCommand,
    BranchCommand,
    Command,
    CommitCommand,
    ExitCommand,
    InitCommand,
    LogCommand,
    PathCommand,
    SearchByAuthor,
    SearchByKeyword,
    SwitchCommand,
    parse_command,
)
from mini_git.domain import BranchName, CommitHash, MiniGitError
from mini_git.repository import Commit, Repository


def _format_branch_name(name: BranchName) -> str:
    if (
        name != name.strip()
        or not name.isprintable()
        or any(character in name for character in ",[]'\"")
    ):
        return repr(name)
    return name


def format_commits(
    commits: Sequence[Commit],
    empty: str = "No commits",
    *,
    branches_by_commit: Mapping[CommitHash, Sequence[BranchName]] | None = None,
) -> str:
    """커밋 메타데이터를 입출력 없이 일관된 텍스트로 변환한다."""
    if not commits:
        return empty
    if branches_by_commit is None:
        branches_by_commit = {}
    entries = []
    for commit in commits:
        branches = branches_by_commit.get(commit.hash, ())
        label = ""
        if branches:
            names = ", ".join(_format_branch_name(branch) for branch in branches)
            label = f" [{names}]"
        entries.append(
            f"commit {commit.hash} ({commit.author}, "
            f"{commit.timestamp.isoformat(timespec='seconds')}){label}\n{commit.message}"
        )
    return "\n".join(entries)


def _format_search_results(matches: Sequence[Commit]) -> str:
    if not matches:
        return "No commits found"
    suffix = "" if len(matches) == 1 else "s"
    return f"Found {len(matches)} commit{suffix}:\n" + format_commits(matches)


def execute(line: str, repository: Repository) -> str | None:
    """명령 결과를 반환한다. 빈 입력은 빈 문자열, 종료 명령은 None이다."""
    command = parse_command(line)
    if command is None:
        return ""
    return _execute_command(command, repository)


def _execute_command(command: Command, repository: Repository) -> str | None:
    match command:
        case ExitCommand():
            return None
        case InitCommand(author=author):
            repository.initialize(author)
            return (
                f"Initialized repository.\nCurrent branch: {repository.current_branch}\n"
                f"Current user: {repository.author}"
            )
        case BranchCommand(name=name):
            repository.create_branch(name)
            return f"Created branch: {name}"
        case SwitchCommand(name=name):
            repository.switch(name)
            return f"Switched to branch: {name}"
        case CommitCommand(message=message):
            commit = repository.commit(message)
            return f"[{repository.current_branch} {commit.hash}] {commit.message}"
        case LogCommand(sort_by=sort_by):
            return format_commits(
                repository.log(sort_by), branches_by_commit=repository.branches_by_commit()
            )
        case PathCommand(start=start, end=end):
            path = repository.path(start, end)
            return "Path: " + " -> ".join(path) if path is not None else "No path"
        case AncestorsCommand(hash=commit_hash):
            return format_commits(repository.ancestors(commit_hash), empty="No ancestors")
        case SearchByAuthor(author=author):
            return _format_search_results(repository.search_author(author))
        case SearchByKeyword(query=query):
            return _format_search_results(repository.search_keyword(query))


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
