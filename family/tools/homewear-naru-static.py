#!/usr/bin/env python3
"""Automatic 5-part clothing decomposition for Naru's homewear outfit.

Delegates to outfit_auto_static.run_character with zero manual polygons.
"""
import argparse
import json
import pathlib
from outfit_auto_static import run_character


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", default="prepared-base")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    family = pathlib.Path(__file__).resolve().parents[1]
    res = run_character(family, "homewear", "naru", candidate_name=args.candidate, force=args.force)
    print(json.dumps(res))


if __name__ == "__main__":
    main()
