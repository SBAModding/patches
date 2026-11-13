#!/usr/bin/env python3
"""Adds a patch zip to the repository and registers it in index.json.

    python3 scripts/add_patch.py path/to/patch.zip --package com.example.game [--game-name "Example"]

The zip's manifest.json supplies id, name, patchVersion, gameVersion and gameHash.
"""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_PREFIX = "https://raw.githubusercontent.com/SBAModding/patches/main/"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--package", required=True, help="Android package name of the game")
    ap.add_argument("--game-name", help="Display name, used when the game is new to the index")
    args = ap.parse_args()

    with zipfile.ZipFile(args.zip) as z:
        m = json.loads(z.read("manifest.json"))
    for key in ("id", "name", "patchVersion", "gameVersion", "gameHash"):
        if key not in m:
            raise SystemExit(f"manifest.json is missing '{key}'")

    rel = Path("patches") / args.package / m["gameVersion"] / f"{m['id']}-v{m['patchVersion']}.zip"
    dest = ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.zip, dest)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()

    index_path = ROOT / "index.json"
    index = json.loads(index_path.read_text())
    game = index["games"].setdefault(args.package, {"patches": []})
    if args.game_name:
        game["name"] = args.game_name
    entry = {
        "id": m["id"], "name": m["name"], "patchVersion": m["patchVersion"],
        "gameVersion": m["gameVersion"], "gameHash": m["gameHash"],
        "url": RAW_PREFIX + rel.as_posix(), "sha256": digest, "size": dest.stat().st_size,
    }
    game["patches"] = [p for p in game["patches"]
                       if (p["id"], p["patchVersion"], p["gameVersion"], p["gameHash"])
                       != (entry["id"], entry["patchVersion"], entry["gameVersion"], entry["gameHash"])]
    game["patches"].append(entry)
    game["patches"].sort(key=lambda p: (p["gameVersion"], p["id"], p["patchVersion"]))
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    print(f"added {rel} ({entry['size']} bytes, sha256 {digest})")


if __name__ == "__main__":
    main()
