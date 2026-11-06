"""토큰 정규화, 교집합 검색과 작성자 일치 조건 검증."""

from mini_git.indexing import InvertedIndex


def test_keyword_index_normalizes_case_and_deduplicates_tokens():
    index = InvertedIndex()
    index.add("first", "Add LOGIN login", "Alice Kim")
    index.add("second", "add payment", "Bob")
    assert index.find_keyword("LOGIN") == {"first"}
    assert index.find_keyword("add") == {"first", "second"}
    assert index.find_keyword("ADD login") == {"first"}
    assert index.find_keyword("login missing") == set()
    assert index.find_keyword("missing") == set()
    assert index.find_keyword("  ") == set()


def test_author_index_matches_full_name_and_returns_independent_set():
    index = InvertedIndex()
    index.add("first", "hello", "Alice Kim")
    index.add("second", "hello!", "Alice Kim")
    assert index.find_author("Alice Kim") == {"first", "second"}
    assert index.find_author("alice kim") == set()
    assert index.find_author("Alice") == set()
    index.find_author("Alice Kim").clear()
    index.find_keyword("hello").clear()
    assert index.find_author("Alice Kim") == {"first", "second"}
    assert index.find_keyword("hello") == {"first"}
    assert index.find_keyword("hello!") == {"second"}
