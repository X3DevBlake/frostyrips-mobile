#!/usr/bin/env python3
"""
Deterministic Android APK 4-byte / 4096-byte Zip Aligner (zipalign equivalent).
Guarantees uncompressed entries (especially resources.arsc) start on a 4-byte
boundary (or 4096-byte boundary for .so native libraries), as required by
Android 11+ (targetSdk 30–34) before apksigner signs the APK.
"""
import os
import struct
import sys
import zipfile


def align_apk(src_path: str, dst_path: str) -> None:
    if os.path.exists(dst_path):
        os.remove(dst_path)

    with zipfile.ZipFile(src_path, "r") as zin:
        infos = zin.infolist()
        with zipfile.ZipFile(dst_path, "w") as zout:
            for info in infos:
                # Skip existing signature entries if re-aligning
                if info.filename.startswith("META-INF/") and (
                    info.filename.endswith(".SF")
                    or info.filename.endswith(".RSA")
                    or info.filename.endswith(".DSA")
                    or info.filename.endswith(".EC")
                    or info.filename == "META-INF/MANIFEST.MF"
                ):
                    continue

                data = zin.read(info.filename)
                # Android 11+ requires resources.arsc to be stored uncompressed & 4-byte aligned
                force_store = (
                    info.filename == "resources.arsc"
                    or info.filename.endswith(".so")
                    or info.compress_type == zipfile.ZIP_STORED
                )
                compress_type = zipfile.ZIP_STORED if force_store else zipfile.ZIP_DEFLATED
                alignment = 4096 if info.filename.endswith(".so") else 4

                new_info = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
                new_info.compress_type = compress_type
                new_info.create_system = info.create_system
                new_info.external_attr = info.external_attr
                new_info.flag_bits = info.flag_bits & ~0x08  # Clear data-descriptor flag

                if compress_type == zipfile.ZIP_STORED:
                    # Local file header = 30 bytes + len(filename) + len(extra)
                    fn_bytes = new_info.filename.encode("utf-8")
                    current_pos = zout.fp.tell()
                    header_end = current_pos + 30 + len(fn_bytes)
                    pad = (alignment - (header_end % alignment)) % alignment
                    if pad > 0:
                        new_info.extra = b"\x00" * pad
                    else:
                        new_info.extra = b""
                else:
                    new_info.extra = b""

                zout.writestr(new_info, data, compress_type=compress_type)

    # Verify alignment of every stored entry
    with open(dst_path, "rb") as f:
        with zipfile.ZipFile(dst_path, "r") as zcheck:
            for info in zcheck.infolist():
                if info.compress_type == zipfile.ZIP_STORED:
                    f.seek(info.header_offset)
                    sig, _, _, _, _, _, _, _, _, fn_len, extra_len = struct.unpack("<IHHHHHIIIHH", f.read(30))
                    assert sig == 0x04034B50, f"Bad local header for {info.filename}"
                    data_offset = info.header_offset + 30 + fn_len + extra_len
                    req = 4096 if info.filename.endswith(".so") else 4
                    assert data_offset % req == 0, f"{info.filename} misaligned: {data_offset} % {req} != 0"
    print(f"Aligned APK written and verified: {dst_path} ({os.path.getsize(dst_path):,} bytes)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: align_apk.py <input.apk> <output-aligned.apk>", file=sys.stderr)
        sys.exit(1)
    align_apk(sys.argv[1], sys.argv[2])
