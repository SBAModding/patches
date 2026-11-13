# SBAModLoader patches

Asset overlays that the games supported by SBAModLoader need before they can be modded. SBAModLoader reads
[`index.json`](index.json), finds the patch for the installed game, downloads it and applies it.

## How a patch is matched

A patch applies to exactly one build of a game. SBAModLoader picks the entry in `games.<package>.patches` where

- `gameVersion` equals the installed game's version name, and
- `gameHash` equals the SHA-256 of the installed game's base APK.

If several entries match, the highest `patchVersion` wins. The download is checked against `sha256` before it is
installed.

## Layout

```
index.json                       the index SBAModLoader fetches
schema/index.schema.json         JSON Schema for index.json
patches/<package>/<version>/     patch zips, named <id>-v<patchVersion>.zip
scripts/validate.py              checks the index and every zip (runs in CI)
scripts/add_patch.py             copies a zip in and registers it in index.json
```

### index.json

```json
{
  "schemaVersion": 1,
  "games": {
    "com.example.game": {
      "name": "Example Game",
      "patches": [
        {
          "id": "example-fix",
          "name": "Example fix",
          "patchVersion": 1,
          "gameVersion": "1.2.3",
          "gameHash": "<sha256 of the game's base APK>",
          "url": "https://raw.githubusercontent.com/SBAModding/patches/main/patches/com.example.game/1.2.3/example-fix-v1.zip",
          "sha256": "<sha256 of the patch zip>",
          "size": 12345678
        }
      ]
    }
  }
}
```

`url` must be HTTPS. It may also be relative to `index.json`, which lets a fork or a custom source host its own
copy.

### Patch zip

```
manifest.json
dex/classes.dex ...              replacement classes, searched before the game's own
lib/arm64-v8a/*.so               replacement native libraries
```

```json
{
  "id": "example-fix",
  "name": "Example fix",
  "patchVersion": 1,
  "gameVersion": "1.2.3",
  "gameHash": "<sha256 of the game's base APK>",
  "applicationClass": "android.app.Application"
}
```

`applicationClass` is optional. It replaces the Application class declared in the game's manifest; use
`android.app.Application` when the patch removes a wrapper class. Released patches must not set
`skipHashVerification`, which exists only for local testing with developer features enabled.

## Adding a patch

1. Build the zip as described above. Get the game hash with `sha256sum base.apk`.
2. `python3 scripts/add_patch.py patch.zip --package com.example.game --game-name "Example Game"`
3. `python3 scripts/validate.py`, then commit. Files must stay under 95 MB (GitHub's hard limit is 100 MB).

Never edit a published zip. Publish a new `patchVersion` instead.
