#!/bin/bash
# Pulse release packer: rebuild plist + icon, zip runtime files,
# verify +x bits and plist.
#
# Usage: ./pack.sh        (from this folder, or anywhere — resolves itself)

set -euo pipefail
cd "$(dirname "$0")"

OUT="$(cd .. && pwd)/Pulse.alfredworkflow"

python3 build_plist.py
python3 make_icon.py
chmod +x pulse.py filter.sh update.sh notify.sh

rm -f "$OUT"
zip -q -r -X "$OUT" pulse.py filter.sh update.sh notify.sh icon.png info.plist

echo "✓ Packed: $OUT"
TMPU="$(mktemp -d)"
unzip -q "$OUT" -d "$TMPU"
(cd "$TMPU" && ls -l | grep -v '^total')
plutil -lint "$TMPU/info.plist"
for f in pulse.py filter.sh update.sh notify.sh; do
	[[ -x "$TMPU/$f" ]] || { echo "ERROR: $f lost +x in package!"; exit 1; }
done
rm -rf "$TMPU"
echo "✓ All executables keep +x inside the package. Ready to release."
