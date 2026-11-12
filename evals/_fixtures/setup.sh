#!/usr/bin/env bash
# scaffold_script for the eval cases: build the synthetic workspace in the current (empty) directory.
# Usage from a case dir: ../_fixtures/setup.sh <kind>
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$here/workspace.py" "$here/../.." "$1"
git init -q
