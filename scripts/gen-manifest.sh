#!/bin/bash
# gen-manifest.sh — Generate versions.json at the repo root for the Pulse
# updater workflow.
#
# Reads each packaged .alfredworkflow's source info.plist (name / bundleid /
# version) and hashes the built zip (sha256), producing the manifest Pulse
# fetches to decide what needs updating:
#
#   versions.json: {"repo", "branch", "updated", "workflows": [
#       {name, bundleid, version, file, sha256, url}, …]}
#
# Called by package-all.sh after packaging; run it standalone after a
# manual repack. Commit versions.json along with the workflow changes.
#
# Usage: bash scripts/gen-manifest.sh [owner/repo] [branch]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REPO="${1:-SongRunqi/alfred-workflows}"
BRANCH="${2:-main}"

python3 - "$ROOT" "$REPO" "$BRANCH" <<'EOF'
import hashlib
import json
import plistlib
import sys
import time
from pathlib import Path

root, repo, branch = sys.argv[1], sys.argv[2], sys.argv[3]

# workflow source dir | packaged file name (must match package-all.sh)
PACKAGES = [
    ("Homebrew Manager", "Homebrew Manager.alfredworkflow"),
    ("netease-music-controls", "NetEase Music Controls.alfredworkflow"),
    ("Glide", "Glide.alfredworkflow"),
    ("PiHop", "PiHop.alfredworkflow"),
    ("System Settings", "Settings.alfredworkflow"),
    ("ApplicationShortcuts", "Application Shortcuts.alfredworkflow"),
    ("Pulse", "Pulse.alfredworkflow"),
    ("SQLIn", "SQL In.alfredworkflow"),
]

workflows = []
for src, pkg in PACKAGES:
    plist_p = Path(root) / src / "info.plist"
    zip_p = Path(root) / pkg
    if not plist_p.is_file() or not zip_p.is_file():
        print(f"SKIP {pkg}: missing source info.plist or package", file=sys.stderr)
        continue
    with plist_p.open("rb") as f:
        meta = plistlib.load(f)
    workflows.append({
        "name": meta.get("name", src),
        "bundleid": meta.get("bundleid", ""),
        "version": str(meta.get("version") or ""),
        "file": pkg,
        "sha256": hashlib.sha256(zip_p.read_bytes()).hexdigest(),
        "url": f"https://raw.githubusercontent.com/{repo}/{branch}/"
               f"{pkg.replace(' ', '%20')}",
    })

manifest = {
    "repo": repo,
    "branch": branch,
    "updated": time.strftime("%Y-%m-%d %H:%M:%S %z"),
    "workflows": workflows,
}

out = Path(root) / "versions.json"
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(f"wrote {out} ({len(workflows)} workflows)")
EOF
