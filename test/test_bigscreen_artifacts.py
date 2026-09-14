"""Synthetic valid and deliberately damaged packages exercise the verifier."""
import hashlib
import gzip
from pathlib import Path
import struct
import tempfile
import unittest

from verify_bigscreen_artifacts import verify, verify_web_version


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.build = self.root / "build"
        (self.build / "bootloader").mkdir(parents=True)
        (self.build / "partition_table").mkdir()
        self.version = "v1.1.0"
        header = bytearray(24)
        header[0], header[1], header[3], header[23] = 0xE9, 1, 0x50, 1
        descriptor = bytearray(256)
        struct.pack_into("<I", descriptor, 0, 0xABCD5432)
        name = b"v1.1.0-bigscreen-12345678"
        descriptor[16:16 + len(name)] = name
        app = header + struct.pack("<II", 0x3C000020, len(descriptor)) + descriptor
        app.extend(bytes(16 - len(app) % 16))
        app.extend(hashlib.sha256(app).digest())
        self.app = bytes(app)
        self.www = b"W" * 0x300000
        self.boot = b"B" * 0x7000
        self.ota = b"\xff" * 0x2000
        rows = [
            ("nvs", 1, 2, 0x9000, 0x6000), ("phy_init", 1, 1, 0xF000, 0x1000),
            ("factory", 0, 0, 0x10000, 0x500000), ("ota_0", 0, 16, 0x510000, 0x500000),
            ("ota_1", 0, 17, 0xA10000, 0x500000), ("otadata", 1, 0, 0xF10000, 0x2000),
            ("coredump", 1, 3, 0xF12000, 0x10000), ("www", 1, 0x82, 0x1000000, 0x300000)]
        self.table = b"".join(struct.pack("<HBBII16sI", 0x50AA, kind, sub, off, size,
                                          label.encode(), 0) for label, kind, sub, off, size in rows)
        self.table += b"\xff" * (0x1000 - len(self.table))
        for name, data in [("esp-miner.bin", self.app), ("www.bin", self.www),
                           ("bootloader/bootloader.bin", self.boot),
                           ("partition_table/partition-table.bin", self.table),
                           ("ota_data_initial.bin", self.ota)]:
            (self.build / name).write_bytes(data)
        self.full_name = self.root / f"esp-miner-factory-NerdQAxe++-BigScreen-FullFlash-{self.version}.bin"
        self.stream_name = self.root / f"esp-miner-factory-NerdQAxe++-{self.version}.bin"
        full = bytearray(b"\xff" * 0x1300000)
        stream = bytearray(b"\xff" * 0x810000)
        for data, offset in [(self.boot, 0), (self.table, 0x8000), (self.app, 0x10000)]:
            full[offset:offset + len(data)] = data
            stream[offset:offset + len(data)] = data
        full[0xF10000:0xF12000] = self.ota
        full[0x1000000:] = self.www
        stream[0x510000:] = self.www
        self.full_name.write_bytes(full)
        self.stream_name.write_bytes(stream)

    def check(self):
        return verify(self.build, self.root, self.version)

    def test_valid_package(self):
        self.assertEqual(self.check()["ota_stream_bytes"], 8454144)
        self.assertFalse(self.check()["hardware_tested"])

    def test_corrupt_app_digest(self):
        damaged = bytearray(self.app)
        damaged[-1] ^= 1
        (self.build / "esp-miner.bin").write_bytes(damaged)
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.check()

    def test_wrong_www_partition(self):
        damaged = bytearray(self.table)
        struct.pack_into("<I", damaged, 7 * 32 + 4, 0x410000)
        (self.build / "partition_table/partition-table.bin").write_bytes(damaged)
        with self.assertRaisesRegex(ValueError, "Unexpected partition"):
            self.check()

    def test_wrong_stream_www(self):
        with self.stream_name.open("r+b") as stream:
            stream.seek(0x510000)
            stream.write(b"X")
        with self.assertRaisesRegex(ValueError, "OTA stream WWW mismatch"):
            self.check()

    def test_wrong_stream_padding(self):
        with self.stream_name.open("r+b") as stream:
            stream.seek(0x10000 + len(self.app))
            stream.write(b"X")
        with self.assertRaisesRegex(ValueError, "padding"):
            self.check()

    def test_wrong_base_version(self):
        with self.assertRaisesRegex(ValueError, "application version"):
            verify(self.build, self.root, "v1.2.0")

    def test_matching_web_version(self):
        (self.root / "main.js.gz").write_bytes(gzip.compress(b'const v="v1.1.0-bigscreen-12345678";'))
        self.assertEqual(verify_web_version("v1.1.0-bigscreen-12345678", self.root),
                         "v1.1.0-bigscreen-12345678")

    def test_reject_original_web_version_bug(self):
        (self.root / "main.js.gz").write_bytes(gzip.compress(b'const v="v1.1.0-bigscreen";'))
        with self.assertRaisesRegex(ValueError, "Firmware/WebUI version mismatch"):
            verify_web_version("v1.1.0-bigscreen-12345678", self.root)

    def test_reject_other_commit(self):
        (self.root / "main.js.gz").write_bytes(gzip.compress(b'const v="v1.1.0-bigscreen-aaaaaaaa";'))
        with self.assertRaisesRegex(ValueError, "Firmware/WebUI version mismatch"):
            verify_web_version("v1.1.0-bigscreen-12345678", self.root)


if __name__ == "__main__":
    unittest.main()
