# Mini Git

[과제 명세](docs/assignment.md)의 필수 기능을 구현한 메모리 기반 CLI 프로그램이다.
커밋 메타데이터와 브랜치를 관리하며, 프로그램을 종료하면 데이터가 사라진다.

## 시작하기

Python 3.10 이상, uv, just가 필요하다. 기본 개발 버전은 `.python-version`의 Python 3.12다.
저장소 루트에서 실행하며, 가상환경을 직접 활성화할 필요는 없다.

```sh
just sync
just run
```

`just sync`는 `uv.lock`에 맞춰 `.venv`와 개발 의존성을 준비한다.
실행 시 추가 패키지는 필요하지 않으며, `python main.py`로도 실행할 수 있다.

## 개발 명령

| 명령 | 동작 |
| --- | --- |
| `just` | 사용 가능한 명령 표시 |
| `just sync` | `uv sync --locked`로 환경 준비 |
| `just run` | `uv run --locked python main.py`로 REPL 실행 |
| `just typecheck` | mypy로 진입점과 애플리케이션을 Python 3.10 기준으로 검사 |
| `just test` | pytest 실행, 커버리지 출력 및 기준 검사 |
| `just check` | 잠금 파일 최신 상태 확인, 타입 검사, 테스트 실행 |
| `just lock` | 의존성 설정 변경 후 `uv.lock` 갱신 |

개발 의존성은 mypy, pytest, coverage다. `pyproject.toml`과 `uv.lock`을 함께 관리한다.
`just test`는 애플리케이션과 진입점의 **라인 80%, 분기 70%** 기준을 각각 검사한다.
상세 결과는 터미널과 `.cache/coverage.json`에서 확인한다.

## 사용 예시

`mini-git>` 프롬프트에 다음 명령을 입력한다.

```text
INIT "Alice Kim"
COMMIT "Initial commit"
BRANCH feature
SWITCH feature
COMMIT "Add login feature"
SWITCH main
COMMIT "Add payment feature"
LOG
PATH 00000002 00000003
ANCESTORS 00000002
SEARCH "login"
SEARCH --author="Alice Kim"
LOG --sort-by=date
quit
```

커밋 hash는 `00000001`부터 증가하는 16진수 식별자다.
위 예시의 경로 출력은 `Path: 00000002 -> 00000001 -> 00000003`이다.

## 명령과 규칙

| 명령 | 동작 |
| --- | --- |
| `INIT <user_name>` | 빈 `main` 브랜치와 현재 작성자 설정 |
| `BRANCH <branch_name>` | 현재 HEAD를 가리키는 브랜치 생성 |
| `SWITCH <branch_name>` | 현재 브랜치 전환 |
| `COMMIT <message>` | 현재 HEAD를 부모로 커밋 생성, HEAD와 역색인 갱신 |
| `LOG` | 모든 브랜치의 커밋을 부모가 자식보다 먼저 나오게 출력 |
| `LOG --sort-by=date\|author` | 날짜 또는 작성자 오름차순 출력 |
| `PATH <commit1> <commit2>` | 부모 연결을 양방향으로 탐색한 최단 경로 출력 |
| `ANCESTORS <commit_hash>` | 자신을 제외한 모든 조상을 중복 없이 출력 |
| `SEARCH <keyword>` | 공백으로 분리하고 소문자로 정규화한 토큰 검색 |
| `SEARCH --author=<name>` | 작성자 전체 이름이 일치하는 커밋 검색 |
| `exit` / `quit` | 프로그램 종료 |

- 명령어는 대소문자를 구분하지 않는다. 브랜치·작성자 이름과 옵션 표기는 구분한다.
- 공백이 포함된 문자열은 따옴표로 감싼다. 예: `COMMIT "Add login"`.
- `INIT`은 세션당 한 번 허용한다. 초기화 전에는 다른 저장소 명령을 실행할 수 없다.
- 첫 커밋 전에 만든 빈 브랜치에서 커밋하면 독립된 루트가 생길 수 있다.
- 정렬 옵션은 지정한 기준을 우선하며, 동률에서는 기본 로그 순서를 유지한다. 시간은 UTC다.
- 최단 경로가 여러 개면 `hash1->hash2->...` 문자열의 사전순으로 선택한다. 연결되지 않으면 `No path`를 출력한다.
- 조상은 반복형 DFS의 발견 순서로 출력한다.
- `SEARCH "add login"`은 두 토큰을 모두 포함하는 커밋을 찾는다. 부분 문자열 검색은 하지 않으며 구두점도 토큰에 남는다.
- 빈 입력은 무시하고, EOF 또는 입력 중 Ctrl+C로도 종료할 수 있다.

잘못된 인자는 `Invalid args`, 없는 브랜치·커밋은 `Unknown branch: <name>` / `Unknown commit: <hash>`로 표시한다.
오류 뒤에도 같은 세션에서 다음 명령을 입력할 수 있다.

## 코드 구성

| 파일 | 역할 |
| --- | --- |
| `main.py` | 실행 진입점 |
| `mini_git/cli.py` | 명령 실행, 결과 형식, REPL |
| `mini_git/commands.py` | 문자열 파싱, 명령별 인자 타입 |
| `mini_git/domain.py` | 커밋 해시, 브랜치·작성자 이름, 정렬 옵션 타입 |
| `mini_git/repository.py` | 불변 커밋 노드, 브랜치·HEAD와 저장소 상태 |
| `mini_git/algorithms.py` | 병합 정렬, 위상 정렬, BFS·DFS |
| `mini_git/indexing.py` | 키워드·작성자 역색인 |
| `tests/test_*.py` | 알고리즘·상태 전이·CLI 검증 |

필요한 개념과 시간복잡도는 [학습 정리](docs/study.md)에서 확인한다.
