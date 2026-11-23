"""커밋·브랜치 상태와 알고리즘을 연결하는 메모리 저장소."""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Final

from mini_git.algorithms import (
    ancestor_hashes,
    merge_sort,
    shortest_path,
    topological_order,
)
from mini_git.domain import AuthorName, BranchName, CommitHash, LogSort
from mini_git.domain import MiniGitError as MiniGitError
from mini_git.indexing import InvertedIndex

_MAIN_BRANCH: Final = BranchName("main")


@dataclass(frozen=True)
class Commit:
    """생성 후 부모와 메타데이터를 변경할 수 없는 커밋 노드."""

    hash: CommitHash
    message: str
    author: AuthorName
    timestamp: datetime
    parents: tuple[CommitHash, ...]


@dataclass
class _InitializedState:
    """초기화 이후의 작성자와 브랜치별 커밋 참조."""

    author: AuthorName
    current_branch: BranchName
    branches: dict[BranchName, CommitHash | None]

    @property
    def head(self) -> CommitHash | None:
        return self.branches[self.current_branch]


class Repository:
    """브랜치 끝과 커밋 DAG 및 역색인을 세션 메모리에 유지한다."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._commits: dict[CommitHash, Commit] = {}
        self._state: _InitializedState | None = None
        self._next_id = 1
        self._parents: dict[CommitHash, tuple[CommitHash, ...]] = {}
        self._index = InvertedIndex()
        self._clock = clock if clock is not None else lambda: datetime.now(timezone.utc)

    @property
    def commits(self) -> Mapping[CommitHash, Commit]:
        """해시로 커밋을 조회하는 읽기 전용 뷰를 반환한다."""
        return MappingProxyType(self._commits)

    @property
    def branches(self) -> Mapping[BranchName, CommitHash | None]:
        """브랜치별 마지막 커밋을 읽기 전용 뷰로 반환한다."""
        state = self._state
        return MappingProxyType(state.branches if state is not None else {})

    @property
    def current_branch(self) -> BranchName:
        """현재 상태를 표시할 브랜치 이름을 반환한다."""
        state = self._state
        return state.current_branch if state is not None else _MAIN_BRANCH

    @property
    def author(self) -> AuthorName:
        """현재 작성자를 반환한다. 초기화 전에는 표시용 빈 문자열이다."""
        state = self._state
        return state.author if state is not None else AuthorName("")

    @author.setter
    def author(self, author: AuthorName) -> None:
        state = self._require_state()
        self._validate_text(author)
        state.author = author

    @property
    def head(self) -> CommitHash | None:
        """현재 브랜치가 가리키는 커밋 해시를 반환한다."""
        return self._require_state().head

    def initialize(self, author: AuthorName) -> None:
        """빈 main 브랜치와 작성자를 설정한다. 재초기화는 거부한다."""
        self._validate_text(author)
        if self._state is not None:
            raise MiniGitError("Repository already initialized")
        self._state = _InitializedState(
            author=author,
            current_branch=_MAIN_BRANCH,
            branches={_MAIN_BRANCH: None},
        )

    def create_branch(self, name: BranchName) -> None:
        """현재 HEAD를 가리키는 새 브랜치를 만든다."""
        state = self._require_state()
        self._validate_text(name)
        if name in state.branches:
            raise MiniGitError(f"Branch already exists: {name}")
        state.branches[name] = state.head

    def switch(self, name: BranchName) -> None:
        """기존 브랜치로 현재 브랜치를 전환한다."""
        state = self._require_state()
        if name not in state.branches:
            raise MiniGitError(f"Unknown branch: {name}")
        state.current_branch = name

    def commit(self, message: str) -> Commit:
        """현재 HEAD를 부모로 하는 유일한 hash의 커밋을 추가한다."""
        state = self._require_state()
        self._validate_text(message)
        head = state.head
        commit = Commit(
            hash=CommitHash(f"{self._next_id:08x}"),
            message=message,
            author=state.author,
            timestamp=self._clock(),
            parents=() if head is None else (head,),
        )
        self._next_id += 1
        self._commits[commit.hash] = commit
        self._parents[commit.hash] = commit.parents
        state.branches[state.current_branch] = commit.hash
        self._index.add(commit.hash, commit.message, commit.author)
        return commit

    def log(self, sort_by: LogSort | None = None) -> list[Commit]:
        """전체 브랜치의 커밋을 위상 순서 또는 지정 기준의 오름차순으로 구한다."""
        self._require_state()
        commits = [self._commits[node] for node in topological_order(self._parents)]
        match sort_by:
            case None:
                return commits
            case "date":
                return merge_sort(commits, key=lambda commit: commit.timestamp)
            case "author":
                return merge_sort(commits, key=lambda commit: commit.author)
        raise MiniGitError("Invalid args")

    def ancestors(self, commit_hash: CommitHash) -> list[Commit]:
        """지정 커밋의 모든 조상을 DFS 발견 순서로 반환한다."""
        commit = self._get_commit(commit_hash)
        return [self._commits[node] for node in ancestor_hashes(self._parents, commit.hash)]

    def path(self, start: CommitHash, end: CommitHash) -> list[CommitHash] | None:
        """커밋 사이의 무방향 최단 경로를 반환한다."""
        source = self._get_commit(start)
        target = self._get_commit(end)
        return shortest_path(self._parents, source.hash, target.hash)

    def search_keyword(self, query: str) -> list[Commit]:
        """전체 커밋 순회 없이 키워드 역색인을 조회한다."""
        self._require_state()
        self._validate_text(query)
        return self._indexed_commits(self._index.find_keyword(query))

    def search_author(self, author: AuthorName) -> list[Commit]:
        """전체 커밋 순회 없이 작성자 역색인을 조회한다."""
        self._require_state()
        self._validate_text(author)
        return self._indexed_commits(self._index.find_author(author))

    def _indexed_commits(self, hashes: Iterable[CommitHash]) -> list[Commit]:
        ordered = merge_sort(list(hashes), key=lambda value: value)
        return [self._commits[node] for node in ordered]

    def _get_commit(self, commit_hash: CommitHash) -> Commit:
        self._require_state()
        if commit_hash not in self._commits:
            raise MiniGitError(f"Unknown commit: {commit_hash}")
        return self._commits[commit_hash]

    def _require_state(self) -> _InitializedState:
        state = self._state
        if state is None:
            raise MiniGitError("Repository not initialized")
        return state

    @staticmethod
    def _validate_text(value: str) -> None:
        if not value.strip():
            raise MiniGitError("Invalid args")
