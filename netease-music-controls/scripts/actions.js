#!/usr/bin/env node

/**
 * NetEase Music Controls for Alfred
 *
 * Ported from the Raycast extension. Controls the macOS NetEase Music app
 * via AppleScript (System Events accessibility API) — clicking menu bar
 * items directly, the same way the Raycast extension does.
 */

const { execFile } = require("node:child_process");
const { promisify } = require("node:util");

const execFileAsync = promisify(execFile);

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PROCESS_NAMES = ["NeteaseMusic", "NetEaseMusic", "网易云音乐"];
const CONTROL_MENU_NAMES = ["Controls", "控制", "播放控制"];
const VIEW_MENU_NAMES = ["View", "显示", "查看"];
const TOUCH_BAR_MENU_NAMES = [...CONTROL_MENU_NAMES, ...VIEW_MENU_NAMES];
const REPEAT_MENU_CANDIDATES = ["Repeat", "重复", "循环", "播放模式"];

const MENU_ITEM_KIND = "menu-item";
const REPEAT_KIND = "repeat";

// ---------------------------------------------------------------------------
// Action definitions
// ---------------------------------------------------------------------------

/** @type {Record<string, import('./types').ActionDefinition>} */
const ACTIONS = {
  play: {
    id: "play",
    kind: MENU_ITEM_KIND,
    title: "Play",
    subtitle: "Start or resume playback",
    section: "Playback",
    candidates: ["Play", "Resume", "播放", "继续播放"],
    allowMissingAsSuccess: true,
  },
  stop: {
    id: "stop",
    kind: MENU_ITEM_KIND,
    title: "Stop",
    subtitle: "Stop playback by pausing",
    section: "Playback",
    candidates: ["Pause", "Stop", "暂停", "停止"],
    allowMissingAsSuccess: true,
  },
  "toggle-play": {
    id: "toggle-play",
    kind: MENU_ITEM_KIND,
    title: "Toggle Play/Pause",
    subtitle: "Switch between play and pause",
    section: "Playback",
    candidates: ["Play", "Pause", "Resume", "播放", "暂停", "继续播放"],
  },
  "next-track": {
    id: "next-track",
    kind: MENU_ITEM_KIND,
    title: "Next Track",
    subtitle: "Skip to the next track",
    section: "Playback",
    candidates: ["Next", "Next Track", "下一首", "下一曲"],
  },
  "previous-track": {
    id: "previous-track",
    kind: MENU_ITEM_KIND,
    title: "Previous Track",
    subtitle: "Go back to the previous track",
    section: "Playback",
    candidates: ["Previous", "Previous Track", "上一首", "上一曲"],
  },
  "turn-up-volume": {
    id: "turn-up-volume",
    kind: MENU_ITEM_KIND,
    title: "Increase Volume",
    subtitle: "Turn NetEase Music up",
    section: "Volume",
    candidates: ["Increase Volume", "Volume Up", "增大音量", "调高音量", "音量增大"],
  },
  "turn-down-volume": {
    id: "turn-down-volume",
    kind: MENU_ITEM_KIND,
    title: "Decrease Volume",
    subtitle: "Turn NetEase Music down",
    section: "Volume",
    candidates: ["Decrease Volume", "Volume Down", "减小音量", "调低音量", "音量减小"],
  },
  like: {
    id: "like",
    kind: MENU_ITEM_KIND,
    title: "Like Track",
    subtitle: "Like the current track",
    section: "Favorites",
    candidates: ["Like", "Love", "Favorite", "喜欢", "红心", "添加到我喜欢的音乐"],
    allowMissingAsSuccess: true,
  },
  dislike: {
    id: "dislike",
    kind: MENU_ITEM_KIND,
    title: "Dislike Track",
    subtitle: "Dislike or unlike the current track",
    section: "Favorites",
    candidates: ["Dislike", "Unlike", "Unfavorite", "Cancel Like", "取消喜欢", "取消红心", "不喜欢", "取消收藏"],
    allowMissingAsSuccess: true,
  },
  "repeat-off": {
    id: "repeat-off",
    kind: REPEAT_KIND,
    title: "Repeat Off",
    subtitle: "Turn repeat off",
    section: "Repeat",
    modeCandidates: ["Off", "None", "关闭", "关", "不重复", "关闭重复"],
  },
  "repeat-one": {
    id: "repeat-one",
    kind: REPEAT_KIND,
    title: "Repeat One",
    subtitle: "Repeat the current track",
    section: "Repeat",
    modeCandidates: ["One", "Repeat One", "单曲", "单曲循环"],
  },
  "repeat-all": {
    id: "repeat-all",
    kind: REPEAT_KIND,
    title: "Repeat All",
    subtitle: "Repeat all tracks",
    section: "Repeat",
    modeCandidates: ["All", "Repeat All", "全部", "列表循环", "全部重复"],
  },
  "toggle-shuffle": {
    id: "toggle-shuffle",
    kind: MENU_ITEM_KIND,
    title: "Shuffle",
    subtitle: "Toggle shuffle playback",
    section: "Playback Mode",
    candidates: ["Shuffle", "Shuffle Playback", "随机播放", "随机"],
  },
  "toggle-lyrics": {
    id: "toggle-lyrics",
    kind: MENU_ITEM_KIND,
    title: "Show/Hide Lyrics",
    subtitle: "Toggle the lyrics window",
    section: "Other",
    candidates: ["Show/Hide Lyrics", "Show Lyrics", "Hide Lyrics", "显示/隐藏歌词", "显示歌词", "隐藏歌词", "桌面歌词"],
  },
  "customize-touch-bar": {
    id: "customize-touch-bar",
    kind: MENU_ITEM_KIND,
    title: "Customize Touch Bar",
    subtitle: "Open NetEase Music's Touch Bar customizer",
    section: "Other",
    menuCandidates: TOUCH_BAR_MENU_NAMES,
    candidates: [
      "Customize Touch Bar",
      "Customize Touch Bar…",
      "Customize Touch Bar...",
      "自定触控栏",
      "自定触控栏…",
      "自定义触控栏",
    ],
  },
};

// ---------------------------------------------------------------------------
// AppleScript builders
// ---------------------------------------------------------------------------

/**
 * Generate the full AppleScript for a menu item action.
 */
function buildMenuItemScript(menuCandidates, candidates, allowMissingAsSuccess) {
  const missingMenuAction = `error ${appleString(`Menu not found: ${menuCandidates.join(" / ")}`)}`;
  const missingItemAction = allowMissingAsSuccess
    ? 'return "OK:NOOP"'
    : `error ${appleString(`Menu item not found: ${candidates.join(" / ")}`)}`;

  return baseScript(`
    ${findMenuItemInMenuBar("actionMenu", "actionMenuFound", "actionName", menuCandidates, candidates)}
    if actionMenuFound is false then
      ${missingMenuAction}
    end if
    if actionName is missing value then
      ${missingItemAction}
    end if
    perform action "AXPress" of menu item actionName of actionMenu
    return "OK:" & actionName
  `);
}

/**
 * Generate the full AppleScript for a repeat-mode action.
 */
function buildRepeatScript(modeCandidates) {
  return baseScript(`
    ${findMenuBarMenu("controlsMenu", "controlsName", CONTROL_MENU_NAMES)}
    if controlsName is missing value then error "Controls menu not found"
    ${findMenuItem("repeatName", "controlsMenu", REPEAT_MENU_CANDIDATES)}
    if repeatName is missing value then error "Repeat menu not found"
    set repeatMenu to menu 1 of menu item repeatName of controlsMenu
    ${findMenuItem("modeName", "repeatMenu", modeCandidates)}
    if modeName is missing value then error ${appleString(`Repeat mode not found: ${modeCandidates.join(" / ")}`)}
    perform action "AXPress" of menu item modeName of repeatMenu
    return "OK:" & repeatName & "/" & modeName
  `);
}

// ---- AppleScript helpers ---- //

function findMenuItemInMenuBar(menuVar, foundVar, itemVar, menuCandidates, itemCandidates) {
  return `
    set ${menuVar} to missing value
    set ${foundVar} to false
    set ${itemVar} to missing value
    repeat with candidateMenuName in ${appleList(menuCandidates)}
      if exists menu bar item (contents of candidateMenuName) of menu bar 1 then
        set ${foundVar} to true
        set candidateMenu to menu 1 of menu bar item (contents of candidateMenuName) of menu bar 1
        repeat with candidateItemName in ${appleList(itemCandidates)}
          if exists menu item (contents of candidateItemName) of candidateMenu then
            set ${menuVar} to candidateMenu
            set ${itemVar} to contents of candidateItemName
            exit repeat
          end if
        end repeat
      end if
      if ${itemVar} is not missing value then exit repeat
    end repeat
  `;
}

function findMenuBarMenu(menuVar, nameVar, candidates) {
  return `
    set ${menuVar} to missing value
    set ${nameVar} to missing value
    repeat with candidateName in ${appleList(candidates)}
      if exists menu bar item (contents of candidateName) of menu bar 1 then
        set ${nameVar} to contents of candidateName
        set ${menuVar} to menu 1 of menu bar item ${nameVar} of menu bar 1
        exit repeat
      end if
    end repeat
  `;
}

function findMenuItem(varName, menuVar, candidates) {
  return `
    set ${varName} to missing value
    repeat with candidateName in ${appleList(candidates)}
      if exists menu item (contents of candidateName) of ${menuVar} then
        set ${varName} to contents of candidateName
        exit repeat
      end if
    end repeat
  `;
}

/**
 * Common preamble: locate or launch NetEase Music, then execute the
 * action body inside a `tell process` block.
 */
function baseScript(actionBody) {
  return `
    on launchNetEaseMusic()
      try
        do shell script "open -gj -b com.netease.163music"
      on error
        try
          do shell script "open -gj -a NetEaseMusic"
        on error
          try
            do shell script "open -gj -a NeteaseMusic"
          end try
        end try
      end try
    end launchNetEaseMusic

    set processName to missing value

    tell application "System Events"
      repeat with candidateName in ${appleList(PROCESS_NAMES)}
        if exists process (contents of candidateName) then
          set processName to contents of candidateName
          exit repeat
        end if
      end repeat
    end tell

    if processName is missing value then
      my launchNetEaseMusic()
      delay 1
      tell application "System Events"
        repeat with candidateName in ${appleList(PROCESS_NAMES)}
          if exists process (contents of candidateName) then
            set processName to contents of candidateName
            exit repeat
          end if
        end repeat
      end tell
    end if
    if processName is missing value then error "NetEase Music is not running or could not be launched"

    tell application "System Events"
      tell process processName
        ${actionBody}
      end tell
    end tell
  `;
}

// ---- Low-level escaping utilities ---- //

function appleList(values) {
  return `{${values.map(appleString).join(", ")}}`;
}

function appleString(value) {
  return `"${value.replace(/\\\\/g, "\\\\\\\\").replace(/"/g, '\\\\"')}"`;
}

// ---------------------------------------------------------------------------
// Runner
// ---------------------------------------------------------------------------

/**
 * Execute the AppleScript for the given action id.
 * @param {string} id
 * @returns {Promise<{ok: boolean, message: string}>}
 */
async function runAction(id) {
  const action = ACTIONS[id];
  if (!action) {
    return { ok: false, message: `Unknown action: ${id}` };
  }

  let script;
  if (action.kind === REPEAT_KIND) {
    script = buildRepeatScript(action.modeCandidates);
  } else {
    script = buildMenuItemScript(
      action.menuCandidates ?? CONTROL_MENU_NAMES,
      action.candidates,
      action.allowMissingAsSuccess ?? false,
    );
  }

  try {
    const result = await runAppleScript(script);
    return { ok: true, message: result };
  } catch (error) {
    return { ok: false, message: formatError(error) };
  }
}

/**
 * Run an AppleScript string via /usr/bin/osascript.
 */
async function runAppleScript(script) {
  const args = script
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .flatMap((line) => ["-e", line]);

  const { stdout, stderr } = await execFileAsync("/usr/bin/osascript", args, { timeout: 8000 });
  if (stderr.trim().length > 0) {
    throw new Error(stderr.trim());
  }
  return stdout.trim();
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function formatError(error) {
  if (error instanceof Error) return error.message;
  return String(error);
}

/** Emit an Alfred JSON item. */
function alfredItem(opts) {
  return {
    uid: opts.uid,
    title: opts.title,
    subtitle: opts.subtitle ?? "",
    arg: opts.arg ?? opts.uid,
    icon: opts.icon ? { path: opts.icon } : undefined,
    autocomplete: opts.autocomplete ?? opts.title,
    valid: opts.valid ?? true,
  };
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = {
  ACTIONS,
  runAction,
  runAppleScript,
  formatError,
  alfredItem,
};
