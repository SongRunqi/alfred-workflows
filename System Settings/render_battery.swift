// Render the macOS System Settings-style battery icon (SF Symbol, green fill)
// to a 256x256 PNG, matching the other icons in the Settings workflow.
// Usage: swiftc render_battery.swift -o /tmp/render_battery && /tmp/render_battery out.png
import AppKit

let size: CGFloat = 256
let symbolSize: CGFloat = 200

// Try modern name first, fall back to legacy
let names = ["battery.100percent", "battery.100"]
var symbol: NSImage? = nil
for name in names {
    if let img = NSImage(systemSymbolName: name, accessibilityDescription: nil) {
        symbol = img
        print("using symbol: \(name)")
        break
    }
}
guard let base = symbol else {
    print("ERROR: no battery symbol found")
    exit(1)
}

// Palette: green fill + dark outline (System Settings battery style)
let config = NSImage.SymbolConfiguration(paletteColors: [.systemGreen, .black])
let configured = base.withSymbolConfiguration(config)!

// Render at fixed pixel size into a bitmap (not retina-scaled)
let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: Int(size),
    pixelsHigh: Int(size),
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: 0,
    bitsPerPixel: 0
)!

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
NSGraphicsContext.current?.imageInterpolation = .high
let drawRect = NSRect(
    x: (size - symbolSize) / 2,
    y: (size - symbolSize) / 2,
    width: symbolSize,
    height: symbolSize
)
configured.draw(in: drawRect)
NSGraphicsContext.restoreGraphicsState()

let png = rep.representation(using: .png, properties: [:])!

let out = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "battery.png"
do {
    try png.write(to: URL(fileURLWithPath: out))
} catch {
    print("ERROR: write failed: \(error)")
    exit(1)
}
print("wrote \(out) (\(size)x\(size))")
