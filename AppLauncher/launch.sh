#!/bin/sh
# Hotkey / management entry: argv[1] is the key (hotkey argumenttext) or a
# management command string from the script filter ("add o Obsidian").
exec "$(dirname "$0")/app.py" "$1"
