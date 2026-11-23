"""CLI 입력을 인자가 정해진 명령으로 변환한다."""

from dataclasses import dataclass
import shlex
from typing import TypeAlias

from mini_git.domain import AuthorName, BranchName, CommitHash, LogSort, MiniGitError


@dataclass(frozen=True)
class InitCommand:
    author: AuthorName


@dataclass(frozen=True)
class BranchCommand:
    name: BranchName


@dataclass(frozen=True)
class SwitchCommand:
    name: BranchName


@dataclass(frozen=True)
class CommitCommand:
    message: str


@dataclass(frozen=True)
class LogCommand:
    sort_by: LogSort | None = None


@dataclass(frozen=True)
class PathCommand:
    start: CommitHash
    end: CommitHash


@dataclass(frozen=True)
class AncestorsCommand:
    hash: CommitHash


@dataclass(frozen=True)
class SearchByKeyword:
    query: str


@dataclass(frozen=True)
class SearchByAuthor:
    author: AuthorName


@dataclass(frozen=True)
class ExitCommand:
    """세션 종료를 요청한다."""


Command: TypeAlias = (
    InitCommand | BranchCommand | SwitchCommand | CommitCommand | LogCommand
    | PathCommand | AncestorsCommand | SearchByKeyword | SearchByAuthor | ExitCommand
)


def _require_args(args: list[str], count: int) -> None:
    if len(args) != count or any(not argument.strip() for argument in args):
        raise MiniGitError("Invalid args")


def parse_command(line: str) -> Command | None:
    """명령 문법을 검증한다. 빈 입력은 None을 반환한다."""
    try:
        tokens = shlex.split(line)
    except ValueError:
        raise MiniGitError("Invalid args") from None
    if not tokens:
        return None

    args = tokens[1:]
    match tokens[0].upper():
        case "EXIT" | "QUIT":
            _require_args(args, 0)
            return ExitCommand()
        case "INIT":
            _require_args(args, 1)
            return InitCommand(AuthorName(args[0]))
        case "BRANCH":
            _require_args(args, 1)
            return BranchCommand(BranchName(args[0]))
        case "SWITCH":
            _require_args(args, 1)
            return SwitchCommand(BranchName(args[0]))
        case "COMMIT":
            _require_args(args, 1)
            return CommitCommand(args[0])
        case "LOG":
            if not args:
                return LogCommand()
            _require_args(args, 1)
            match args[0]:
                case "--sort-by=date":
                    return LogCommand("date")
                case "--sort-by=author":
                    return LogCommand("author")
                case _:
                    raise MiniGitError("Invalid args")
        case "PATH":
            _require_args(args, 2)
            return PathCommand(start=CommitHash(args[0]), end=CommitHash(args[1]))
        case "ANCESTORS":
            _require_args(args, 1)
            return AncestorsCommand(CommitHash(args[0]))
        case "SEARCH":
            _require_args(args, 1)
            query = args[0]
            if query.startswith("--author="):
                return SearchByAuthor(AuthorName(query.split("=", 1)[1]))
            if query.startswith("--"):
                raise MiniGitError("Invalid args")
            return SearchByKeyword(query)
        case _:
            raise MiniGitError(f"Unknown command: {tokens[0]}")
