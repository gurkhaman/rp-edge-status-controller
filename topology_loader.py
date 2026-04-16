from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_topology_json(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    payload = "\n".join(line for line in lines if not line.lstrip().startswith("//"))
    return json.loads(payload)
