set positional-arguments

# 사용 가능한 명령을 표시한다.
default:
    @just --list

# 잠금 파일에 맞춰 .venv와 개발 의존성을 준비한다.
sync:
    uv sync --locked

# 의존성을 변경한 뒤 잠금 파일을 갱신한다.
lock:
    uv lock

# Mini Git REPL을 실행한다.
run:
    uv run --locked python main.py

# 테스트와 라인·분기 커버리지 기준을 검사한다.
test *args:
    uv run --locked coverage run -m pytest "$@"
    uv run --locked coverage report
    uv run --locked coverage json -o .cache/coverage.json
    uv run --locked python scripts/check_coverage.py

# 애플리케이션을 Python 3.10 기준으로 정적 타입 검사한다.
typecheck:
    uv run --locked mypy

# 잠금 파일과 타입 및 전체 테스트를 검사한다.
check:
    uv lock --check
    just typecheck
    just test
