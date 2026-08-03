// Render the Window Control icon set: SF Symbols tinted white on a dark
// rounded badge, 256x256 PNG. Build: swiftc -O make_icons.swift -o /tmp/mkicons
// Usage: /tmp/mkicons <output-dir>

import AppKit
import Foundation

let icons: [(name: String, symbol: String)] = [
    ("icon", "square.grid.2x2"),
    ("max", "arrow.up.left.and.arrow.down.right"),
    ("reasonable", "rectangle.inset.filled"),
    ("center", "arrow.up.and.down.and.arrow.left.and.right"),
    ("tl", "rectangle.inset.topleft.filled"),
    ("tr", "rectangle.inset.topright.filled"),
    ("bl", "rectangle.inset.bottomleft.filled"),
    ("br", "rectangle.inset.bottomright.filled"),
]

func render(_ name: String, _ symbol: String, to dir: String) {
    let px = 256
    guard let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px,
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
        colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)
    else { return }
    rep.size = NSSize(width: px, height: px)

    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let ctx = NSGraphicsContext.current!.cgContext

    // Badge
    let badge = NSBezierPath(
        roundedRect: NSRect(x: 8, y: 8, width: 240, height: 240),
        xRadius: 56, yRadius: 56)
    NSColor(calibratedRed: 0.22, green: 0.24, blue: 0.30, alpha: 1).setFill()
    badge.fill()

    // Symbol, tinted white via alpha-mask clip
    let target = NSRect(x: 34, y: 34, width: 188, height: 188)
    let cfg = NSImage.SymbolConfiguration(pointSize: 110, weight: .medium)
    if let img = NSImage(systemSymbolName: symbol, accessibilityDescription: nil)?
        .withSymbolConfiguration(cfg) {
        var proposed = NSRect(origin: .zero, size: img.size)
        if let cg = img.cgImage(forProposedRect: &proposed, context: nil, hints: nil) {
            ctx.saveGState()
            ctx.clip(to: target, mask: cg)
            ctx.setFillColor(NSColor.white.cgColor)
            ctx.fill(target)
            ctx.restoreGState()
        }
    }
    NSGraphicsContext.restoreGraphicsState()

    if let png = rep.representation(using: .png, properties: [:]) {
        try? png.write(to: URL(fileURLWithPath: "\(dir)/\(name).png"))
    }
}

let outDir = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "."
for icon in icons {
    render(icon.name, icon.symbol, to: outDir)
}
print("rendered \(icons.count) icons to \(outDir)")
