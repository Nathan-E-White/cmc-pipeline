#!/usr/bin/env python3
"""Check that R0 family members are distinct declared cases, never point splits."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory() as directory:
    output = Path(directory)
    subprocess.run([sys.executable, str(ROOT / "reference/python/generate_r0_case_family.py"), "--template", str(ROOT / "reference/cases/r0-elastic-displacement-v1.json"), "--output", str(output)], check=True)
    cards = [json.loads(path.read_text()) for path in sorted(output.glob("*.json"))]

assert len(cards) == 3
assert {card["case_id"] for card in cards} == {
    "r0-elastic-displacement-e180-v1", "r0-elastic-displacement-e200-v1", "r0-elastic-displacement-e220-v1"
}
assert all(card["problem_key"] == "r0-elastic/v1" for card in cards)
assert all(card["loading"]["kind"] == "prescribed-top-displacement" for card in cards)
assert len({(card["model"]["youngs_modulus_gpa"], card["loading"]["top_displacement_mm"]) for card in cards}) == 3
