"""Fail CI if the adaptation changes code outside its reviewed scope."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
base = (root / "UPSTREAM_COMMIT").read_text().strip()
subprocess.run(["git", "cat-file", "-e", base + "^{commit}"], cwd=root, check=True)
allowed = {
    ".github/workflows/bigscreen-build.yml",
    ".github/workflows/upstream-stable.yml",
    "CMakeLists.txt", "UPSTREAM_VERSION", "UPSTREAM_COMMIT",
    "main/CMakeLists.txt",
    "main/displays/displayDriver.cpp", "main/displays/displayDriver.h",
    "main/displays/ui.cpp", "main/displays/ui.h",
    "main/http_server/handler_ota_factory.cpp",
    "main/http_server/v2/handler_v2_settings.cpp",
    "main/http_server/axe-os/src/app/models/ISettingsV2.ts",
    "main/http_server/axe-os/src/app/pages/settings/settings.component.ts",
    "main/http_server/axe-os/src/app/services/github-update.service.ts",
    "partitions_yysluping_32mb.csv", "sdkconfig.yysluping.defaults",
    "docs/BIGSCREEN.md", "test/check_bigscreen_scope.py",
    "test/verify_bigscreen_artifacts.py",
    "test/test_bigscreen_artifacts.py",
}
allowed.update("components/yysluping_boya_flash/" + name for name in
               ["CMakeLists.txt", "chip_drivers.c", "linker.lf", "spi_flash_chip_boya_32mb.c"])
changed = subprocess.check_output(
    ["git", "diff", "--name-only", base, "--"], cwd=root, text=True).splitlines()
unexpected = set(changed) - allowed
for name in list(unexpected):
    # Ignore a trailing blank-line-only difference, never source changes.
    baseline = subprocess.check_output(["git", "show", f"{base}:{name}"], cwd=root)
    local = root / name
    if local.is_file() and local.read_bytes().rstrip(b"\n") == baseline.rstrip(b"\n"):
        unexpected.remove(name)
if unexpected:
    raise SystemExit("Changes outside reviewed display/flash/OTA scope: " + ", ".join(sorted(unexpected)))
print("Scope OK: mining, boards, configuration defaults, dependencies and original artwork unchanged.")
print("This scope check is not a complete security audit.")
