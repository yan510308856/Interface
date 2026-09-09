"""Analysis-only loop and progress metrics for action-boundary trajectories."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any


_EDIT_OPERATIONS = {"replace_text", "create_file", "delete_file"}
_TEST_PREFIXES = (
    ("python", "-m", "pytest"),
    ("python3", "-m", "pytest"),
    ("pytest",),
)


def _signature(event: dict[str, Any]) -> tuple[str, str]:
    return (
        str(event.get("operation", "")),
        json.dumps(event.get("arguments", {}), sort_keys=True, ensure_ascii=False),
    )


def _streak_count(values: list[Any]) -> tuple[int, int]:
    """Return (number of repeated links, longest identical-value streak)."""
    repeated = 0
    longest = 0
    previous = object()
    streak = 0
    for value in values:
        if value == previous:
            repeated += 1
            streak += 1
        else:
            streak = 1
        longest = max(longest, streak)
        previous = value
    return repeated, longest


def _read_range(event: dict[str, Any]) -> tuple[str, int, int | None] | None:
    if event.get("operation") != "read_file":
        return None
    arguments = event.get("arguments")
    if not isinstance(arguments, dict) or not isinstance(arguments.get("path"), str):
        return None
    start = arguments.get("start_line", 1)
    end = arguments.get("end_line")
    if not isinstance(start, int) or isinstance(start, bool):
        return None
    if end is not None and (not isinstance(end, int) or isinstance(end, bool)):
        return None
    return arguments["path"], start, end


def _read_ranges_overlap(left: tuple[str, int, int | None], right: tuple[str, int, int | None]) -> bool:
    if left[0] != right[0]:
        return False
    left_end = left[2] if left[2] is not None else float("inf")
    right_end = right[2] if right[2] is not None else float("inf")
    return left[1] <= right_end and right[1] <= left_end


def _is_successful_test(event: dict[str, Any]) -> bool:
    if event.get("operation") != "run_process" or event.get("status") != "success":
        return False
    arguments = event.get("arguments")
    result = event.get("result")
    argv = arguments.get("argv") if isinstance(arguments, dict) else None
    return (
        isinstance(argv, list)
        and any(argv[: len(prefix)] == list(prefix) for prefix in _TEST_PREFIXES)
        and isinstance(result, dict)
        and result.get("exit_code") == 0
    )


def trajectory_loop_metrics(events: list[dict[str, Any]]) -> dict[str, int]:
    """Compute loop/progress signals without changing execution or decisions.

    Retry counts require a repeated canonical operation signature after the same
    failure class. Read overlap is counted only for consecutive read operations;
    a range with no end line overlaps every later range on that path.
    """
    backend = [event for event in events if event.get("event") == "backend_operation"]
    actions = [
        event for event in events
        if event.get("event") in {"interface_action", "action"}
    ]
    signatures = [_signature(event) for event in backend]
    repeated_ops, max_repeated_ops = _streak_count(signatures)

    searches = [_signature(event) for event in backend if event.get("operation") == "search_text"]
    repeated_searches, max_repeated_searches = _streak_count(searches)

    read_ranges = [item for item in (_read_range(event) for event in backend) if item is not None]
    repeated_read_overlap = 0
    max_read_overlap_streak = 0
    read_overlap_streak = 0
    previous_read = None
    for current_read in read_ranges:
        if previous_read is not None and _read_ranges_overlap(previous_read, current_read):
            repeated_read_overlap += 1
            read_overlap_streak += 1
        else:
            read_overlap_streak = 0
        max_read_overlap_streak = max(max_read_overlap_streak, read_overlap_streak)
        previous_read = current_read

    seen_enoent: set[tuple[str, str]] = set()
    seen_permission_denials: set[tuple[str, str]] = set()
    enoent_retries = 0
    permission_denial_retries = 0
    for event in backend:
        signature = _signature(event)
        error = str(event.get("error", ""))
        if "No such file or directory" in error or "ENOENT" in error:
            if signature in seen_enoent:
                enoent_retries += 1
            seen_enoent.add(signature)
        if event.get("status") == "denied":
            if signature in seen_permission_denials:
                permission_denial_retries += 1
            seen_permission_denials.add(signature)

    by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in backend:
        by_action[str(event.get("action_id"))].append(event)
    actions_since_edit = 0
    actions_since_test = 0
    max_actions_since_edit = 0
    max_actions_since_test = 0
    for action in actions:
        action_events = by_action[str(action.get("action_id"))]
        if any(
            event.get("operation") in _EDIT_OPERATIONS and event.get("status") == "success"
            for event in action_events
        ):
            actions_since_edit = 0
        else:
            actions_since_edit += 1
        if any(_is_successful_test(event) for event in action_events):
            actions_since_test = 0
        else:
            actions_since_test += 1
        max_actions_since_edit = max(max_actions_since_edit, actions_since_edit)
        max_actions_since_test = max(max_actions_since_test, actions_since_test)

    return {
        "repeated_identical_operation_count": repeated_ops,
        "max_repeated_identical_operation_streak": max_repeated_ops,
        "repeated_read_overlap_count": repeated_read_overlap,
        "max_repeated_read_overlap_streak": max_read_overlap_streak,
        "repeated_identical_search_count": repeated_searches,
        "max_repeated_identical_search_streak": max_repeated_searches,
        "enoent_retry_count": enoent_retries,
        "permission_denial_retry_count": permission_denial_retries,
        "actions_since_last_edit": actions_since_edit,
        "max_actions_since_last_edit": max_actions_since_edit,
        "actions_since_last_successful_test": actions_since_test,
        "max_actions_since_last_successful_test": max_actions_since_test,
    }
