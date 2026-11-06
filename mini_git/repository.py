"""커밋·브랜치 상태와 알고리즘을 연결하는 메모리 저장소."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

from mini_git.algorithms import (
    ancestor_hashes,
    merge_sort,
    shortest_path,
    topological_order,
)
from mini_git.indexing import InvertedIndex


class MiniGitError(ValueError):
    """CLI에 그대로 표시할 수 있는 사용자 입력 오류."""


@dataclass(frozen=True)
class Commit:
    """생성 후 부모와 메타데이터를 변경할 수 없는 커밋 노드."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    parents: tuple[str, ...]


class Repository:
    """브랜치 끝과 커밋 DAG 및 역색인을 세션 메모리에 유지한다."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self.commits: dict[str, Commit] = {}
        self.branches: dict[str, str | None] = {}
        self.current_branch = "main"
        self.author = ""
        self._initialized = False
        self._next_id = 1
        self._parents: dict[str, tuple[str, ...]] = {}
        self._index = InvertedIndex()
        self._clock = clock if clock is not None else lambda: datetime.now(timezone.utc)

    @property
    def head(self) -> str | None:
        """현재 브랜치가 가리키는 커밋 hash를 반환한다."""
        self._require_initialized()
        return self.branches[self.current_branch]

    def initialize(self, author: str) -> None:
        """빈 main 브랜치와 작성자를 설정한다. 재초기화는 거부한다."""
        self._validate_text(author)
        if self._initialized:
            raise MiniGitError("Repository already initialized")
        self.branches["main"] = None
        self.author = author
        self._initialized = True

    def create_branch(self, name: str) -> None:
        """현재 HEAD를 가리키는 새 브랜치를 만든다."""
        self._require_initialized()
        self._validate_text(name)
        if name in self.branches:
            raise MiniGitError(f"Branch already exists: {name}")
        self.branches[name] = self.head

    def switch(self, name: str) -> None:
        """기존 브랜치로 현재 브랜치를 전환한다."""
        self._require_initialized()
        if name not in self.branches:
            raise MiniGitError(f"Unknown branch: {name}")
        self.current_branch = name

    def commit(self, message: str) -> Commit:
        """현재 HEAD를 부모로 하는 유일한 hash의 커밋을 추가한다."""
        self._require_initialized()
        self._validate_text(message)
        head = self.head
        commit = Commit(
            hash=f"{self._next_id:08x}",
            message=message,
            author=self.author,
            timestamp=self._clock(),
            parents=() if head is None else (head,),
        )
        self._next_id += 1
        self.commits[commit.hash] = commit
        self._parents[commit.hash] = commit.parents
        self.branches[self.current_branch] = commit.hash
        self._index.add(commit.hash, commit.message, commit.author)
        return commit

    def log(self, sort_by: str | None = None) -> list[Commit]:
        """전체 브랜치의 커밋을 위상 순서 또는 지정 기준의 오름차순으로 구한다."""
        self._require_initialized()
        commits = [self.commits[node] for node in topological_order(self._parents)]
        if sort_by is None:
            return commits
        if sort_by == "date":
            return merge_sort(commits, key=lambda commit: commit.timestamp)
        if sort_by == "author":
            return merge_sort(commits, key=lambda commit: commit.author)
        raise MiniGitError("Invalid args")

    def ancestors(self, commit_hash: str) -> list[Commit]:
        """지정 커밋의 모든 조상을 DFS 발견 순서로 반환한다."""
        self._get_commit(commit_hash)
        return [self.commits[node] for node in ancestor_hashes(self._parents, commit_hash)]

    def path(self, start: str, end: str) -> list[str] | None:
        """커밋 사이의 무방향 최단 경로를 반환한다."""
        self._get_commit(start)
        self._get_commit(end)
        return shortest_path(self._parents, start, end)

    def search_keyword(self, query: str) -> list[Commit]:
        """전체 커밋 순회 없이 키워드 역색인을 조회한다."""
        self._require_initialized()
        self._validate_text(query)
        return self._indexed_commits(self._index.find_keyword(query))

    def search_author(self, author: str) -> list[Commit]:
        """전체 커밋 순회 없이 작성자 역색인을 조회한다."""
        self._require_initialized()
        self._validate_text(author)
        return self._indexed_commits(self._index.find_author(author))

    def _indexed_commits(self, hashes: Iterable[str]) -> list[Commit]:
        ordered = merge_sort(list(hashes), key=lambda value: value)
        return [self.commits[node] for node in ordered]

    def _get_commit(self, commit_hash: str) -> Commit:
        self._require_initialized()
        if commit_hash not in self.commits:
            raise MiniGitError(f"Unknown commit: {commit_hash}")
        return self.commits[commit_hash]

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise MiniGitError("Repository not initialized")

    @staticmethod
    def _validate_text(value: str) -> None:
        if not value.strip():
            raise MiniGitError("Invalid args")
