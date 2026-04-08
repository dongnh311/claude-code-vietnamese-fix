#!/usr/bin/env python3
"""
Claude Code Vietnamese IME Fix

Fixes Vietnamese input bug in Claude Code CLI (npm & binary) by patching
the backspace handling logic to also insert replacement text.

Supports:
  - npm cli.js (Node.js)
  - Bun single-file binary (macOS, Linux, Windows)

Usage:
  python3 patcher.py              Auto-detect and fix
  python3 patcher.py --restore    Restore from backup
  python3 patcher.py --path FILE  Fix specific file

Repository: https://github.com/dongnh311/claude-code-vietnamese-fix
License: MIT
"""

import os
import re
import sys
import shutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime

PATCH_MARKER = "/* Vietnamese IME fix */"
DEL_CHAR = chr(127)  # 0x7F - character used by Vietnamese IME for backspace


def find_claude():
    """Auto-detect Claude Code installation - binary or npm cli.js."""
    home = Path.home()
    is_windows = platform.system() == 'Windows'

    def run_cmd(cmd):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0].strip()
        except Exception:
            pass
        return ''

    # 1) which/where claude -> resolves to binary or symlink to cli.js
    cmd = ['where', 'claude'] if is_windows else ['which', 'claude']
    p = run_cmd(cmd)
    if p and os.path.exists(p):
        if not is_windows:
            p = os.path.realpath(p)
        if os.path.exists(p):
            return p

    # 2) Bun global paths
    bun_install = os.environ.get('BUN_INSTALL', str(home / '.bun'))
    bun_paths = [
        Path(bun_install) / 'bin' / ('claude.exe' if is_windows else 'claude'),
        Path(bun_install) / 'install' / 'global' / 'node_modules'
        / '@anthropic-ai' / 'claude-code' / 'cli.js',
    ]
    for bp in bun_paths:
        if bp.exists():
            return str(bp)

    # 3) npm global root
    npm_root = run_cmd(['npm', 'root', '-g'])
    if npm_root:
        cli_path = Path(npm_root) / '@anthropic-ai' / 'claude-code' / 'cli.js'
        if cli_path.exists():
            return str(cli_path)

    # 4) Search common npm install directories
    if is_windows:
        search_dirs = [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'npm-cache' / '_npx',
            Path(os.environ.get('APPDATA', '')) / 'npm' / 'node_modules',
        ]
    else:
        search_dirs = [
            home / '.npm' / '_npx',
            home / '.nvm' / 'versions' / 'node',
            Path('/usr/local/lib/node_modules'),
            Path('/opt/homebrew/lib/node_modules'),
        ]

    for d in search_dirs:
        if d.exists():
            for cli_js in d.rglob('*/@anthropic-ai/claude-code/cli.js'):
                return str(cli_js)

    # 5) Windows NVM fallback
    if is_windows:
        win_paths = [
            Path(os.environ.get('APPDATA', '')) / 'npm' / 'node_modules'
            / '@anthropic-ai' / 'claude-code' / 'cli.js',
            Path(os.environ.get('LOCALAPPDATA', '')) / 'npm' / 'node_modules'
            / '@anthropic-ai' / 'claude-code' / 'cli.js',
        ]
        nvm_home = os.environ.get('NVM_HOME')
        if nvm_home:
            try:
                for d in os.listdir(nvm_home):
                    win_paths.append(
                        Path(nvm_home) / d / 'node_modules'
                        / '@anthropic-ai' / 'claude-code' / 'cli.js'
                    )
            except OSError:
                pass
        for wp in win_paths:
            if wp.exists():
                return str(wp)

    raise FileNotFoundError(
        "Khong tim thay Claude Code.\n"
        "Cai dat truoc: npm install -g @anthropic-ai/claude-code"
    )


def find_all_claude():
    """Scan for ALL Claude Code installations (binary + npm)."""
    home = Path.home()
    is_windows = platform.system() == 'Windows'
    found = []
    seen = set()

    def add(p, source):
        p = str(p)
        rp = os.path.realpath(p)
        if rp not in seen and os.path.exists(p):
            seen.add(rp)
            found.append({'path': p, 'source': source})

    def run_cmd(cmd):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0].strip()
        except Exception:
            pass
        return ''

    # 1) which/where claude
    cmd = ['where', 'claude'] if is_windows else ['which', 'claude']
    p = run_cmd(cmd)
    if p and os.path.exists(p):
        if not is_windows:
            p = os.path.realpath(p)
        add(p, 'PATH')

    # 2) Bun paths
    bun_install = os.environ.get('BUN_INSTALL', str(home / '.bun'))
    bun_bin = Path(bun_install) / 'bin' / ('claude.exe' if is_windows else 'claude')
    if bun_bin.exists():
        add(bun_bin, 'bun')
    bun_cli = (Path(bun_install) / 'install' / 'global' / 'node_modules'
               / '@anthropic-ai' / 'claude-code' / 'cli.js')
    if bun_cli.exists():
        add(bun_cli, 'bun/npm')

    # 3) npm global root
    npm_root = run_cmd(['npm', 'root', '-g'])
    if npm_root:
        cli_path = Path(npm_root) / '@anthropic-ai' / 'claude-code' / 'cli.js'
        if cli_path.exists():
            add(cli_path, 'npm global')

    # 4) Search npm directories
    if is_windows:
        search_dirs = [
            Path(os.environ.get('LOCALAPPDATA', '')) / 'npm-cache' / '_npx',
            Path(os.environ.get('APPDATA', '')) / 'npm' / 'node_modules',
        ]
    else:
        search_dirs = [
            home / '.npm' / '_npx',
            home / '.nvm' / 'versions' / 'node',
            Path('/usr/local/lib/node_modules'),
            Path('/opt/homebrew/lib/node_modules'),
        ]

    for d in search_dirs:
        if d.exists():
            for cli_js in d.rglob('*/@anthropic-ai/claude-code/cli.js'):
                add(cli_js, f'npm ({d.name})')

    # 5) Windows fallbacks
    if is_windows:
        for base in [os.environ.get('APPDATA', ''), os.environ.get('LOCALAPPDATA', '')]:
            wp = Path(base) / 'npm' / 'node_modules' / '@anthropic-ai' / 'claude-code' / 'cli.js'
            if wp.exists():
                add(wp, 'npm (Windows)')
        nvm_home = os.environ.get('NVM_HOME')
        if nvm_home:
            try:
                for d in os.listdir(nvm_home):
                    wp = Path(nvm_home) / d / 'node_modules' / '@anthropic-ai' / 'claude-code' / 'cli.js'
                    if wp.exists():
                        add(wp, f'nvm ({d})')
            except OSError:
                pass

    return found


def find_claude_configs():
    """Find all .claude config directories."""
    home = Path.home()
    configs = []
    try:
        for item in home.iterdir():
            if item.is_dir() and item.name.startswith('.claude'):
                configs.append(str(item))
    except OSError:
        pass
    configs.sort()
    return configs


def check_patch_status(file_path):
    """Check if a file is already patched. Returns 'patched', 'unpatched', or 'error'."""
    try:
        binary = is_binary(file_path)
        if binary:
            with open(file_path, 'rb') as f:
                content = f.read().decode('latin1')
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        if PATCH_MARKER in content:
            return 'patched'
        return 'unpatched'
    except Exception:
        return 'error'


def is_binary(file_path):
    """Check if the target is a binary (not .js)."""
    return not file_path.endswith('.js')


def find_bug_block(content):
    """Find the if-block containing the Vietnamese IME bug pattern."""
    # cli.js: raw 0x7F byte in string literal
    # binary: escaped \x7F or \x7f as literal text
    for pattern in [
        f'.includes("{DEL_CHAR}")',
        r'.includes("\x7F")',
        r'.includes("\x7f")',
    ]:
        idx = content.find(pattern)
        if idx != -1:
            break

    if idx == -1:
        raise RuntimeError(
            'Khong tim thay bug pattern .includes("\\x7f").\n'
            "Claude Code co the da duoc Anthropic fix."
        )

    # Find the containing if(
    block_start = content.rfind('if(', max(0, idx - 150), idx)
    if block_start == -1:
        raise RuntimeError("Khong tim thay block if chua pattern")

    # Find matching closing brace
    depth = 0
    block_end = idx
    for i, c in enumerate(content[block_start:block_start + 800]):
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                block_end = block_start + i + 1
                break

    if depth != 0:
        raise RuntimeError("Khong tim thay closing brace cua block if")

    return block_start, block_end, content[block_start:block_end]


def extract_variables(block):
    """Extract dynamic variable names from the bug block."""
    # Normalize DEL char for regex matching
    # cli.js: raw 0x7F byte -> escaped \x7f
    # binary: may have uppercase \x7F -> lowercase \x7f
    normalized = block.replace(DEL_CHAR, '\\x7f').replace('\\x7F', '\\x7f')

    # Match: let COUNT=(INPUT.match(/\x7f/g)||[]).length,STATE=CURSTATE;
    m = re.search(
        r'let ([\w$]+)=\(\w+\.match\(/\\x7f/g\)\|\|\[\]\)\.length[,;]([\w$]+)=([\w$]+)[;,]',
        normalized
    )
    if not m:
        raise RuntimeError("Khong trich xuat duoc bien count/state")

    state, cur_state = m.group(2), m.group(3)

    # Match: UPDATETEXT(STATE.text);UPDATEOFFSET(STATE.offset)
    m2 = re.search(
        rf'([\w$]+)\({re.escape(state)}\.text\);([\w$]+)\({re.escape(state)}\.offset\)',
        block
    )
    if not m2:
        raise RuntimeError("Khong trich xuat duoc update functions")

    # Match: INPUT.includes("
    m3 = re.search(r'([\w$]+)\.includes\("', block)
    if not m3:
        raise RuntimeError("Khong trich xuat duoc input variable")

    # Match: }RESET1(),RESET2();return} at end of block
    m4 = re.search(r'\}([\w$]+)\(\),([\w$]+)\(\);return\}', block)
    if not m4:
        raise RuntimeError("Khong trich xuat duoc reset functions (G48/v48)")

    # Match: if(!KEY_META.backspace to extract the key metadata parameter name
    m5 = re.search(r'if\(!([\w$]+)\.backspace', block)
    if not m5:
        raise RuntimeError("Khong trich xuat duoc key metadata variable")

    return {
        'input': m3.group(1),
        'key_meta': m5.group(1),
        'state': state,
        'cur_state': cur_state,
        'update_text': m2.group(1),
        'update_offset': m2.group(2),
        'reset_fn1': m4.group(1),
        'reset_fn2': m4.group(2),
    }


def generate_fix(v):
    """Generate the fix code that does backspace + insert replacement text."""
    return (
        f'{PATCH_MARKER}'
        f'if(!{v["key_meta"]}.backspace&&!{v["key_meta"]}.delete&&{v["input"]}.includes("\\x7f")){{'
        f'let {v["state"]}={v["cur_state"]};'
        f'for(const _c of {v["input"]}){{'
        f'if(_c==="\\x7f"){v["state"]}={v["state"]}.backspace();'
        f'else {v["state"]}={v["state"]}.insert(_c);'
        f'}}'
        f'if(!{v["cur_state"]}.equals({v["state"]})){{'
        f'if({v["cur_state"]}.text!=={v["state"]}.text)'
        f'{v["update_text"]}({v["state"]}.text);'
        f'{v["update_offset"]}({v["state"]}.offset)'
        f'}}{v["reset_fn1"]}(),{v["reset_fn2"]}();return;}}'
    )


def compensate_binary_size(content, patch_position, size_diff):
    """Compensate for size change in Bun binary by trimming pragma comment bytes.

    Bun single-file executables have '\\x00// @bun ' pragmas before each
    embedded JS module. We trim bytes from the first comment line after
    the pragma to keep binary size identical.
    """
    pragma = '// @bun '

    # Search backwards from patch position for \x00// @bun
    search_start = max(0, patch_position - 100000)
    for j in range(patch_position - 1, search_start - 1, -1):
        if content[j] == '\x00':
            if content[j + 1:j + 1 + len(pragma)] == pragma:
                # Find first \n// after pragma
                pragma_end = j + 1 + len(pragma)
                for k in range(pragma_end, patch_position):
                    if (content[k] == '\n'
                            and k + 2 < len(content)
                            and content[k + 1] == '/'
                            and content[k + 2] == '/'):
                        slice_start = k + 3
                        if slice_start + size_diff > len(content):
                            raise RuntimeError(
                                "Comment line qua ngan de compensate size diff"
                            )
                        content = (content[:slice_start]
                                   + content[slice_start + size_diff:])
                        return content
                break

    raise RuntimeError(
        "Khong tim thay pragma '// @bun' trong binary. "
        "File nay co the khong phai Bun single-file executable."
    )


def codesign_binary(file_path):
    """Re-sign binary on macOS (required for Gatekeeper)."""
    if platform.system() != 'Darwin':
        return
    try:
        subprocess.run(
            ['codesign', '--sign', '-', '--force',
             '--preserve-metadata=entitlements,requirements,flags', file_path],
            check=True, capture_output=True
        )
        print("   Re-signed binary.")
    except FileNotFoundError:
        pass
    except subprocess.CalledProcessError:
        print("   Warning: Re-sign failed. Run manually:", file=sys.stderr)
        print(f'   codesign --sign - --force '
              f'--preserve-metadata=entitlements,requirements,flags '
              f'"{file_path}"', file=sys.stderr)


def find_latest_backup(file_path):
    """Find the most recent backup file."""
    dir_path = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    backups = [
        os.path.join(dir_path, f) for f in os.listdir(dir_path or '.')
        if f.startswith(f"{filename}.backup-")
    ]
    if not backups:
        return None
    backups.sort(key=os.path.getmtime, reverse=True)
    return backups[0]


def patch(file_path):
    """Apply Vietnamese IME fix to cli.js or binary."""
    binary = is_binary(file_path)
    encoding = 'latin1' if binary else 'utf-8'

    print(f"-> File{' (binary)' if binary else ''}: {file_path}")

    if not os.path.exists(file_path):
        print(f"Loi: File khong ton tai: {file_path}", file=sys.stderr)
        return 1

    # Read (binary mode for Bun executables to preserve \r\n)
    if binary:
        with open(file_path, 'rb') as f:
            raw = f.read()
        original_size = len(raw)
        content = raw.decode('latin1')
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        original_size = None

    # Already patched?
    if PATCH_MARKER in content:
        print("Da patch truoc do.")
        return 0

    # Backup
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{file_path}.backup-{timestamp}"
    shutil.copy2(file_path, backup_path)
    print(f"   Backup: {backup_path}")

    try:
        # Find bug block
        block_start, block_end, block = find_bug_block(content)

        # Extract variables
        variables = extract_variables(block)
        print(f"   Vars: input={variables['input']}, state={variables['state']}, "
              f"cur={variables['cur_state']}")

        # Generate fix and replace
        fix_code = generate_fix(variables)
        patched = content[:block_start] + fix_code + content[block_end:]

        # Binary: compensate size to keep offsets valid
        if binary:
            size_diff = len(patched) - original_size
            if size_diff > 0:
                patched = compensate_binary_size(patched, block_start, size_diff)
            elif size_diff < 0:
                # Patch shorter than original - pad fix with spaces
                patched = (content[:block_start]
                           + fix_code + (' ' * abs(size_diff))
                           + content[block_end:])

            if len(patched) != original_size:
                raise RuntimeError(
                    f"Binary size mismatch: original={original_size}, "
                    f"patched={len(patched)}, diff={len(patched) - original_size}"
                )

        # Write (binary mode for Bun executables)
        if binary:
            with open(file_path, 'wb') as f:
                f.write(patched.encode('latin1'))
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(patched)

        # Verify
        if binary:
            with open(file_path, 'rb') as f:
                verify_content = f.read().decode('latin1')
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                verify_content = f.read()
        if PATCH_MARKER not in verify_content:
                raise RuntimeError("Verify failed: patch marker not found after write")

        # Binary on macOS: re-sign
        if binary:
            codesign_binary(file_path)

        print("\n   Patch thanh cong! Khoi dong lai Claude Code.\n")
        return 0

    except Exception as e:
        print(f"\nLoi: {e}", file=sys.stderr)
        print("Bao loi tai: https://github.com/dongnh311/claude-code-vietnamese-fix/issues",
              file=sys.stderr)
        # Rollback
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            os.remove(backup_path)
            print("Da rollback ve ban goc.", file=sys.stderr)
        return 1


def restore(file_path):
    """Restore file from latest backup."""
    backup = find_latest_backup(file_path)
    if not backup:
        print(f"Khong tim thay backup cho {file_path}", file=sys.stderr)
        return 1

    shutil.copy2(backup, file_path)
    print(f"Da khoi phuc tu: {backup}")

    print("Khoi dong lai Claude Code.")
    return 0


def show_help():
    print("Claude Code Vietnamese IME Fix")
    print("")
    print("Su dung:")
    print("  python3 patcher.py                  Interactive menu")
    print("  python3 patcher.py --auto           Tu dong phat hien va fix")
    print("  python3 patcher.py --restore        Khoi phuc tu backup (auto-detect)")
    print("  python3 patcher.py --restore-all    Khoi phuc tat ca installations")
    print("  python3 patcher.py --scan           Liet ke tat ca cai dat")
    print("  python3 patcher.py --path FILE      Fix file cu the")
    print("  python3 patcher.py --help           Hien thi huong dan")
    print("")
    print("Supports: npm cli.js & Bun binary (macOS/Linux/Windows)")
    print("")
    print("https://github.com/dongnh311/claude-code-vietnamese-fix")


def scan_and_display():
    """Scan and display all Claude installations and config dirs."""
    installations = find_all_claude()
    configs = find_claude_configs()

    print("")
    if installations:
        print("  Claude Code installations:")
        for i, inst in enumerate(installations, 1):
            file_type = "binary" if is_binary(inst['path']) else "npm"
            status = check_patch_status(inst['path'])
            if status == 'patched':
                tag = "\033[32m[PATCHED]\033[0m"
            elif status == 'unpatched':
                tag = "\033[33m[NOT PATCHED]\033[0m"
            else:
                tag = "\033[31m[ERROR]\033[0m"
            print(f"  [{i}] {inst['path']}")
            print(f"      ({file_type}, {inst['source']}) {tag}")
    else:
        print("  Khong tim thay Claude Code installation nao.")

    if configs:
        print("")
        print("  Claude config directories:")
        for cfg in configs:
            print(f"      {cfg}")

    print("")
    return installations


def interactive_menu():
    """Show interactive menu for user to choose action."""
    print("")
    print("================================================")
    print("  Claude Code Vietnamese IME Fix")
    print("================================================")

    installations = scan_and_display()

    while True:
        patched_count = sum(1 for inst in installations
                            if check_patch_status(inst['path']) == 'patched')
        print("  Actions:")
        print("  [P] Patch auto-detect")
        if installations:
            print(f"  [1-{len(installations)}] Patch installation cu the")
        print(f"  [R] Restore tu backup" + (
            f" ({patched_count} da patch)" if patched_count else ""))
        print("  [S] Scan lai")
        print("  [Q] Thoat")
        print("")

        try:
            choice = input("  Chon> ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("")
            return 0

        if choice == 'Q':
            return 0
        elif choice == 'S':
            installations = scan_and_display()
        elif choice == 'P':
            try:
                file_path = find_claude()
                return patch(file_path)
            except FileNotFoundError as e:
                print(f"  Loi: {e}")
        elif choice == 'R':
            # Restore sub-menu
            patched = [inst for inst in installations
                       if check_patch_status(inst['path']) == 'patched']
            if not patched:
                print("  Khong co installation nao da patch de restore.")
                continue
            print("")
            print("  Restore:")
            for i, inst in enumerate(patched, 1):
                file_type = "binary" if is_binary(inst['path']) else "npm"
                print(f"  [{i}] {inst['path']} ({file_type})")
            print(f"  [A] Restore ALL ({len(patched)} installations)")
            print(f"  [B] Quay lai")
            print("")
            try:
                sub = input("  Chon> ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print("")
                continue
            if sub == 'B':
                pass
            elif sub == 'A':
                ok_count = 0
                for inst in patched:
                    print(f"\n-> Restore: {inst['path']}")
                    if restore(inst['path']) == 0:
                        ok_count += 1
                print(f"\n  Restore {ok_count}/{len(patched)} thanh cong.")
                if ok_count > 0:
                    return 0
            elif sub.isdigit():
                idx = int(sub) - 1
                if 0 <= idx < len(patched):
                    result = restore(patched[idx]['path'])
                    if result == 0:
                        installations = scan_and_display()
                else:
                    print("  Lua chon khong hop le.")
            else:
                print("  Lua chon khong hop le.")
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(installations):
                return patch(installations[idx]['path'])
            print("  Lua chon khong hop le.")
        else:
            print("  Lua chon khong hop le.")
        print("")


def main():
    args = sys.argv[1:]

    if '--help' in args or '-h' in args:
        show_help()
        return 0

    # --scan: list all installations
    if '--scan' in args:
        scan_and_display()
        return 0

    # --restore-all: restore all patched installations
    if '--restore-all' in args:
        installations = find_all_claude()
        patched = [inst for inst in installations
                   if check_patch_status(inst['path']) == 'patched']
        if not patched:
            print("Khong co installation nao da patch de restore.")
            return 0
        ok_count = 0
        for inst in patched:
            print(f"\n-> Restore: {inst['path']}")
            if restore(inst['path']) == 0:
                ok_count += 1
        print(f"\nRestore {ok_count}/{len(patched)} thanh cong.")
        return 0 if ok_count == len(patched) else 1

    # --restore
    if '--restore' in args:
        args.remove('--restore')
        file_path = None
        if '--path' in args:
            idx = args.index('--path')
            file_path = args[idx + 1]
        else:
            file_path = find_claude()
        return restore(file_path)

    # --auto: auto-detect and patch (no menu)
    if '--auto' in args:
        file_path = find_claude()
        return patch(file_path)

    # --path: patch specific file
    if '--path' in args:
        idx = args.index('--path')
        file_path = args[idx + 1]
        return patch(file_path)

    # Default: interactive menu
    return interactive_menu()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except FileNotFoundError as e:
        print(f"Loi: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Loi: {e}", file=sys.stderr)
        sys.exit(1)
