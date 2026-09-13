"""Check packaging against the actual ESP partition table; never touches a miner."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(build, output, version):
    app = (build / "esp-miner.bin").read_bytes()
    www = (build / "www.bin").read_bytes()
    boot = (build / "bootloader/bootloader.bin").read_bytes()
    table = (build / "partition_table/partition-table.bin").read_bytes()
    ota = (build / "ota_data_initial.bin").read_bytes()
    require(len(app) <= 0x500000, "Application exceeds OTA slot")
    require(len(www) == 0x300000, "WWW must be exactly 3 MiB")
    require(len(boot) <= 0x8000, "Bootloader overlaps partition table")
    require(app[0] == 0xE9 and app[3] >> 4 == 5, "Expected ESP image with 32 MiB flash")
    require(struct.unpack_from("<I", app, 32)[0] == 0xABCD5432, "Missing app descriptor")
    app_version = app[48:80].split(b"\0", 1)[0].decode()
    require(app_version.startswith(version + "-bigscreen-"), "Incorrect application version")

    # Validate the ESP image's appended SHA-256 (not a publisher signature).
    require(app[23] == 1, "Application lacks appended SHA-256")
    end = 24
    for _ in range(app[1]):
        length = struct.unpack_from("<I", app, end + 4)[0]
        end += 8 + length
        require(end < len(app), "Truncated ESP segment")
    end = (end // 16 + 1) * 16
    require(hashlib.sha256(app[:end]).digest() == app[end:end + 32], "ESP image digest mismatch")

    expected = {
        "nvs": (1, 2, 0x9000, 0x6000),
        "phy_init": (1, 1, 0xF000, 0x1000),
        "factory": (0, 0, 0x10000, 0x500000),
        "ota_0": (0, 0x10, 0x510000, 0x500000),
        "ota_1": (0, 0x11, 0xA10000, 0x500000),
        "otadata": (1, 0, 0xF10000, 0x2000),
        "coredump": (1, 3, 0xF12000, 0x10000),
        "www": (1, 0x82, 0x1000000, 0x300000),
    }
    actual = {}
    for offset in range(0, len(table), 32):
        magic, kind, sub, start, size, label, flags = struct.unpack_from("<HBBII16sI", table, offset)
        if magic != 0x50AA:
            break
        actual[label.split(b"\0", 1)[0].decode()] = (kind, sub, start, size)
        require(start + size <= 0x2000000, "Partition exceeds physical flash")
        require(flags == 0, "Unexpected encrypted/read-only partition")
    require(actual == expected, f"Unexpected partition table: {actual}")

    full = (output / f"esp-miner-factory-NerdQAxe++-BigScreen-FullFlash-{version}.bin").read_bytes()
    stream = (output / f"esp-miner-factory-NerdQAxe++-{version}.bin").read_bytes()
    require(len(full) == 0x1300000, "Incorrect full-flash length")
    require(len(stream) == 0x810000, "Incorrect OTA stream length")
    for name, data, address in [("bootloader", boot, 0), ("table", table, 0x8000),
                                ("application", app, 0x10000)]:
        require(full[address:address + len(data)] == data, f"Full-flash {name} mismatch")
        require(stream[address:address + len(data)] == data, f"OTA stream {name} mismatch")
    require(full[0xF10000:0xF10000 + len(ota)] == ota, "Initial OTA data mismatch")
    require(full[0x1000000:] == www, "Full-flash WWW mismatch")
    require(stream[0x510000:] == www, "OTA stream WWW mismatch")
    require(stream[0x10000 + len(app):0x510000] ==
            b"\xff" * (0x500000 - len(app)), "OTA padding is not erased flash")
    return {"upstream_version": version, "application_version": app_version,
            "application_bytes": len(app), "www_bytes": len(www),
            "display_profile": "bigscreen-480x320", "hardware_tested": False,
            "ota_stream_bytes": len(stream), "full_flash_bytes": len(full)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, default=Path("build"))
    parser.add_argument("--output", type=Path, default=Path("."))
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.build, args.output, args.version), indent=2))
