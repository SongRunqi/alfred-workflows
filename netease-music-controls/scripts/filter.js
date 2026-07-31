#!/usr/bin/env node

/**
 * Alfred Script Filter for NetEase Music Controls.
 *
 * Outputs a JSON array of Alfred items — one per control action.  When the
 * user types a keyword Alfred passes the query as the first argument; this
 * script filters the list accordingly (case-insensitive match on title,
 * subtitle, section, or keywords).
 *
 * Usage in Alfred Script Filter:
 *   /usr/bin/env node scripts/filter.js "$1"
 *
 * An `alfred_icon` environment variable may be set to the workflow's
 * icon path so every item gets the correct icon.
 */

const { ACTIONS, alfredItem } = require("./actions");

// ---------------------------------------------------------------------------
// Build the item list
// ---------------------------------------------------------------------------

const iconPath = process.env.alfred_icon || "icon.png";

/** All actions as flat Alfred items, grouped by section. */
const actionIds = Object.keys(ACTIONS);

// Sections in display order
const sectionOrder = ["Playback", "Volume", "Favorites", "Repeat", "Playback Mode", "Other"];

// Build a lookup: section → action ids
const bySection = {};
for (const id of actionIds) {
  const section = ACTIONS[id].section || "Other";
  if (!bySection[section]) bySection[section] = [];
  bySection[section].push(id);
}

// Flatten in section-order, adding a pseudo section-header item.
const items = [];
for (const section of sectionOrder) {
  const ids = bySection[section];
  if (!ids || ids.length === 0) continue;

  for (const id of ids) {
    const a = ACTIONS[id];
    items.push(
      alfredItem({
        uid: id,
        title: a.title,
        subtitle: `${section} — ${a.subtitle}`,
        arg: id,
        icon: iconPath,
        autocomplete: a.title,
      }),
    );
  }
}

// ---------------------------------------------------------------------------
// Optional filtering
// ---------------------------------------------------------------------------

function matches(query, action) {
  if (!query) return true;
  const q = query.toLowerCase();
  // Build a single searchable blob
  const blob = [action.title, action.subtitle, action.section || "", action.id]
    .join(" ")
    .toLowerCase();
  return blob.includes(q);
}

const query = (process.argv[2] || "").trim();
const filtered = query ? items.filter((item) => matches(query, ACTIONS[item.uid])) : items;

// If the query is empty, insert a placeholder at the top so the user sees
// something friendly.
if (!query) {
  filtered.unshift(
    alfredItem({
      uid: "_placeholder",
      title: "Search NetEase Music controls…",
      subtitle: `${filtered.length} actions available — start typing to filter`,
      arg: "_placeholder",
      icon: iconPath,
      valid: false,
      autocomplete: "",
    }),
  );
}

// ---------------------------------------------------------------------------
// Output
// ---------------------------------------------------------------------------

process.stdout.write(JSON.stringify({ items: filtered }, null, 2));
