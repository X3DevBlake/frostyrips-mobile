# FrostyRips Mobile — Android APK & iOS App

Official native mobile apps for **FrostyRips** (`https://frostrips.web.app` & `https://frostyrips-stadium.web.app`).

## Contents

- `android/` — Complete native Android project (`com.frostyrips.app`, `minSdk 24`, `targetSdk 34`) + signed release APK (`FrostyRips-v1.0.0.apk`).
  - Hardware-accelerated WebGL2 WebView with custom dark splash overlay, offline recovery UI, deep links (`frostyrips://`, `https://frostrips.web.app`, `https://frostyrips-stadium.web.app`), back-button navigation, and `window.FrostyNative` bridge (haptics, native Share Sheet, clipboard, toast, Megastadium switch).
- `ios/` — Complete native SwiftUI + `WKWebView` iOS project (`com.frostyrips.app`, iOS 16+) + Apple direct-install Home Screen configuration profile (`FrostyRips-iOS.mobileconfig`).
  - Matching `window.FrostyNative` bridge via `WKScriptMessageHandler`, Core Haptics (`UIImpactFeedbackGenerator`), `UIActivityViewController` share sheet, Universal Links, custom URL scheme (`frostyrips://`), and full `Assets.xcassets/AppIcon.appiconset` up to 1024×1024 PNG.
- `.github/workflows/build-ios-ipa.yml` — Automated macOS GitHub Actions workflow to build an unsigned/ad-hoc `.ipa` from `ios/` via XcodeGen + `xcodebuild`.

## Installing on Android

1. Download `FrostyRips.apk` from `https://frostrips.web.app/downloads/FrostyRips.apk` (or `android/FrostyRips-v1.0.0.apk`).
2. Tap the downloaded APK and allow **Install unknown apps** if prompted.
3. Launch **FrostyRips** from your Home Screen.

## Installing on iOS (iPhone & iPad)

### Option A — Instant Direct Install (No Mac / No App Store Required)
1. Open Safari on your iPhone and tap **Install iOS App Profile** (`https://frostrips.web.app/downloads/FrostyRips-iOS.mobileconfig`).
2. Tap **Allow** when prompted to download the FrostyRips profile.
3. Open **Settings → Profile Downloaded → Install** to add the standalone full-screen FrostyRips app directly to your Home Screen.

### Option B — Build Signed Native `.ipa` in Xcode or GitHub Actions
1. Open `ios/` on macOS with Xcode 15+ and run `xcodegen generate` (or push to a GitHub repo and trigger `.github/workflows/build-ios-ipa.yml`).
2. Select your Apple Developer Team in Signing & Capabilities and Archive / deploy to device, TestFlight, or App Store Connect.
