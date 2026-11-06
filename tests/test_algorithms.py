"""알고리즘의 순서 보장, 경로 선택 및 긴 그래프 처리 검증."""

from collections import Counter
import random

import pytest

from mini_git.algorithms import (
    ancestor_hashes,
    merge_sort,
    shortest_path,
    topological_order,
)


@pytest.mark.parametrize(
    ("items", "expected"),
    [([], []), ([1], [1]), ([3, 1, 2, 1, -2], [-2, 1, 1, 2, 3]), ([1, 2], [1, 2])],
)
def test_merge_sort_orders_without_mutating_input(items, expected):
    original = items.copy()
    assert merge_sort(items, key=lambda value: value) == expected
    assert items == original


def test_merge_sort_is_stable_and_accepts_different_keys():
    records = [(2, "z"), (1, "b"), (2, "a"), (1, "c")]
    assert merge_sort(records, key=lambda item: item[0]) == [
        (1, "b"), (1, "c"), (2, "z"), (2, "a")
    ]
    assert merge_sort(records, key=lambda item: item[1]) == [
        (2, "a"), (1, "b"), (1, "c"), (2, "z")
    ]


def test_merge_sort_preserves_all_values_on_larger_input():
    generator = random.Random(42)
    items = [generator.randrange(-100, 100) for _ in range(2048)]
    result = merge_sort(items, key=lambda value: value)
    assert Counter(result) == Counter(items)
    assert all(left <= right for left, right in zip(result, result[1:]))


def test_topological_order_handles_multiple_parents_and_disconnected_roots():
    graph = {"child": ("left", "right"), "right": ("root",), "left": ("root",),
             "root": (), "orphan": ()}
    order = topological_order(graph)
    assert set(order) == set(graph)
    position = {node: index for index, node in enumerate(order)}
    assert all(position[parent] < position[child]
               for child, parents in graph.items() for parent in parents)
    assert topological_order({}) == []


def test_topological_order_rejects_a_cycle():
    with pytest.raises(ValueError, match="cycle"):
        topological_order({"a": ("b",), "b": ("a",)})


def test_ancestors_visit_all_parents_once_and_exclude_self():
    graph = {"root": (), "left": ("root",), "right": ("root",),
             "tip": ("left", "right"), "unrelated": ()}
    result = ancestor_hashes(graph, "tip")
    assert set(result) == {"left", "right", "root"}
    assert len(result) == 3
    assert ancestor_hashes(graph, "root") == []


def test_shortest_path_uses_both_edge_directions():
    graph = {"root": (), "left": ("root",), "right": ("root",), "other": ()}
    assert shortest_path(graph, "left", "right") == ["left", "root", "right"]
    assert shortest_path(graph, "root", "left") == ["root", "left"]
    assert shortest_path(graph, "left", "left") == ["left"]
    assert shortest_path(graph, "root", "other") is None


def test_shortest_path_chooses_lexicographically_smallest_tie():
    graph = {"end": (), "b": ("end",), "a": ("end",), "c": ("end",),
             "start": ("b", "a", "c")}
    assert shortest_path(graph, "start", "end") == ["start", "a", "end"]


def test_path_tie_compares_serialized_path_including_delimiters():
    graph = {"end": (), "a": ("end",), "a!": ("end",), "start": ("a", "a!")}
    assert shortest_path(graph, "start", "end") == ["start", "a!", "end"]


def test_shortest_path_prefers_distance_before_lexical_order():
    graph = {"end": (), "a": ("end",), "b": ("a",), "start": ("b", "end")}
    assert shortest_path(graph, "start", "end") == ["start", "end"]


def test_graph_traversal_does_not_depend_on_python_recursion_depth():
    graph = {"0": ()}
    for number in range(1, 1600):
        graph[str(number)] = (str(number - 1),)
    assert len(ancestor_hashes(graph, "1599")) == 1599
    assert topological_order(graph) == [str(number) for number in range(1600)]
    assert shortest_path(graph, "0", "1599") == [str(number) for number in range(1600)]
