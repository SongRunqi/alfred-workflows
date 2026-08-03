// Render the PiHop icon set: SF Symbols tinted per-brand on dark rounded
// badges, 256x256 PNG. Build: swiftc -O make_icons.swift -o /tmp/mkpihop
// Usage: /tmp/mkpihop <output-dir>

import AppKit
import Foundation

struct IconSpec {
    let name: String
    let symbol: String
    let color: NSColor
}

let icons: [IconSpec] = [
    IconSpec(name: "pi", symbol: "terminal", color: NSColor(calibratedRed: 0.20, green: 0.83, blue: 0.60, alpha: 1)),      // green
    IconSpec(name: "claude", symbol: "sparkles", color: NSColor(calibratedRed: 0.65, green: 0.55, blue: 0.98, alpha: 1)),  // purple
    IconSpec(name: "new", symbol: "plus.circle", color: NSColor(calibratedRed: 0.98, green: 0.75, blue: 0.15, alpha: 1)), // amber
    IconSpec(name: "resume", symbol: "clock.arrow.circlepath", color: NSColor(calibratedRed: 0.38, green: 0.65, blue: 0.98, alpha: 1)), // blue
]

func render(_ spec: IconSpec, to dir: String) {
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

    // Terminal-dark badge
    let badge = NSBezierPath(
        roundedRect: NSRect(x: 8, y: 8, width: 240, height: 240),
        xRadius: 56, yRadius: 56)
    NSColor(calibratedRed: 0.09, green: 0.10, blue: 0.13, alpha: 1).setFill()
    badge.fill()

    // Symbol, tinted via alpha-mask clip
    let target = NSRect(x: 40, y: 40, width: 176, height: 176)
    let cfg = NSImage.SymbolConfiguration(pointSize: 104, weight: .medium)
    if let img = NSImage(systemSymbolName: spec.symbol, accessibilityDescription: nil)?
        .withSymbolConfiguration(cfg) {
        var proposed = NSRect(origin: .zero, size: img.size)
        if let cg = img.cgImage(forProposedRect: &proposed, context: nil, hints: nil) {
            ctx.saveGState()
            ctx.clip(to: target, mask: cg)
            ctx.setFillColor(spec.color.cgColor)
            ctx.fill(target)
            ctx.restoreGState()
        }
    }
    NSGraphicsContext.restoreGraphicsState()

    if let png = rep.representation(using: .png, properties: [:]) {
        try? png.write(to: URL(fileURLWithPath: "\(dir)/\(spec.name).png"))
    }
}

let outDir = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "."
for spec in icons {
    render(spec, to: outDir)
}
print("rendered \(icons.count) icons to \(outDir)")
