#!/usr/bin/env python3
"""Materialise the small declared R0 displacement-controlled case family."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path


VARIANTS = (
    ("r0-elastic-displacement-e180-v1", 180.0, 0.04),
    ("r0-elastic-displacement-e200-v1", 200.0, 0.05),
    ("r0-elastic-displacement-e220-v1", 220.0, 0.06),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    template = json.loads(args.template.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    for case_id, modulus, displacement in VARIANTS:
        card = deepcopy(template)
        card["case_id"] = case_id
        card["model"]["youngs_modulus_gpa"] = modulus
        card["loading"]["top_displacement_mm"] = displacement
        (args.output / f"{case_id}.json").write_text(
            json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
