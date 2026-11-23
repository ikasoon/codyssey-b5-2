"""저장소와 명령 처리에서 공유하는 도메인 값의 타입."""

from typing import Literal, NewType, TypeAlias

CommitHash = NewType("CommitHash", str)
BranchName = NewType("BranchName", str)
AuthorName = NewType("AuthorName", str)
LogSort: TypeAlias = Literal["date", "author"]


class MiniGitError(ValueError):
    """CLI에 그대로 표시할 수 있는 사용자 입력 오류."""
