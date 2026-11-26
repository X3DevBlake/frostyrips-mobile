#!/usr/bin/env bash
set -euo pipefail

ROOT="/data/data/com.termux/files/home/frostyrips-mobile"
ANDROID_DIR="$ROOT/android"
APP_DIR="$ANDROID_DIR/app/src/main"
BUILD_DIR="$ANDROID_DIR/build"
TOOLS_DIR="$ROOT/tools"
ANDROID_JAR="$TOOLS_DIR/android-34.jar"
KEYSTORE="$ANDROID_DIR/frostyrips-release.jks"
KEY_ALIAS="frostyrips"
STORE_PASS="FrostyRips2026!Release"
OUT_APK="$ANDROID_DIR/FrostyRips-v1.0.0.apk"
PUB_APK="/data/data/com.termux/files/home/frostrips/public/downloads/FrostyRips.apk"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/gen" "$BUILD_DIR/classes" "$BUILD_DIR/dex" "$(dirname "$PUB_APK")"

echo "[1/6] Compiling Android resources with aapt2..."
aapt2 compile --dir "$APP_DIR/res" -o "$BUILD_DIR/res.zip"

echo "[2/6] Linking APK resources & manifest..."
aapt2 link \
  -o "$BUILD_DIR/base.apk" \
  -I "$ANDROID_JAR" \
  --manifest "$APP_DIR/AndroidManifest.xml" \
  --java "$BUILD_DIR/gen" \
  -R "$BUILD_DIR/res.zip" \
  --auto-add-overlay \
  --version-code 1 \
  --version-name "1.0.0"

echo "[3/6] Compiling Java sources against Android API 34..."
javac \
  -source 11 -target 11 \
  -classpath "$ANDROID_JAR" \
  -d "$BUILD_DIR/classes" \
  "$BUILD_DIR/gen/com/frostyrips/app/R.java" \
  "$APP_DIR/java/com/frostyrips/app/MainActivity.java"

echo "[4/6] Translating bytecode to Dalvik DEX with d8 (minSdk 24)..."
d8 \
  --lib "$ANDROID_JAR" \
  --min-api 24 \
  --release \
  --output "$BUILD_DIR/dex" \
  "$BUILD_DIR"/classes/com/frostyrips/app/*.class

echo "[5/6] Packing classes.dex & 4-byte aligning APK..."
cp "$BUILD_DIR/base.apk" "$BUILD_DIR/unsigned.apk"
(cd "$BUILD_DIR/dex" && zip -q "$BUILD_DIR/unsigned.apk" classes.dex)
python3 "$TOOLS_DIR/align_apk.py" "$BUILD_DIR/unsigned.apk" "$BUILD_DIR/aligned.apk"

if [ ! -f "$KEYSTORE" ]; then
  echo "[5b] Generating RSA-2048 release keystore..."
  keytool -genkeypair -v \
    -keystore "$KEYSTORE" \
    -alias "$KEY_ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -storepass "$STORE_PASS" \
    -keypass "$STORE_PASS" \
    -dname "CN=FrostyRips LLC, OU=Mobile Engineering, O=FrostyRips, L=Las Vegas, ST=NV, C=US"
fi

echo "[6/6] Signing APK (v1 + v2 + v3) & verifying with apksigner..."
apksigner sign \
  --ks "$KEYSTORE" \
  --ks-key-alias "$KEY_ALIAS" \
  --ks-pass "pass:$STORE_PASS" \
  --key-pass "pass:$STORE_PASS" \
  --v1-signing-enabled true \
  --v2-signing-enabled true \
  --v3-signing-enabled true \
  --out "$OUT_APK" \
  "$BUILD_DIR/aligned.apk"

apksigner verify --verbose --print-certs "$OUT_APK"
cp "$OUT_APK" "$PUB_APK"

echo ""
echo "✓ Built, signed & verified Android APK:"
ls -lh "$OUT_APK" "$PUB_APK"
sha256sum "$PUB_APK"
