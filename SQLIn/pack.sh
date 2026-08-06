#!/bin/bash
# SQL In release packer: rebuild plist + icon, zip runtime files,
# verify +x bits and plist.
#
# Usage: ./pack.sh        (from this folder, or anywhere — resolves itself)

set -euo pipefail
cd "$(dirname "$0")"

OUT="$(cd .. && pwd)/SQL In.alfredworkflow"

python3 build_plist.py
python3 make_icon.py
chmod +x sql_in.py

rm -f "$OUT"
zip -q -r -X "$OUT" sql_in.py icon.png info.plist

echo "✓ Packed: $OUT"
TMPU="$(mktemp -d)"
unzip -q "$OUT" -d "$TMPU"
(cd "$TMPU" && ls -l | grep -v '^total')
plutil -lint "$TMPU/info.plist"
[[ -x "$TMPU/sql_in.py" ]] || {
	echo "ERROR: sql_in.py lost +x in package!"
	exit 1
}
rm -rf "$TMPU"
echo "✓ sql_in.py keeps +x inside the package. Ready to release."
