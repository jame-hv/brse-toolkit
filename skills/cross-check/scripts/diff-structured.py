#!/usr/bin/env python3
"""Diff two structured JSON sources already normalized to [{"key": ..., "value": ...}, ...].

Usage: diff-structured.py <old.json> <new.json>
"""
import json
import sys


def _duplicate_keys(items: list[dict]) -> list[str]:
    seen = set()
    dupes = []
    for item in items:
        k = item["key"]
        if k in seen and k not in dupes:
            dupes.append(k)
        seen.add(k)
    return dupes


def diff(old: list[dict], new: list[dict]) -> dict:
    # dict-comprehension key collision silently keeps only the last
    # occurrence — that's fine as a diff *result* (a key can only map to one
    # current value), but silently losing which rows collided would hide a
    # real data problem in the source sheet, so it's surfaced separately.
    old_map = {item["key"]: item["value"] for item in old}
    new_map = {item["key"]: item["value"] for item in new}

    added = [{"key": k, "value": v} for k, v in new_map.items() if k not in old_map]
    removed = [{"key": k, "value": v} for k, v in old_map.items() if k not in new_map]
    changed = [
        {"key": k, "old_value": old_map[k], "new_value": new_map[k]}
        for k in old_map.keys() & new_map.keys()
        if old_map[k] != new_map[k]
    ]
    result = {"added": added, "removed": removed, "changed": changed}
    duplicate_keys_old = _duplicate_keys(old)
    duplicate_keys_new = _duplicate_keys(new)
    if duplicate_keys_old or duplicate_keys_new:
        result["warning"] = (
            "duplicate key(s) found in source data — only the last occurrence "
            "of each was compared, earlier ones were silently dropped from "
            "this diff"
        )
        if duplicate_keys_old:
            result["duplicate_keys_old"] = duplicate_keys_old
        if duplicate_keys_new:
            result["duplicate_keys_new"] = duplicate_keys_new
    return result


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: diff-structured.py <old.json> <new.json>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        old = json.load(f)
    with open(sys.argv[2], encoding="utf-8") as f:
        new = json.load(f)
    print(json.dumps(diff(old, new), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
