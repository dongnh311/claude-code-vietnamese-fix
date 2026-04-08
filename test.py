#!/usr/bin/env python3
"""
Claude Code Vietnamese IME Fix - Test Runner

Auto-downloads latest npm versions + binary builds, patches, verifies.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SOURCES_DIR = SCRIPT_DIR / "tests" / "sources"
PATCHER = SCRIPT_DIR / "patcher.py"

GREEN = "\033[0;32m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
NC = "\033[0m"

# GCS base URL for Claude Code binary releases
GCS_BASE = (
    "https://storage.googleapis.com/"
    "claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/"
    "claude-code-releases"
)


def get_current_platform():
    """Get platform string for binary download."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == 'darwin':
        arch = 'arm64' if machine == 'arm64' else 'x64'
        return f'darwin-{arch}'
    elif system == 'linux':
        arch = 'arm64' if machine in ('aarch64', 'arm64') else 'x64'
        return f'linux-{arch}'
    elif system == 'windows':
        arch = 'arm64' if machine in ('arm64', 'aarch64') else 'x64'
        return f'win32-{arch}'
    return None


def get_latest_versions(count=3):
    """Get latest N versions from npm registry."""
    result = subprocess.run(
        ["npm", "view", "@anthropic-ai/claude-code", "versions", "--json"],
        capture_output=True, text=True, timeout=30
    )
    versions = json.loads(result.stdout)

    def semver_key(v):
        parts = v.replace("-", ".").split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in parts[:3])

    return sorted(versions, key=semver_key, reverse=True)[:count]


def download_npm(version):
    """Download npm package and extract cli.js."""
    version_dir = SOURCES_DIR / f"v{version}"

    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(
            ["npm", "pack", f"@anthropic-ai/claude-code@{version}"],
            cwd=temp_dir, capture_output=True, timeout=120
        )
        tarball = list(Path(temp_dir).glob("*.tgz"))[0]

        version_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tarball, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.startswith("package/"):
                    member.name = member.name[8:]
                    if member.name:
                        tar.extract(member, version_dir, filter="data")

    return version_dir / "cli.js"


def download_binary(version, plat):
    """Download Claude Code binary from GCS."""
    binary_dir = SOURCES_DIR / f"v{version}-{plat}"
    binary_dir.mkdir(parents=True, exist_ok=True)

    ext = '.exe' if plat.startswith('win32') else ''
    binary_path = binary_dir / f"claude{ext}"

    url = f"{GCS_BASE}/{version}/{plat}/claude{ext}"
    try:
        urllib.request.urlretrieve(url, str(binary_path))
        if not plat.startswith('win32'):
            os.chmod(str(binary_path), 0o755)
        return binary_path
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Download failed ({e.code}): {url}")


def run_patcher(args):
    """Run patcher with args, return (success, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, str(PATCHER)] + args,
        capture_output=True, text=True, timeout=30
    )
    return result.returncode == 0, result.stdout, result.stderr


def verify_runs(file_path):
    """Verify patched cli.js runs with --version."""
    result = subprocess.run(
        ["node", str(file_path), "--version"],
        capture_output=True, text=True, timeout=10
    )
    return result.returncode == 0, result.stdout.strip()


def verify_fix_logic(file_path, binary=False):
    """Verify patched code contains correct fix logic (backspace + insert)."""
    encoding = 'latin1' if binary else 'utf-8'
    content = Path(file_path).read_text(encoding=encoding)

    # Must have patch marker
    if "/* Vietnamese IME fix */" not in content:
        return False, "missing patch marker"

    # Extract the fix block (from marker to next return;})
    marker_idx = content.index("/* Vietnamese IME fix */")
    fix_end = content.find("return;}", marker_idx)
    if fix_end == -1:
        return False, "cannot find fix block end"
    fix_block = content[marker_idx:fix_end + 8]

    # Must iterate string and branch
    if "for(const _c of " not in fix_block:
        return False, "missing character iteration in fix"

    if '==="\\x7f"' not in fix_block:
        return False, "missing backspace character check"

    # Must have backspace loop
    if ".backspace()" not in fix_block:
        return False, "missing .backspace() in fix"

    # Must have insert loop
    if ".insert(" not in fix_block:
        return False, "missing .insert() in fix"

    # Original bug pattern should be gone (only appears in our fix block)
    del_char = chr(127)
    bug_pattern = f'.includes("{del_char}")'
    occurrences = content.count(bug_pattern)
    if occurrences > 1:
        return False, f"bug pattern appears {occurrences} times (expected 1 from fix)"

    # Binary: verify size is preserved
    if binary:
        pass  # size check is done in the patcher itself

    return True, "fix logic OK"


def verify_binary_size(file_path, original_size, tolerance=0):
    """Verify binary file size is preserved after patching.

    tolerance: allow small size change from codesign re-signing on macOS.
    """
    patched_size = os.path.getsize(file_path)
    diff = abs(patched_size - original_size)
    if diff > tolerance:
        return False, f"size mismatch: {original_size} -> {patched_size} (diff={diff})"
    return True, f"size OK (diff={patched_size - original_size})"


def test_npm_versions(versions, results):
    """Test patching npm cli.js versions."""
    for version in versions:
        print(f"{BLUE}-> Testing npm v{version}{NC}")
        print(f"   downloading...", end=" ", flush=True)

        try:
            cli_js = download_npm(version)

            # Test patch
            print("patch...", end=" ", flush=True)
            ok, stdout, stderr = run_patcher(["--path", str(cli_js)])
            if not ok:
                print(f"{RED}x{NC} Patch failed: {stderr}")
                results.append(("npm-patch", version, False))
                continue

            # Verify --version
            print("verify...", end=" ", flush=True)
            ok, output = verify_runs(cli_js)
            if not ok:
                print(f"{RED}x{NC} --version failed")
                results.append(("npm-verify", version, False))
                continue

            # Verify fix logic
            print("logic...", end=" ", flush=True)
            ok, detail = verify_fix_logic(cli_js)
            if not ok:
                print(f"{RED}x{NC} {detail}")
                results.append(("npm-logic", version, False))
                continue

            # Test double-patch
            print("double-patch...", end=" ", flush=True)
            ok, stdout, _ = run_patcher(["--path", str(cli_js)])
            if "patch" not in stdout.lower():
                print(f"{RED}x{NC} double-patch not detected")
                results.append(("npm-double", version, False))
                continue

            # Test restore
            print("restore...", end=" ", flush=True)
            ok, _, stderr = run_patcher(["--restore", "--path", str(cli_js)])
            if not ok:
                print(f"{RED}x{NC} restore failed: {stderr}")
                results.append(("npm-restore", version, False))
                continue

            print(f"{GREEN}ok{NC} {output}")
            results.append(("npm", version, True))

        except Exception as e:
            print(f"{RED}x{NC} {e}")
            results.append(("npm", version, False))

        print()


def test_binary_versions(versions, results):
    """Test patching binary versions."""
    plat = get_current_platform()
    if not plat:
        print(f"{BLUE}-> Skipping binary tests (unsupported platform){NC}")
        return

    for version in versions:
        print(f"{BLUE}-> Testing binary v{version} ({plat}){NC}")
        print(f"   downloading...", end=" ", flush=True)

        try:
            binary_path = download_binary(version, plat)
            original_size = os.path.getsize(binary_path)

            # Test patch
            print("patch...", end=" ", flush=True)
            ok, stdout, stderr = run_patcher(["--path", str(binary_path)])
            if not ok:
                print(f"{RED}x{NC} Patch failed: {stderr}")
                results.append(("bin-patch", f"{version}/{plat}", False))
                continue

            # Verify size preserved (allow small tolerance for codesign)
            print("size...", end=" ", flush=True)
            ok, detail = verify_binary_size(binary_path, original_size,
                                            tolerance=64)
            if not ok:
                print(f"{RED}x{NC} {detail}")
                results.append(("bin-size", f"{version}/{plat}", False))
                continue

            # Verify fix logic
            print("logic...", end=" ", flush=True)
            ok, detail = verify_fix_logic(binary_path, binary=True)
            if not ok:
                print(f"{RED}x{NC} {detail}")
                results.append(("bin-logic", f"{version}/{plat}", False))
                continue

            # Test double-patch
            print("double-patch...", end=" ", flush=True)
            ok, stdout, _ = run_patcher(["--path", str(binary_path)])
            if "patch" not in stdout.lower():
                print(f"{RED}x{NC} double-patch not detected")
                results.append(("bin-double", f"{version}/{plat}", False))
                continue

            # Test restore
            print("restore...", end=" ", flush=True)
            ok, _, stderr = run_patcher(["--restore", "--path", str(binary_path)])
            if not ok:
                print(f"{RED}x{NC} restore failed: {stderr}")
                results.append(("bin-restore", f"{version}/{plat}", False))
                continue

            # Verify restore size (exact match since restore copies original backup)
            ok, detail = verify_binary_size(binary_path, original_size)
            if not ok:
                print(f"{RED}x{NC} restore {detail}")
                results.append(("bin-restore-size", f"{version}/{plat}", False))
                continue

            print(f"{GREEN}ok{NC}")
            results.append(("binary", f"{version}/{plat}", True))

        except Exception as e:
            print(f"{RED}x{NC} {e}")
            results.append(("binary", f"{version}/{plat}", False))

        print()


def main():
    print()
    print("=" * 60)
    print("  Claude Code Vietnamese IME Fix - Test Suite")
    print("=" * 60)
    print()

    # Clean old sources
    if SOURCES_DIR.exists():
        print(f"{BLUE}-> Cleaning old sources...{NC}")
        shutil.rmtree(SOURCES_DIR)

    # Get versions
    print(f"{BLUE}-> Getting latest versions...{NC}")
    versions = get_latest_versions(3)
    print(f"   {', '.join(versions)}")
    print()

    results = []

    # Test npm versions
    test_npm_versions(versions, results)

    # Test binary versions
    test_binary_versions(versions, results)

    # Edge case: nonexistent file
    print(f"{BLUE}-> Testing edge cases{NC}")
    print(f"   nonexistent file...", end=" ", flush=True)
    ok, _, _ = run_patcher(["--path", "/nonexistent/file.js"])
    if not ok:
        print(f"{GREEN}ok{NC} correctly rejected")
        results.append(("edge", "N/A", True))
    else:
        print(f"{RED}x{NC} should have failed")
        results.append(("edge", "N/A", False))
    print()

    # Summary
    print("=" * 60)
    passed = sum(1 for _, _, ok in results if ok)
    total = len(results)

    if passed == total:
        print(f"{GREEN}All {total} tests passed!{NC}")
        return 0
    else:
        print(f"{RED}{passed}/{total} tests passed{NC}")
        for test_type, version, ok in results:
            if not ok:
                print(f"  {RED}FAIL{NC}: {test_type} {version}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
