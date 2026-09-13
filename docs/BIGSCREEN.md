# Native 480×320 profile

This is a community adaptation, not an official shufps binary. The official
upstream version is recorded in UPSTREAM_VERSION. Mining, board initialization,
pool configuration and thermal protection remain from that upstream base.

Display/UI and BOYA flash support are ported selectively from XTVDDICT commit
f400e23326266ada3b78d617d85de5bc9892b549 (GPL-3.0), not from its older LTS tree.
The native main screens use LVGL widgets and NerdQAxe branding. Splash/shutdown
images still use the original artwork enlarged by 1.5; this is not a promise of
pixel-perfect original artwork at 480×320.

Build with BOARD=NERDQAXEPLUS2, DISPLAY_PROFILE=YYSLUPING_480X320 and
SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.yysluping.defaults".
The profile is for the ESP32-S3 / 8 MiB PSRAM / BOYA 0x684019 / 32 MiB device.
The flash driver enables access to WWW at 0x1000000. A successful build does
not establish that a particular miner's screen, color order or flash works.

## Files are NOT interchangeable

- esp-miner-NerdQAxe++-BigScreen.bin: application-only OTA file; requires the
  existing 5 MiB-slot partition layout and a compatible web UI.
- www.bin: web UI for the same build.
- *BigScreen-FullFlash-*.bin: serial recovery image at offset 0. Writing the
  full image overwrites configuration; do not use this for routine OTA.
- esp-miner-factory-NerdQAxe++-v*.bin: compact stream for this fork's one-click
  updater only. It is NOT a serial-flash image: its WWW offset is intentionally
  different from the physical flash partition table.

## Updates and release gate

Every six hours GitHub Actions checks for a new official stable release. It
prepares an upstream-candidate branch and builds it. Conflicts stop the run.
Nothing automatically flashes a miner or promotes an untested build.

One-click OTA keeps the official version names and changelogs but offers only
non-prerelease bigscreen-v<version>-r<N> releases in harmstorf/ESP-Miner-NerdQAxePlus with
the expected 8,454,144-byte stream. API errors/missing builds never fall back
to unmodified stock firmware. Standard display builds keep the official route.
Manual file upload can bypass this selection: never upload an arbitrary stock
application to a big-screen miner.

Before promoting a candidate: test cold boot, full-screen orientation/colors,
Wi-Fi and SPIFFS, all UI screens, actual pool/user configuration, fan/temperature
telemetry, and OTA through both application slots. Keep a verified serial backup.
Record the tested commit and artifact SHA-256 in the release notes, then promote
the tested candidate and publish its exact artifacts under bigscreen-v<version>-r<N>
(for example bigscreen-v1.1.0-r1). A later fix gets a new revision, never an
overwrite of existing assets. The UI selects the highest promoted revision.
Do not rebuild or silently replace artifacts after hardware approval.

The big-screen updater delays boot-slot selection until WWW write/read-back
succeeds. WWW is still a SINGLE partition: loss of power while writing it can
require recovery. This is not a fully atomic A/B firmware+web update.

## Security scope

The port introduces no pool, payout address or mining task changes. This is a
diff-based scope check, not proof that upstream or all dependencies are free of
backdoors. Official source contains default/donation addresses; verify your
own pool and payout user after a configuration reset and before mining.
Artifact SHA-256 checks detect corruption, not a malicious publisher.
GitHub account security, build dependencies and release approval remain trust
boundaries. No firmware should be described as hardware-safe before testing.
