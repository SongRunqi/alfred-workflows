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

// NOTE: claude.png is NOT rendered here — it is composited from the official
// Anthropic starburst (simple-icons claudecode.svg, brand #D97757) on the
// dark badge via the PIL script below, so the brand mark stays exact:
//
//   curl -sL -o /tmp/cc.svg https://raw.githubusercontent.com/simple-icons/simple-icons/master/icons/claudecode.svg
//   qlmanage -t -s 512 -o /tmp /tmp/cc.svg
//   python3 - <<'PY'
//   from PIL import Image, ImageDraw
//   src = Image.open('/tmp/cc.svg.png').convert('RGBA')
//   lum = src.convert('L')
//   burst = Image.new('RGBA', src.size, (217, 119, 87, 255))
//   burst.putalpha(lum.point(lambda v: 255 - v))
//   S = 512
//   badge = Image.new('RGBA', (S, S), (0, 0, 0, 0))
//   ImageDraw.Draw(badge).rounded_rectangle([8, 8, S-8, S-8], radius=112, fill=(23, 26, 35, 255))
//   t = int(S * 0.62)
//   badge.alpha_composite(burst.resize((t, t), Image.LANCZOS), ((S-t)//2, (S-t)//2))
//   badge.resize((256, 256), Image.LANCZOS).save('icons/claude.png')
//   PY

let icons: [IconSpec] = [
    IconSpec(name: "pi", symbol: "pi", color: NSColor(calibratedRed: 0.20, green: 0.83, blue: 0.60, alpha: 1)),      // π, green
    IconSpec(name: "agent", symbol: "cpu", color: NSColor(calibratedRed: 0.61, green: 0.64, blue: 0.69, alpha: 1)),  // grey, custom-agent fallback
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

    // Symbol, tinted via alpha-mask clip; falls back to drawing the π glyph
    // for the "pi" symbol when the system symbol is unavailable.
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
    } else if spec.symbol == "pi" {
        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = .center
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 150, weight: .medium),
            .foregroundColor: spec.color,
            .paragraphStyle: paragraph,
        ]
        let glyph = NSAttributedString(string: "π", attributes: attrs)
        let bounds = glyph.boundingRect(with: target.size, options: [.usesLineFragmentOrigin])
        glyph.draw(at: NSPoint(x: target.minX + (target.width - bounds.width) / 2,
                               y: target.minY + (target.height - bounds.height) / 2))
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
