#!/usr/bin/env python3
"""Automatic 5-part clothing decomposition for the Family homewear outfits.

Delegates to outfit_auto_static.run_character with zero manual polygons.
"""
import argparse
import json
import pathlib
from outfit_auto_static import run_character


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--characters", nargs="*", default=["roa", "luna", "jinni", "nova"])
    parser.add_argument("--candidate", default="prepared")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    family = pathlib.Path(__file__).resolve().parents[1]
    results = []
    for char in args.characters:
        res = run_character(family, "homewear", char, candidate_name=args.candidate, force=args.force)
        results.append(res)
    print(json.dumps({"results": results}, indent=2))


if __name__ == "__main__":
    main()
