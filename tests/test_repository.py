"""저장소 상태 전이와 입력 오류 및 역색인 사용 검증."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from mini_git.repository import MiniGitError, Repository


@pytest.fixture
def repository():
    repository = Repository(clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    repository.initialize("Alice Kim")
    return repository


@pytest.mark.parametrize("action", [
    lambda repository: repository.head,
    lambda repository: repository.create_branch("feature"),
    lambda repository: repository.switch("main"),
    lambda repository: repository.commit("first"),
    lambda repository: repository.log(),
    lambda repository: repository.path("a", "b"),
    lambda repository: repository.ancestors("a"),
    lambda repository: repository.search_keyword("first"),
    lambda repository: repository.search_author("Alice"),
])
def test_commands_require_initialization(action):
    with pytest.raises(MiniGitError, match="^Repository not initialized$"):
        action(Repository())


def test_initialize_sets_author_main_and_empty_head(repository):
    assert repository.author == "Alice Kim"
    assert repository.current_branch == "main"
    assert repository.branches == {"main": None}
    assert repository.head is None
    assert repository.log() == []
    with pytest.raises(MiniGitError, match="^Repository already initialized$"):
        repository.initialize("Bob")
    assert repository.author == "Alice Kim"


def test_commit_and_branch_views_reflect_changes_and_block_writes():
    repository = Repository()
    assert repository.commits == repository.branches == {}
    assert repository.current_branch == "main"
    assert repository.author == ""
    repository.initialize("Alice")
    commits = repository.commits
    branches = repository.branches

    commit = repository.commit("first")
    with pytest.raises(TypeError):
        commits[commit.hash] = commit
    with pytest.raises(TypeError):
        branches["main"] = None

    assert commits[commit.hash] == commit
    assert branches["main"] == repository.head == commit.hash


@pytest.mark.parametrize("text", ["", " ", "\t\n"])
def test_initialize_rejects_blank_author(text):
    with pytest.raises(MiniGitError, match="^Invalid args$"):
        Repository().initialize(text)


@pytest.mark.parametrize("action", [
    lambda repository: repository.create_branch(" "),
    lambda repository: repository.commit(" "),
    lambda repository: repository.search_keyword(" "),
    lambda repository: repository.search_author(" "),
    lambda repository: repository.log("unknown"),
])
def test_invalid_arguments_do_not_create_commits(repository, action):
    with pytest.raises(MiniGitError, match="^Invalid args$"):
        action(repository)
    assert repository.commits == {}
    assert repository.head is None


def test_branches_keep_independent_tips_and_log_includes_all_commits(repository):
    root = repository.commit("Initial commit")
    repository.create_branch("feature")
    assert repository.current_branch == "main"
    repository.switch("feature")
    feature = repository.commit("Add login")
    repository.switch("main")
    main = repository.commit("Add payment")
    assert root.parents == ()
    assert feature.parents == main.parents == (root.hash,)
    assert repository.branches == {"main": main.hash, "feature": feature.hash}
    assert [commit.hash for commit in repository.log()] == [root.hash, feature.hash, main.hash]
    assert repository.path(feature.hash, main.hash) == [feature.hash, root.hash, main.hash]
    assert repository.ancestors(feature.hash) == [root]
    assert repository.ancestors(root.hash) == []
    with pytest.raises(FrozenInstanceError):
        root.parents = (feature.hash,)


def test_empty_branch_can_produce_an_independent_root(repository):
    repository.create_branch("empty")
    root = repository.commit("main root")
    repository.switch("empty")
    other = repository.commit("independent root")
    assert other.parents == ()
    assert repository.path(root.hash, other.hash) is None
    assert len(repository.log()) == 2


def test_duplicate_and_unknown_branches_preserve_state(repository):
    with pytest.raises(MiniGitError, match="^Branch already exists: main$"):
        repository.create_branch("main")
    with pytest.raises(MiniGitError, match="^Unknown branch: missing$"):
        repository.switch("missing")
    assert repository.branches == {"main": None}
    assert repository.current_branch == "main"


def test_unknown_commit_errors_identify_the_missing_hash(repository):
    root = repository.commit("first")
    with pytest.raises(MiniGitError, match="^Unknown commit: missing$"):
        repository.ancestors("missing")
    with pytest.raises(MiniGitError, match="^Unknown commit: missing$"):
        repository.path("missing", root.hash)
    with pytest.raises(MiniGitError, match="^Unknown commit: missing$"):
        repository.path(root.hash, "missing")


def test_sort_criteria_and_equal_key_stability():
    dates = iter(datetime(2026, 1, day, tzinfo=timezone.utc) for day in (3, 1, 2))
    repository = Repository(clock=lambda: next(dates))
    repository.initialize("Zoe")
    first = repository.commit("first")
    repository.author = "Alice"
    second = repository.commit("second")
    third = repository.commit("third")
    assert repository.log() == [first, second, third]
    assert repository.log("date") == [second, third, first]
    assert repository.log("author") == [second, third, first]
    assert repository.search_author("Alice") == [second, third]


def test_counter_hashes_are_unique_and_default_clock_uses_utc():
    repository = Repository()
    repository.initialize("Alice")
    commits = [repository.commit("repeated message") for _ in range(1000)]
    assert commits[0].hash == "00000001"
    assert commits[-1].hash == "000003e8"
    assert len({commit.hash for commit in commits}) == 1000
    assert commits[0].timestamp.tzinfo == timezone.utc


def test_search_looks_up_index_candidates_without_scanning_commits(repository, monkeypatch):
    first = repository.commit("Add LOGIN login")
    repository.commit("Add payment")

    class LookupOnly(dict):
        def __iter__(self):
            raise AssertionError("전체 커밋 순회는 허용하지 않는다")

        def values(self):
            raise AssertionError("전체 커밋 순회는 허용하지 않는다")

        def items(self):
            raise AssertionError("전체 커밋 순회는 허용하지 않는다")

    monkeypatch.setattr(repository, "_commits", LookupOnly(repository.commits))
    assert repository.search_keyword("LOGIN") == [first]
    assert repository.search_keyword("add login") == [first]
    assert len(repository.search_author("Alice Kim")) == 2
    assert repository.search_author("missing") == []
    assert repository.search_keyword("log") == []
