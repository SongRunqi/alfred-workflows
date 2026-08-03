// Window Control geometry engine.
//
// Resizes/moves the frontmost app's focused window via the Accessibility API.
// Geometry is computed from the window's own screen:
//   - top:   macOS clamps window tops to below the menu bar; the engine reads
//            the menu bar height directly from the window list (no probing
//            moves).
//   - bottom: the physical screen bottom when the Dock is auto-hidden
//            (com.apple.dock autohide), otherwise the visible-frame bottom
//            (Dock strip respected).
//
// Animation is hybrid (measured on Chrome/TextEdit): the size is set ONCE —
// apps render a single AX resize as their own smooth ~250ms morph — while the
// position glides in eased steps (pure moves are compositor-only and render
// smoothly on every app). Settlement is verified against the WINDOW SERVER
// (CGWindowList bounds), not the AX attribute: AX reports the requested value
// instantly ("promise"), long before the app finished rendering, so an AX
// check lets the next action pile onto a busy app — the stutter you see.
//
// Modes: max | reasonable | center | tl | tr | bl | br
// Prints nothing on success; prints an error message on failure (Alfred
// surfaces it as a notification). Coordinates are in the global display
// space (top-left origin of the primary display, y down) — the same space
// NSScreen frames use.
//
// Build: swiftc -O -framework AppKit -framework ApplicationServices window_control.swift -o window_control

import Cocoa
import ApplicationServices

let reasonableWidthFraction: CGFloat = 2.0 / 3.0
let reasonableHeightFraction: CGFloat = 2.0 / 3.0
let tolerance: CGFloat = 3.0

func fail(_ message: String) -> Never {
    print(message)
    exit(1)
}

// --- AX helpers -------------------------------------------------------------

func copyAttribute(_ element: AXUIElement, _ attribute: CFString) -> CFTypeRef? {
    var ref: CFTypeRef?
    guard AXUIElementCopyAttributeValue(element, attribute, &ref) == .success else { return nil }
    return ref
}

func windowFrame(_ window: AXUIElement) -> CGRect? {
    guard let posRef = copyAttribute(window, kAXPositionAttribute as CFString),
          CFGetTypeID(posRef) == AXValueGetTypeID(),
          let sizeRef = copyAttribute(window, kAXSizeAttribute as CFString),
          CFGetTypeID(sizeRef) == AXValueGetTypeID() else {
        return nil
    }
    let posVal = posRef as! AXValue  // swiftlint:disable:this force_cast — type id verified above
    let sizeVal = sizeRef as! AXValue  // swiftlint:disable:this force_cast — type id verified above
    var point = CGPoint.zero
    var size = CGSize.zero
    guard AXValueGetValue(posVal, .cgPoint, &point),
          AXValueGetValue(sizeVal, .cgSize, &size) else { return nil }
    return CGRect(origin: point, size: size)
}

func setPosition(_ window: AXUIElement, _ point: CGPoint) {
    var value = point
    if let axValue = AXValueCreate(.cgPoint, &value) {
        AXUIElementSetAttributeValue(window, kAXPositionAttribute as CFString, axValue)
    }
}

func setSize(_ window: AXUIElement, _ size: CGSize) {
    var value = size
    if let axValue = AXValueCreate(.cgSize, &value) {
        AXUIElementSetAttributeValue(window, kAXSizeAttribute as CFString, axValue)
    }
}

func frameMatches(_ current: CGRect, _ target: CGRect) -> Bool {
    abs(current.minX - target.minX) <= tolerance
        && abs(current.minY - target.minY) <= tolerance
        && abs(current.width - target.width) <= tolerance
        && abs(current.height - target.height) <= tolerance
}

// Rectangle's trick (PR #285): apps with AXEnhancedUserInterface enabled
// render AX resizes as a smooth animated morph and may not land exactly.
// Disable it for the duration of the operation, then restore (Chrome ships
// with it enabled — disabling turns its ~1.5s morph into an instant resize).
func withEnhancedUIDisabled<T>(_ appElement: AXUIElement, _ body: () -> T) -> T {
    var wasEnabled = false
    if let ref = copyAttribute(appElement, "AXEnhancedUserInterface" as CFString),
       CFGetTypeID(ref) == CFBooleanGetTypeID(),
       CFBooleanGetValue((ref as! CFBoolean)) {  // swiftlint:disable:this force_cast — type id verified above
        wasEnabled = true
        AXUIElementSetAttributeValue(appElement, "AXEnhancedUserInterface" as CFString, kCFBooleanFalse)
        usleep(50_000)
    }
    defer {
        if wasEnabled {
            AXUIElementSetAttributeValue(appElement, "AXEnhancedUserInterface" as CFString, kCFBooleanTrue)
        }
    }
    return body()
}

// --- Window Server helpers --------------------------------------------------
// The window server's bounds are the on-screen truth: AX attributes report the
// requested value immediately, but the app renders asynchronously. Settlement
// is verified against the server so the next action never piles onto a busy
// app.

func windowServerID(for pid: pid_t, matching frame: CGRect) -> CGWindowID? {
    let list = CGWindowListCopyWindowInfo(
        [.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
    var best: (CGWindowID, CGFloat) = (0, .greatestFiniteMagnitude)
    for window in list {
        guard let owner = window[kCGWindowOwnerPID as String] as? Int, owner == Int(pid),
              let layer = window[kCGWindowLayer as String] as? Int, layer == 0,
              let bounds = window[kCGWindowBounds as String] as? [String: CGFloat],
              let number = window[kCGWindowNumber as String] as? Int else { continue }
        let winBounds = CGRect(x: bounds["X"] ?? 0, y: bounds["Y"] ?? 0,
                              width: bounds["Width"] ?? 0, height: bounds["Height"] ?? 0)
        let distance = abs(winBounds.minX - frame.minX) + abs(winBounds.minY - frame.minY)
            + abs(winBounds.width - frame.width) + abs(winBounds.height - frame.height)
        if distance < best.1 {
            best = (CGWindowID(number), distance)
        }
    }
    // The window must be the one we're about to move (within half its size).
    return best.1 < max(frame.width, frame.height) / 2 ? best.0 : nil
}

func windowServerFrame(_ windowID: CGWindowID) -> CGRect? {
    let list = CGWindowListCopyWindowInfo(
        [.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
    for window in list {
        guard let number = window[kCGWindowNumber as String] as? Int, number == Int(windowID),
              let bounds = window[kCGWindowBounds as String] as? [String: CGFloat] else { continue }
        return CGRect(x: bounds["X"] ?? 0, y: bounds["Y"] ?? 0,
                      width: bounds["Width"] ?? 0, height: bounds["Height"] ?? 0)
    }
    return nil
}

// --- Frame application ------------------------------------------------------

// Poll until the window really is where we asked, up to timeoutMs, against
// the WINDOW SERVER (CGWindowList) — the on-screen truth. Falls back to the
// AX attribute when the window has no on-screen server entry (e.g. minimized).
func waitForFrame(_ window: AXUIElement, _ rect: CGRect,
                  windowID: CGWindowID?, timeoutMs: Int) -> Bool {
    let deadline = Date().addingTimeInterval(Double(timeoutMs) / 1000)
    while Date() < deadline {
        if let windowID, let server = windowServerFrame(windowID), frameMatches(server, rect) {
            return true
        }
        if windowID == nil, let current = windowFrame(window), frameMatches(current, rect) {
            return true
        }
        usleep(50_000)
    }
    return false
}

// Rectangle-style placement: size -> position -> size, back-to-back. Apps
// merge the rapid requests into a single visual step (measured on Chrome:
// position and size land together in ~50-90ms, exactly), which is what makes
// it feel like one motion instead of "move, then resize". The trailing size
// corrects macOS clamping the size to the current display. The window server
// is then polled as a safety net so the next action never piles onto a busy
// app; one gentle retry if the app drifted.
func settleFrame(_ window: AXUIElement, _ rect: CGRect, windowID: CGWindowID?) {
    setSize(window, rect.size)
    setPosition(window, rect.origin)
    setSize(window, rect.size)
    if waitForFrame(window, rect, windowID: windowID, timeoutMs: 1500) { return }
    setSize(window, rect.size)
    setPosition(window, rect.origin)
    setSize(window, rect.size)
    _ = waitForFrame(window, rect, windowID: windowID, timeoutMs: 1200)
}

// Smooth transition from the current frame to the target.
//
// Hybrid strategy (measured): per-step size interpolation stutters because
// apps batch/coalesce rapid AX resizes — a SINGLE size change renders as the
// app's own smooth morph. So actions with a big size change (max, reasonable)
// skip the glide entirely and let the app morph; actions that only move
// (corners, center) glide the position in eased steps (~150ms), since pure
// moves are compositor-only and render smoothly everywhere. Skips when the
// change is negligible and respects the system Reduce Motion setting.
func animateFrame(_ window: AXUIElement, from start: CGRect, to target: CGRect,
                  windowID: CGWindowID?) {
    if frameMatches(start, target) { return }
    let sizeDelta = abs(target.width - start.width) + abs(target.height - start.height)
    let positionDelta = abs(target.minX - start.minX) + abs(target.minY - start.minY)
    if !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        && sizeDelta < 200 && positionDelta > 10 {
        let steps = 12
        for step in 1...steps {
            let progress = CGFloat(step) / CGFloat(steps)
            let eased = 1 - pow(1 - progress, 3)  // easeOutCubic: fast start, gentle landing
            setPosition(window, CGPoint(
                x: start.minX + (target.minX - start.minX) * eased,
                y: start.minY + (target.minY - start.minY) * eased))
            usleep(12_000)
        }
    }
    settleFrame(window, target, windowID: windowID)
}

// --- Main -------------------------------------------------------------------

let args = CommandLine.arguments
guard args.count > 1 else { fail("usage: window_control <max|reasonable|center|tl|tr|bl|br> [animate 0|1]") }
let mode = args[1]
let animate = args.count > 2 ? args[2] != "0" : true

guard AXIsProcessTrusted() else {
    fail("Alfred 缺少「辅助功能」权限：系统设置 → 隐私与安全性 → 辅助功能 → 勾选 Alfred")
}

guard let app = NSWorkspace.shared.frontmostApplication else { fail("没有前台应用") }
let axApp = AXUIElementCreateApplication(app.processIdentifier)

// Focused window, falling back to main window, then the first window.
var windowRef: CFTypeRef?
if AXUIElementCopyAttributeValue(axApp, kAXFocusedWindowAttribute as CFString, &windowRef) != .success {
    if AXUIElementCopyAttributeValue(axApp, kAXMainWindowAttribute as CFString, &windowRef) != .success,
       let windows = copyAttribute(axApp, kAXWindowsAttribute as CFString) as? [AXUIElement] {
        windowRef = windows.first
    }
}
guard let windowRef else { fail("前台应用没有可操作的窗口") }
// swiftlint:disable:next force_cast — kAX*Window attributes return AXUIElement
let window = windowRef as! AXUIElement

guard let current = windowFrame(window) else { fail("无法读取窗口位置") }
let windowID = windowServerID(for: app.processIdentifier, matching: current)

// The screen the window mostly sits on; fall back to the primary display.
func area(_ rect: CGRect) -> CGFloat { rect.width * rect.height }
let screen = NSScreen.screens.max(by: {
    area($0.frame.intersection(current)) < area($1.frame.intersection(current))
}) ?? NSScreen.screens.first!
let visible = screen.visibleFrame
let full = screen.frame

// Usable top edge = menu bar height (the OS clamps window tops below it);
// no probing move needed — the menu bar is a full-width window we can read.
func menuBarHeight(on screen: NSScreen) -> CGFloat {
    let frame = screen.frame
    let info = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as? [[String: Any]] ?? []
    for window in info {
        guard let bounds = window[kCGWindowBounds as String] as? [String: CGFloat],
              let xPos = bounds["X"], let yPos = bounds["Y"],
              let width = bounds["Width"], let height = bounds["Height"] else { continue }
        if abs(xPos - frame.minX) <= 2 && abs(yPos) <= 1
            && abs(width - frame.width) <= 2
            && height >= 20 && height <= 60 {
            return height
        }
    }
    return 0
}
let topY = menuBarHeight(on: screen)

// Bottom edge: full screen bottom when the Dock is auto-hidden, otherwise the
// visible frame's bottom (which stops above the Dock).
let dockAutoHidden = UserDefaults(suiteName: "com.apple.dock")?.bool(forKey: "autohide") ?? false
let bottomY = dockAutoHidden ? full.maxY : visible.maxY

let usable = CGRect(x: visible.minX, y: topY, width: visible.width, height: bottomY - topY)

let target: CGRect
switch mode {
case "max":
    target = usable
case "reasonable":
    let width = usable.width * reasonableWidthFraction
    let height = usable.height * reasonableHeightFraction
    target = CGRect(x: usable.midX - width / 2, y: usable.midY - height / 2, width: width, height: height)
case "center":
    target = CGRect(x: usable.midX - current.width / 2,
                    y: usable.midY - current.height / 2,
                    width: current.width, height: current.height)
case "tl":
    target = CGRect(x: usable.minX, y: usable.minY,
                    width: usable.width / 2, height: usable.height / 2)
case "tr":
    target = CGRect(x: usable.midX, y: usable.minY,
                    width: usable.width / 2, height: usable.height / 2)
case "bl":
    target = CGRect(x: usable.minX, y: usable.midY,
                    width: usable.width / 2, height: usable.height / 2)
case "br":
    target = CGRect(x: usable.midX, y: usable.midY,
                    width: usable.width / 2, height: usable.height / 2)
default:
    fail("未知模式: \(mode)")
}

if animate {
    withEnhancedUIDisabled(axApp) {
        animateFrame(window, from: current, to: target, windowID: windowID)
    }
} else {
    withEnhancedUIDisabled(axApp) {
        settleFrame(window, target, windowID: windowID)
    }
}
