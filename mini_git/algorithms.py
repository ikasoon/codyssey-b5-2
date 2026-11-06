"""표준 정렬 API와 그래프 라이브러리를 사용하지 않는 알고리즘."""

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from typing import Any, TypeVar

T = TypeVar("T")
ParentGraph = Mapping[str, Sequence[str]]


def merge_sort(items: Sequence[T], key: Callable[[T], Any]) -> list[T]:
    """입력을 변경하지 않고 key 기준으로 오름차순 안정 병합 정렬한다."""
    if len(items) < 2:
        return list(items)
    middle = len(items) // 2
    left = merge_sort(items[:middle], key)
    right = merge_sort(items[middle:], key)
    result = []
    left_index = right_index = 0
    while left_index < len(left) and right_index < len(right):
        if key(left[left_index]) <= key(right[right_index]):
            result.append(left[left_index])
            left_index += 1
        else:
            result.append(right[right_index])
            right_index += 1
    result.extend(left[left_index:])
    result.extend(right[right_index:])
    return result


def topological_order(parents: ParentGraph) -> list[str]:
    """Kahn 알고리즘으로 모든 부모가 자식보다 앞서는 순서를 구한다."""
    indegrees = {node: len(links) for node, links in parents.items()}
    children: dict[str, list[str]] = {node: [] for node in parents}
    for child, links in parents.items():
        for parent in links:
            children[parent].append(child)
    ready = deque(node for node, degree in indegrees.items() if degree == 0)
    result = []
    while ready:
        node = ready.popleft()
        result.append(node)
        for child in children[node]:
            indegrees[child] -= 1
            if indegrees[child] == 0:
                ready.append(child)
    if len(result) != len(parents):
        raise ValueError("Commit graph contains a cycle")
    return result


def ancestor_hashes(parents: ParentGraph, start: str) -> list[str]:
    """반복형 DFS로 자신을 제외한 모든 조상을 중복 없이 구한다."""
    visited = {start}
    pending = list(parents[start])
    result = []
    while pending:
        node = pending.pop()
        if node in visited:
            continue
        visited.add(node)
        result.append(node)
        pending.extend(parents[node])
    return result


def shortest_path(parents: ParentGraph, start: str, end: str) -> list[str] | None:
    """무방향 최단 경로 중 '->'로 연결한 문자열이 가장 작은 것을 구한다."""
    neighbors: dict[str, list[str]] = {node: [] for node in parents}
    for child, links in parents.items():
        for parent in links:
            neighbors[child].append(parent)
            neighbors[parent].append(child)

    # 목적지까지의 거리를 먼저 계산하면 최단 경로에 속하는 이웃만 고를 수 있다.
    distances = {end: 0}
    pending = deque([end])
    while pending:
        node = pending.popleft()
        for neighbor in neighbors[node]:
            if neighbor not in distances:
                distances[neighbor] = distances[node] + 1
                pending.append(neighbor)
    if start not in distances:
        return None

    result = [start]
    while result[-1] != end:
        node = result[-1]
        candidates = [
            neighbor
            for neighbor in neighbors[node]
            if distances.get(neighbor) == distances[node] - 1
        ]
        next_node = candidates[0]
        for candidate in candidates[1:]:
            # 구분자까지 비교해 한 hash가 다른 hash의 접두사인 경우도 처리한다.
            if candidate + "->" < next_node + "->":
                next_node = candidate
        result.append(next_node)
    return result
