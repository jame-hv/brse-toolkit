#!/usr/bin/env python3
"""Diff two structured JSON sources already normalized to [{"key": ..., "value": ...}, ...].

Usage: diff-structured.py <old.json> <new.json>
"""
import json
import sys


def diff(old: list[dict], new: list[dict]) -> dict:
    old_map = {item["key"]: item["value"] for item in old}
    new_map = {item["key"]: item["value"] for item in new}

    added = [{"key": k, "value": v} for k, v in new_map.items() if k not in old_map]
    removed = [{"key": k, "value": v} for k, v in old_map.items() if k not in new_map]
    changed = [
        {"key": k, "old_value": old_map[k], "new_value": new_map[k]}
        for k in old_map.keys() & new_map.keys()
        if old_map[k] != new_map[k]
    ]
    return {"added": added, "removed": removed, "changed": changed}


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
