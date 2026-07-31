#!/bin/zsh
# shellcheck disable=SC2168,SC2296
# launch.sh — Open pi/claude in default terminal
#
# Input formats:
#   __new__|<dir>|<agent>             → start new session
#   <session_file>|<agent>|<dir>      → resume session
#   __finder__|pi                     → hotkey
set -euo pipefail

INPUT="${1:-}"

# ---- parse ----
local dir="" agent="" mode="" session_file=""
local IFS='|'
local -a parts=("${(@s:|:)INPUT}")

case "${#parts[@]}" in
2)
	mode="finder"
	agent="${parts[2]:-pi}"
	;;
3)
	if [[ "${parts[1]}" == "__new__" ]]; then
		mode="new"
		dir="${parts[2]}"
		agent="${parts[3]:-pi}"
	else
		mode="resume"
		session_file="${parts[1]}"
		agent="${parts[2]:-pi}"
		dir="${parts[3]}"
	fi
	;;
*)
	echo "Invalid: $INPUT"
	exit 1
	;;
esac

# ---- resolve dir ----
if [[ "$mode" == "finder" ]]; then
	dir=$(osascript -e 'tell application "Finder" to if (count of windows) > 0 then POSIX path of (target of front window as alias)' 2>/dev/null || echo "$HOME")
elif [[ "$mode" == "resume" && ! -d "$dir" ]]; then
	dir=$(head -1 "$session_file" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null || echo "$HOME")
fi

dir="${dir/#\~/$HOME}"
[[ ! -d "$dir" ]] && {
	echo "Directory not found: $dir"
	exit 1
}
dir="$(cd "$dir" && pwd)"
local name="${dir:t}"

# ---- build command ----
local cmd=""
case "$agent" in
claude | cc)
	if [[ "$mode" == "resume" && -f "$session_file" ]]; then
		local sid
		sid=$(head -1 "$session_file" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sessionId',''))" 2>/dev/null || true)
		if [[ -n "$sid" ]]; then
			cmd="cd ${(q)dir} && clear && echo '🟣 claude — ${name}' && claude --resume '${sid}'; exec \$SHELL"
		else
			cmd="cd ${(q)dir} && clear && echo '🟣 claude — ${name}' && claude --continue; exec \$SHELL"
		fi
	else
		cmd="cd ${(q)dir} && clear && echo '🟣 claude — ${name}' && claude; exec \$SHELL"
	fi
	;;
*)
	if [[ "$mode" == "resume" && -f "$session_file" ]]; then
		cmd="cd ${(q)dir} && clear && echo '🟢 pi — ${name}' && pi --session ${(q)session_file}; exec \$SHELL"
	else
		cmd="cd ${(q)dir} && clear && echo '🟢 pi — ${name}' && pi; exec \$SHELL"
	fi
	;;
esac

# ---- launch ----
local tmpfile="/tmp/agent-session-$$.command"
cat >"$tmpfile" <<EOF
#!/bin/zsh
$cmd
EOF
chmod +x "$tmpfile"
open "$tmpfile"
(sleep 5 && rm -f "$tmpfile") &
