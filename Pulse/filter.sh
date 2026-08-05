#!/bin/sh
# `update` keyword entry: emits the script-filter JSON.
exec "$(dirname "$0")/pulse.py" filter "$1"
