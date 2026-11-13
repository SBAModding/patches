#!/usr/bin/env python3
"""Validates index.json and every patch zip it references. Standard library only."""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_PREFIX = "https://raw.githubusercontent.com/SBAModding/patches/main/"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MAX_BYTES = 95 * 1024 * 1024  # GitHub rejects files over 100 MB; keep headroom.
errors = []


def err(msg):
    errors.append(msg)
    print(f"error: {msg}")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    index = json.loads((ROOT / "index.json").read_text())
    if index.get("schemaVersion") != 1:
        err("schemaVersion must be 1")
    seen = set()
    for package, game in index.get("games", {}).items():
        for p in game.get("patches", []):
            label = f"{package}/{p.get('id')}@{p.get('patchVersion')}"
            for key in ("id", "name", "patchVersion", "gameVersion", "gameHash", "url", "sha256", "size"):
                if key not in p:
                    err(f"{label}: missing '{key}'")
            if err_count_for(label):
                continue
            if not ID.match(p["id"]):
                err(f"{label}: invalid id")
            if not HEX64.match(p["gameHash"]) or not HEX64.match(p["sha256"]):
                err(f"{label}: gameHash/sha256 must be 64 lowercase hex characters")
            key = (package, p["gameVersion"], p["gameHash"], p["id"], p["patchVersion"])
            if key in seen:
                err(f"{label}: duplicate entry")
            seen.add(key)
            if not p["url"].startswith("https://"):
                err(f"{label}: url must be https")
            if not p["url"].startswith(RAW_PREFIX):
                print(f"note: {label}: url is not hosted in this repository, skipping file checks")
                continue
            path = ROOT / p["url"][len(RAW_PREFIX):]
            if not path.is_file():
                err(f"{label}: {path.relative_to(ROOT)} does not exist")
                continue
            if path.stat().st_size > MAX_BYTES:
                err(f"{label}: file is larger than 95 MB")
            if path.stat().st_size != p["size"]:
                err(f"{label}: size is {path.stat().st_size}, index says {p['size']}")
            if sha256(path) != p["sha256"]:
                err(f"{label}: sha256 does not match the file")
            check_zip(label, path, p)
    if errors:
        print(f"{len(errors)} error(s)")
        sys.exit(1)
    print("ok")


def err_count_for(label):
    return any(e.startswith(label + ":") for e in errors)


def check_zip(label, path, p):
    try:
        with zipfile.ZipFile(path) as z:
            m = json.loads(z.read("manifest.json"))
            for key in ("id", "patchVersion", "gameVersion", "gameHash"):
                if m.get(key) != p[key]:
                    err(f"{label}: zip manifest {key}={m.get(key)!r} differs from the index ({p[key]!r})")
            if m.get("skipHashVerification"):
                err(f"{label}: released patches must not set skipHashVerification")
            names = z.namelist()
            if not any(n.startswith("dex/") and n.endswith(".dex") for n in names) and \
               not any(n.startswith("lib/arm64-v8a/") and n.endswith(".so") for n in names):
                err(f"{label}: zip contains no dex files or arm64-v8a libraries")
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as e:
        err(f"{label}: unreadable patch zip ({e})")


if __name__ == "__main__":
    main()
