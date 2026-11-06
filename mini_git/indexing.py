"""커밋 메시지와 작성자를 위한 역색인."""


class InvertedIndex:
    """토큰·작성자에서 커밋 hash 집합을 직접 조회한다."""

    def __init__(self) -> None:
        self._keywords: dict[str, set[str]] = {}
        self._authors: dict[str, set[str]] = {}

    def add(self, commit_hash: str, message: str, author: str) -> None:
        """공백 분리·소문자 정규화 토큰과 작성자를 인덱스에 등록한다."""
        for token in set(message.lower().split()):
            self._keywords.setdefault(token, set()).add(commit_hash)
        self._authors.setdefault(author, set()).add(commit_hash)

    def find_keyword(self, query: str) -> set[str]:
        """여러 단어를 검색하면 모든 토큰을 포함하는 커밋만 반환한다."""
        tokens = query.lower().split()
        if not tokens:
            return set()
        matches = self._keywords.get(tokens[0], set()).copy()
        for token in tokens[1:]:
            matches.intersection_update(self._keywords.get(token, set()))
        return matches

    def find_author(self, author: str) -> set[str]:
        """대소문자와 공백을 포함해 작성자 이름이 일치하는 커밋을 반환한다."""
        return self._authors.get(author, set()).copy()
