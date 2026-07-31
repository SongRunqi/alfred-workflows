#!/usr/bin/env node

/**
 * Alfred Run Script — executes a NetEase Music control action.
 *
 * The action id is received as the first argument (Alfred's `{query}`).
 * On success a macOS notification is posted; on failure the error is
 * shown via Alfred's notification mechanism.
 */

const { runAction, formatError } = require("./actions");

async function main() {
  const actionId = (process.argv[2] || "").trim();

  if (!actionId) {
    console.error("No action specified");
    process.exit(1);
  }

  const result = await runAction(actionId);

  if (result.ok) {
    // Post a success notification via osascript
    const { execFile } = require("node:child_process");
    const { promisify } = require("node:util");
    const execFileAsync = promisify(execFile);
    try {
      await execFileAsync("/usr/bin/osascript", [
        "-e",
        `display notification "Action completed" with title "NetEase Music" sound name "Pop"`,
      ]);
    } catch {
      // Notification failure is non-fatal
    }
  } else {
    // Output failure so Alfred can show it
    console.log(result.message);
  }
}

main().catch((err) => {
  console.error(formatError(err));
  process.exit(1);
});
