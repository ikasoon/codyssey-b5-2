"""필수 CLI 명령과 문법 오류 및 대화형 실행 검증."""

from datetime import datetime, timezone
from pathlib import Path
import runpy

import pytest

from mini_git.cli import execute, run
from mini_git.repository import MiniGitError, Repository


@pytest.fixture
def repository():
    repository = Repository(clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    execute('iNiT "Alice Kim"', repository)
    return repository


def test_initialize_accepts_quoted_unicode_name():
    repository = Repository()
    assert execute('init "홍 길동"', repository) == (
        "Initialized repository.\nCurrent branch: main\nCurrent user: 홍 길동"
    )
    assert execute('commit "로그인 추가"', repository) == "[main 00000001] 로그인 추가"
    assert "Found 1 commit:" in execute('SEARCH "로그인 추가"', repository)


def test_cli_scenario_with_branches_log_paths_and_search(repository):
    assert execute('CoMmIt "Initial commit"', repository) == "[main 00000001] Initial commit"
    assert execute("BRANCH feature", repository) == "Created branch: feature"
    assert execute("switch feature", repository) == "Switched to branch: feature"
    assert execute('commit "Add LOGIN feature"', repository) == "[feature 00000002] Add LOGIN feature"
    execute("SWITCH main", repository)
    execute('COMMIT "Add payment feature"', repository)
    log = execute("log", repository)
    assert log.index("00000001") < log.index("00000002") < log.index("00000003")
    assert "Alice Kim, 2026-01-01T00:00:00+00:00" in log
    assert "Add LOGIN feature" in log
    assert execute("PATH 00000002 00000003", repository) == (
        "Path: 00000002 -> 00000001 -> 00000003"
    )
    assert execute("PATH 00000002 00000002", repository) == "Path: 00000002"
    assert execute("ANCESTORS 00000002", repository) == (
        "commit 00000001 (Alice Kim, 2026-01-01T00:00:00+00:00)\nInitial commit"
    )
    assert execute('SEARCH "LOGIN feature"', repository) == (
        "Found 1 commit:\ncommit 00000002 (Alice Kim, 2026-01-01T00:00:00+00:00)\nAdd LOGIN feature"
    )
    assert execute('SEARCH --author="Alice Kim"', repository).startswith("Found 3 commits:")
    assert execute("SEARCH missing", repository) == "No commits found"
    assert execute("SEARCH --author=missing", repository) == "No commits found"
    assert execute("LOG --sort-by=date", repository) == log
    assert execute("LOG --sort-by=author", repository) == log


def test_empty_log_ancestors_and_disconnected_path(repository):
    assert execute("LOG", repository) == "No commits"
    execute("BRANCH empty", repository)
    execute('COMMIT "main root"', repository)
    assert execute("ANCESTORS 00000001", repository) == "No ancestors"
    execute("SWITCH empty", repository)
    execute('COMMIT "separate root"', repository)
    assert execute("PATH 00000001 00000002", repository) == "No path"


@pytest.mark.parametrize("line", [
    'COMMIT "unfinished',
    "INIT", "INIT Alice Bob", 'INIT " "',
    "BRANCH", "BRANCH a b", 'BRANCH ""',
    "SWITCH", "SWITCH a b",
    "COMMIT", "COMMIT hello world", 'COMMIT " "',
    "LOG --sort-by=", "LOG --sort-by=unknown", "LOG --sort-by date", "LOG extra", 'LOG ""',
    "PATH", "PATH a", "PATH a b c", 'PATH "" b',
    "ANCESTORS", "ANCESTORS a b",
    "SEARCH", "SEARCH a b", 'SEARCH " "',
    "SEARCH --author=", 'SEARCH --author=" "', "SEARCH --unknown=a",
    "EXIT extra", "QUIT extra",
])
def test_invalid_grammar_reports_standard_error_and_preserves_state(repository, line):
    with pytest.raises(MiniGitError, match="^Invalid args$"):
        execute(line, repository)
    assert repository.commits == {}
    assert repository.current_branch == "main"


@pytest.mark.parametrize(("line", "message"), [
    ("SWITCH missing", "Unknown branch: missing"),
    ("ANCESTORS unknown", "Unknown commit: unknown"),
    ("BRANCH main", "Branch already exists: main"),
    ("merge feature", "Unknown command: merge"),
    ("diff a b", "Unknown command: diff"),
    ("INIT Bob", "Repository already initialized"),
])
def test_command_errors_have_clear_messages(repository, line, message):
    with pytest.raises(MiniGitError) as error:
        execute(line, repository)
    assert str(error.value) == message


@pytest.mark.parametrize("line", ["", "   ", "\t"])
def test_blank_input_has_no_effect(repository, line):
    assert execute(line, repository) == ""


@pytest.mark.parametrize("line", ["exit", "QuIt"])
def test_exit_commands_work_without_initialization(line):
    assert execute(line, Repository()) is None


def test_repl_recovers_from_errors_and_keeps_session(monkeypatch, capsys):
    lines = iter(["", "COMMIT first", "INIT Alice", 'COMMIT "unterminated',
                  'COMMIT "Ready now"', "LOG", "exit"])
    prompts = []

    def read(prompt):
        prompts.append(prompt)
        return next(lines)

    monkeypatch.setattr("builtins.input", read)
    run()
    output = capsys.readouterr().out
    assert "Repository not initialized\n" in output
    assert "Invalid args\n" in output
    assert "[main 00000001] Ready now\n" in output
    assert "commit 00000001 (Alice," in output
    assert prompts == ["mini-git> "] * 7


@pytest.mark.parametrize("exception", [EOFError, KeyboardInterrupt])
def test_repl_exits_cleanly_when_input_is_interrupted(monkeypatch, capsys, exception):
    def read(prompt):
        raise exception

    monkeypatch.setattr("builtins.input", read)
    run()
    assert capsys.readouterr().out == "\n"


@pytest.mark.parametrize("run_name", ["__main__", "imported_main"])
def test_main_entry_point(monkeypatch, run_name):
    monkeypatch.setattr("builtins.input", lambda prompt: "quit")
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "main.py"), run_name=run_name)
