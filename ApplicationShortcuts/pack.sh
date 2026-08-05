#!/bin/bash
# application shortcuts v2 — release packer.
#
# Regenerates info.plist, zips the runtime files into
# ../Application Shortcuts.alfredworkflow, verifies +x bits and plist.
#
# Usage: ./pack.sh        (from this folder, or anywhere — resolves itself)

set -euo pipefail
cd "$(dirname "$0")"

NAME="Application Shortcuts"
OUT="$(cd .. && pwd)/$NAME.alfredworkflow"

python3 build_plist.py
chmod +x launch.sh filter.py

rm -f "$OUT"
zip -q -r -X "$OUT" launch.sh filter.py icon.png info.plist

echo "✓ Packed: $OUT"
TMPU="$(mktemp -d)"
unzip -q "$OUT" -d "$TMPU"
(cd "$TMPU" && ls -l | grep -v '^total')
plutil -lint "$TMPU/info.plist"
for f in launch.sh filter.py; do
	[[ -x "$TMPU/$f" ]] || {
		echo "ERROR: $f lost +x in package!"
		exit 1
	}
done
rm -rf "$TMPU"
echo "✓ All executables keep +x inside the package. Ready to release."
