#!/bin/bash
# Alfred Run Script — execute a NetEase Music control action via AppleScript.
# Usage: runner.sh <action-id>
set -euo pipefail

ACTION="${1:-}"

# ---------------------------------------------------------------------------
# Helper: run an AppleScript snippet inside a "tell process NeteaseMusic"
# block.  Launches the app first if it's not already running.
# ---------------------------------------------------------------------------
run_applescript() {
	local snippet="$1"
	osascript -e "
    -- Locate or launch NetEase Music
    set procName to missing value
    tell application \"System Events\"
      repeat with n in {\"NeteaseMusic\", \"NetEaseMusic\", \"网易云音乐\"}
        if exists process (contents of n) then
          set procName to contents of n
          exit repeat
        end if
      end repeat
    end tell
    if procName is missing value then
      try
        do shell script \"open -gj -b com.netease.163music\"
      on error
        try
          do shell script \"open -gj -a NetEaseMusic\"
        end try
      end try
      delay 1.5
      tell application \"System Events\"
        repeat with n in {\"NeteaseMusic\", \"NetEaseMusic\", \"网易云音乐\"}
          if exists process (contents of n) then
            set procName to contents of n
            exit repeat
          end if
        end repeat
      end tell
    end if
    if procName is missing value then error \"Could not launch NetEase Music\"

    tell application \"System Events\"
      tell process procName
        ${snippet}
      end tell
    end tell
  "
}

# ---------------------------------------------------------------------------
# Click a menu item in the Controls (播放控制) menu
# ---------------------------------------------------------------------------
click_control() {
	local candidates_str="$1"
	local snippet
	snippet=$(
		cat <<EOF
    set done to false
    repeat with ctrlName in {"Controls", "控制", "播放控制"}
      if exists menu bar item (contents of ctrlName) of menu bar 1 then
        set m to menu 1 of menu bar item (contents of ctrlName) of menu bar 1
        repeat with itemName in {${candidates_str}}
          if exists menu item (contents of itemName) of m then
            click menu item (contents of itemName) of m
            set done to true
            exit repeat
          end if
        end repeat
      end if
      if done then exit repeat
    end repeat
EOF
	)
	run_applescript "$snippet"
}

# ---------------------------------------------------------------------------
# Click a menu item in the View (显示/查看) menu
# ---------------------------------------------------------------------------
click_view() {
	local candidates_str="$1"
	local snippet
	snippet=$(
		cat <<EOF
    set done to false
    repeat with vName in {"View", "显示", "查看"}
      if exists menu bar item (contents of vName) of menu bar 1 then
        set m to menu 1 of menu bar item (contents of vName) of menu bar 1
        repeat with itemName in {${candidates_str}}
          if exists menu item (contents of itemName) of m then
            click menu item (contents of itemName) of m
            set done to true
            exit repeat
          end if
        end repeat
      end if
      if done then exit repeat
    end repeat
EOF
	)
	run_applescript "$snippet"
}

# ---------------------------------------------------------------------------
# Click a repeat submenu item
# ---------------------------------------------------------------------------
click_repeat() {
	local candidate_str="$1"
	local snippet
	snippet=$(
		cat <<EOF
    set done to false
    repeat with ctrlName in {"Controls", "控制", "播放控制"}
      if exists menu bar item (contents of ctrlName) of menu bar 1 then
        set ctrlMenu to menu 1 of menu bar item (contents of ctrlName) of menu bar 1
        repeat with repName in {"Repeat", "重复", "循环", "播放模式"}
          if exists menu item (contents of repName) of ctrlMenu then
            set repMenu to menu 1 of menu item (contents of repName) of ctrlMenu
            repeat with modeName in {${candidate_str}}
              if exists menu item (contents of modeName) of repMenu then
                click menu item (contents of modeName) of repMenu
                set done to true
                exit repeat
              end if
            end repeat
          end if
          if done then exit repeat
        end repeat
      end if
      if done then exit repeat
    end repeat
EOF
	)
	run_applescript "$snippet"
}

# ===========================================================================
# Action dispatch
# ===========================================================================
case "$ACTION" in

toggle-play)
	click_control '"Play", "Pause", "播放", "暂停"'
	;;

next-track)
	click_control '"Next Track", "Next", "下一首", "下一曲"'
	;;

previous-track)
	click_control '"Previous Track", "Previous", "上一首", "上一曲"'
	;;

turn-up-volume)
	click_control '"Increase Volume", "Volume Up", "增大音量", "调高音量"'
	;;

turn-down-volume)
	click_control '"Decrease Volume", "Volume Down", "减小音量", "调低音量"'
	;;

like | dislike)
	click_control '"Like", "Love", "Favorite", "Dislike", "Unlike", "Cancel Like", "喜欢", "红心", "添加到我喜欢的音乐", "取消喜欢", "取消红心", "不喜欢"'
	;;

toggle-shuffle)
	click_control '"Shuffle", "Shuffle Playback", "随机播放", "随机"'
	;;

toggle-lyrics)
	click_view '"Show/Hide Lyrics", "Show Lyrics", "Hide Lyrics", "显示/隐藏歌词", "显示歌词", "隐藏歌词", "桌面歌词"'
	;;

repeat-one)
	click_repeat '"One", "Repeat One", "单曲", "单曲循环"'
	;;

repeat-off)
	click_repeat '"Off", "None", "关闭", "关", "不重复"'
	;;

repeat-all)
	click_repeat '"All", "Repeat All", "全部", "列表循环"'
	;;

*)
	echo "Unknown action: $ACTION" >&2
	exit 1
	;;
esac
