#!/usr/bin/env python3
"""Regenerate the stored expected JSON snapshots under tests/expected_json/.

Requires: nothing beyond requirements.txt; it reads only the committed
fixtures. Run after an intentional change to the explanation output:

    python3 tools/regenerate_expected_json.py

Review the resulting diff before committing it. A snapshot that changes without
an intended reason is a regression, not a file to refresh.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from expected_json_support import (  # noqa: E402
    SNAPSHOT_DIR,
    SNAPSHOT_FIXTURES,
    dump,
    run_json,
    snapshot_path,
)


def main() -> int:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for fixture in SNAPSHOT_FIXTURES:
        path = snapshot_path(fixture)
        text = dump(fixture, run_json(fixture))
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        path.write_text(text, encoding="utf-8")
        status = "unchanged" if existing == text else ("written" if existing is None else "UPDATED")
        print(f"{status:>9}  {path.relative_to(SNAPSHOT_DIR.parents[1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
