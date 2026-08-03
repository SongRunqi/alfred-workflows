#!/bin/zsh
# shellcheck disable=SC2168,SC2296
# launch.sh — Open pi/claude in a (configurable) terminal
#
# Input formats:
#   __new__|<dir>|<agent>             → start new session
#   <session_file>|<agent>|<dir>      → resume session
#   __finder__|pi                     → hotkey
#
# Terminal selection (optional, Alfred workflow env var AGENT_TERMINAL):
#   "iTerm" | "Terminal" | "kitty"     → NEW TAB in the running app
#                                         (Terminal needs Accessibility;
#                                          kitty needs a listen-enabled
#                                          instance; both fall back to a
#                                          new window)
#   "kitty <any> {file}"              → template with kitty: same logic as
#                                         "kitty" (compat with legacy config)
#   "<app name>"                      → open -a (new window)
#   "<template with {file}>"          → run as-is; {file} = session script
#   unset / empty                      → system default terminal (open)
set -euo pipefail

INPUT="${1:-}"

# ---- kitty launcher ----
# kitty on macOS facts:
#  1. Window-external remote control needs a socket. `allow_remote_control
#     yes` alone only enables control from inside a kitty window.
#  2. kitty.conf's `listen_on` works on macOS (kitty 0.48); it appends the
#     kitty PID to the socket name (unless {kitty_pid} is used), and only
#     takes effect after a restart.
#  3. `kitten @` without --to finds the instance via the controlling TTY,
#     so from Alfred (no TTY) it always fails with
#     "open /dev/tty: device not configured".
# Strategy: scan the listen_on socket glob and probe each one with
# `kitten @ --to`; if a controllable instance exists → new tab (activated).
# Otherwise launch a fresh instance via LaunchServices (`open -n`, so a
# running Dock-started instance is NOT activated with dropped args) with
# CLI args — NOT `kitty --detach`, which hangs headless from a background
# context (process alive, no window, no shell, no socket).
_launch_kitty() {
	local qf="$1"
	local kitty_args="--listen-on unix:/tmp/kitty-$(id -un)-{kitty_pid}.sock -o allow_remote_control=yes"
	local kitten_bin="/opt/homebrew/bin/kitten"
	[[ -x "$kitten_bin" ]] || kitten_bin="$(command -v kitten 2>/dev/null || echo kitten)"
	# find an existing controllable instance; kitty.conf's listen_on appends
	# the PID to the socket name, so probe each socket in the glob
	# (newest instance first: that is the one the user is most likely using)
	# NB: main script sets IFS='|' for arg parsing; restore word-splitting
	# here or the $(ls ...) list collapses into a single word
	setopt local_options null_glob
	local IFS=$' \t\n'
	local sock target=""
	for sock in $(ls -t /tmp/kitty-$(id -un)-*.sock 2>/dev/null); do
		[[ -S "$sock" ]] || continue
		if "$kitten_bin" @ --to "unix:$sock" ls >/dev/null 2>&1; then
			target="$sock"
			break
		fi
	done
	if [[ -n "$target" ]]; then
		# save current layout first, so the next kitty launch restores it
		# (kitty.conf startup_session points at this file)
		"$kitten_bin" @ --to "unix:$target" ls --output-format=session >"$HOME/.config/kitty/restore-session" 2>/dev/null || true
		echo "$kitten_bin @ --to unix:$target launch --type=tab zsh $qf"
	elif pgrep -x kitty >/dev/null 2>&1; then
		# kitty IS running but has no controllable socket (old instance
		# started before listen_on was added, or a broken one). NEVER pile
		# up another window on top of the user's — tell them instead.
		echo "osascript -e 'display notification \"kitty 未启用远程控制：请在 kitty.conf 添加 listen_on unix:/tmp/kitty-{kitty_pid}.sock 和 allow_remote_control yes，保存后退出并重新打开 kitty 一次，之后会话都会开新 tab\" with title \"PiHop\"'"
	else
		# no kitty at all → a new instance is the correct behavior
		echo "open -n -a kitty --args $kitty_args zsh $qf"
	fi
}

# ---- busy-claude detection ----
# If the session we are about to resume is already attached to a running
# claude process (status busy in ~/.claude/sessions/*.json), `claude
# --resume` refuses and exits with a "background agent" notice. Detect it
# and fork a copy instead, so the user lands in a working session.
_session_is_busy() {
	setopt local_options null_glob
	local sid="$1"
	local f
	for f in "$HOME"/.claude/sessions/*.json; do
		[[ -f "$f" ]] || continue
		if grep -q "\"sessionId\"[[:space:]]*:[[:space:]]*\"$sid\"" "$f" \
			&& grep -q "\"status\"[[:space:]]*:[[:space:]]*\"busy\"" "$f"; then
			return 0
		fi
	done
	return 1
}

# ---- parse ----
local dir="" agent="" mode="" session_file=""
local IFS='|'
local -a parts=("${(@s:|:)INPUT}")

case "${#parts[@]}" in
0 | 1)
	mode="finder"
	agent=""
	;;
2)
	mode="finder"
	agent="${parts[2]}"
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

# ---- default agent ----
# The hotkey trigger can't carry an argument reliably (Alfred normalizes
# it away on import), so finder mode falls back to the configured default
# agent instead of assuming pi.
if [[ "$mode" == "finder" && -z "$agent" ]]; then
	agent="${DEFAULT_AGENT:-pi}"
fi

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
			if _session_is_busy "$sid"; then
				cmd="cd ${(q)dir} && clear && echo '🟣 claude — ${name}（原会话在后台运行，已分支副本）' && claude --resume '${sid}' --fork-session; exec \${SHELL:-/bin/zsh}"
			else
				cmd="cd ${(q)dir} && clear && echo '🟣 claude — ${name}' && claude --resume '${sid}'; exec \${SHELL:-/bin/zsh}"
			fi
		else
			cmd="cd ${(q)dir} && clear && echo '🟣 claude — ${name}' && claude --continue; exec \${SHELL:-/bin/zsh}"
		fi
	else
		cmd="cd ${(q)dir} && clear && echo '🟣 claude — ${name}' && claude; exec \${SHELL:-/bin/zsh}"
	fi
	;;
*)
	if [[ "$mode" == "resume" && -f "$session_file" ]]; then
		cmd="cd ${(q)dir} && clear && echo '🟢 pi — ${name}' && pi --session ${(q)session_file}; exec \${SHELL:-/bin/zsh}"
	else
		cmd="cd ${(q)dir} && clear && echo '🟢 pi — ${name}' && pi; exec \${SHELL:-/bin/zsh}"
	fi
	;;
esac

# ---- resolve terminal (Alfred workflow env var) ----
local terminal="${AGENT_TERMINAL:-}"

# ---- launch ----
local tmpfile="/tmp/agent-session-$$.command"
cat >"$tmpfile" <<EOF
#!/bin/zsh
# self-delete once running (the shell keeps the fd; avoids the startup
# race where a slow terminal still needs the file)
trap 'rm -f "\$0"' EXIT
export PATH="\$HOME/.pi/agent/bin:/opt/homebrew/bin:\$PATH"
# Normalize proxy env vars. A GUI-launched terminal can inherit macOS system
# proxy settings as bare "host:port" (no scheme) — e.g. iTerm's process env
# carries http_proxy=127.0.0.1:7890. Node/undici builds a URL from it and dies
# with ERR_INVALID_URL before pi/claude ever starts, so add the scheme back.
for _pv in http_proxy https_proxy HTTP_PROXY HTTPS_PROXY; do
	_pval="\${(P)_pv:-}"
	[[ -n "\$_pval" && "\$_pval" != *://* ]] && export "\$_pv=http://\$_pval"
done
unset _pv _pval
$cmd
EOF
chmod +x "$tmpfile"

local termcmd=""
local qf="${(q)tmpfile}"
case "$terminal" in
iTerm | iterm)
	# Native AppleScript tab support, then bring iTerm to the front —
	# `create tab` alone runs the new tab in the background and the user
	# never sees it open.
	termcmd="osascript -e 'tell application \"iTerm\"' -e 'if (count of windows) > 0 then' -e 'tell current window to create tab with default profile command \"zsh $qf\"' -e 'else' -e 'create window with default profile command \"zsh $qf\"' -e 'end if' -e 'activate' -e 'end tell'"
	;;
Terminal | terminal)
	# Terminal.app has no native "new tab" API; GUI scripting needs
	# Accessibility permission. Falls back to a new window on failure.
	termcmd="osascript -e 'tell application \"Terminal\" to activate' -e 'delay 0.2' -e 'tell application \"System Events\" to keystroke \"t\" using command down' -e 'delay 0.3' -e 'tell application \"Terminal\" to do script \"zsh $qf\" in front window' 2>/dev/null || osascript -e 'tell application \"Terminal\" to do script \"zsh $qf\"'"
	;;
kitty)
termcmd="$(_launch_kitty "$qf")"
;;
ghostty)
# No remote-control / tab API (as of 1.x) — open a new window via
# ghostty's own -e flag through LaunchServices.
termcmd="open -a ghostty --args -e zsh $qf"
;;
*)
	if [[ -n "$terminal" && "$terminal" == *"{file}"* ]]; then
		if [[ "${terminal%% *}" == "kitty" ]]; then
			# legacy config "kitty --detach zsh {file}" → same as "kitty"
			termcmd="$(_launch_kitty "$qf")"
		else
			termcmd="${terminal//\{file\}/$qf}"
		fi
	elif [[ -n "$terminal" ]]; then
		termcmd="open -a ${(q)terminal} ${(q)tmpfile}"
	else
		termcmd="open ${(q)tmpfile}"
	fi
	;;
esac

if [[ -n "${AGENT_SESSION_TEST:-}" ]]; then
	echo "$termcmd"
	exit 0
fi

(eval "$termcmd") &
# safety net only: the script self-deletes once running
(sleep 60 && rm -f "$tmpfile") &
