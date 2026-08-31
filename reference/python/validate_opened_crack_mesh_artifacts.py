#!/usr/bin/env python3
"""Validate one exported opened-crack mesh and its pairing artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from opened_crack_mesh_artifacts import OpenedCrackArtifactError, validate_exported_artifacts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--pairs", type=Path, required=True)
    args = parser.parse_args()
    try:
        validate_exported_artifacts(args.mesh, args.pairs)
    except (OSError, json.JSONDecodeError, OpenedCrackArtifactError) as error:
        print(f"opened crack mesh artifact error: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
