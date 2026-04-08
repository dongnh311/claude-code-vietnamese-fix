# Claude Code Vietnamese IME Fix

Fix lỗi gõ tiếng Việt trong Claude Code CLI với các bộ gõ OpenKey, EVKey, PHTV, Unikey... Hỗ trợ **npm cli.js** và **Bun binary** trên macOS, Linux, Windows.

## Vấn đề

Khi gõ tiếng Việt trong Claude Code CLI, các bộ gõ sử dụng kỹ thuật "backspace rồi thay thế" để chuyển đổi ký tự (ví dụ: `a` → `á`). Claude Code xử lý phần backspace nhưng không chèn ký tự thay thế, dẫn đến:

- Ký tự bị "nuốt" hoặc mất khi gõ
- Văn bản hiển thị không đúng với những gì đã gõ
- Phải copy-paste từ nơi khác thay vì gõ trực tiếp

### Tính năng

- Hỗ trợ cả **npm cli.js** và **Bun single-file binary**
- **Fix lỗi gõ nhanh**: Khắc phục hiện tượng gõ nhanh bị mất chữ hoặc biến thành khoảng trắng
- **Fix lỗi chập chờn**: Sửa lỗi "lúc gõ được, lúc không" do cache trạng thái gợi ý
- **Bảo toàn phím Backspace gốc**: Phím Backspace vật lý giữ nguyên hành vi xóa tiêu chuẩn
- **Multi-account**: Scan và patch nhiều Claude Code installation trên cùng 1 máy
- **Interactive menu**: Chọn patch/restore từng installation hoặc tất cả

## Cài đặt

**macOS / Linux:**

```bash
curl -fsSL https://raw.githubusercontent.com/dongnh311/claude-code-vietnamese-fix/main/install.sh | bash
```

**Windows (PowerShell):**

```powershell
irm https://raw.githubusercontent.com/dongnh311/claude-code-vietnamese-fix/main/install.ps1 | iex
```

Lần đầu chạy sẽ hiển thị **interactive menu** để chọn action:

```
================================================
  Claude Code Vietnamese IME Fix
================================================

  Claude Code installations:
  [1] /Users/you/.nvm/.../cli.js
      (npm, PATH) [NOT PATCHED]
  [2] /Users/you/.bun/bin/claude
      (binary, bun) [NOT PATCHED]

  Claude config directories:
      /Users/you/.claude
      /Users/you/.claude-work

  Actions:
  [P] Patch auto-detect
  [1-2] Patch installation cu the
  [R] Restore tu backup (0 da patch)
  [S] Scan lai
  [Q] Thoat

  Chon>
```

## Sau khi update Claude Code

Chạy lại fix:

```bash
python3 ~/.claude-vn-fix/patcher.py
```

**Windows:**

```powershell
python ~\.claude-vn-fix\patcher.py
```

## Các lệnh

```bash
python3 patcher.py                  # Interactive menu
python3 patcher.py --auto           # Tự động phát hiện và fix
python3 patcher.py --scan           # Liệt kê tất cả installations
python3 patcher.py --restore        # Khôi phục từ backup (auto-detect)
python3 patcher.py --restore-all    # Khôi phục tất cả installations
python3 patcher.py --path FILE      # Fix file cụ thể
python3 patcher.py --help           # Hiển thị hướng dẫn
```

### Multi-account

Nếu bạn dùng nhiều tài khoản Claude (alias) trên cùng 1 máy, patcher sẽ tự scan tất cả installations và config directories (`~/.claude*`). Dùng interactive menu hoặc `--scan` để xem, chọn số để patch/restore từng cái.

## Cập nhật patcher

```bash
cd ~/.claude-vn-fix && git pull
```

## Credits

Tham khảo và cải tiến từ [PHTV](https://github.com/phamhungtien/PHTV) và [0x0a0d](https://github.com/0x0a0d/fix-vietnamese-claude-code).
