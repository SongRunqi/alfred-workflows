#!/bin/sh
# `pulselist` list entry: emits the full update-list script-filter JSON.
exec "$(dirname "$0")/pulse.py" filter "$1"
