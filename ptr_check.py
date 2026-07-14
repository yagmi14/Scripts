#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import os
import re
import select
import shutil
import socket
import subprocess
import sys
import termios
import tty
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


VERSION = "2026.07.14-2"
MASK = "xxx"
DIG = shutil.which("dig")


def _char_width(char: str) -> int:
    if not char or unicodedata.combining(char):
        return 0
    return 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1


def _text_width(text: str) -> int:
    return sum(_char_width(char) for char in text)


def _read_utf8_char(fd: int, first: bytes) -> str:
    lead = first[0]
    if lead < 0x80:
        return first.decode("ascii")

    if 0xC2 <= lead <= 0xDF:
        needed = 1
    elif 0xE0 <= lead <= 0xEF:
        needed = 2
    elif 0xF0 <= lead <= 0xF4:
        needed = 3
    else:
        return ""

    data = bytearray(first)
    for _ in range(needed):
        more = os.read(fd, 1)
        if not more:
            break
        data.extend(more)

    try:
        return bytes(data).decode("utf-8")
    except UnicodeDecodeError:
        return ""


def _read_escape_sequence(fd: int) -> bytes:
    sequence = bytearray(b"\x1b")
    # 大多数方向键/功能键序列会在极短时间内完整到达。
    while len(sequence) < 16:
        ready, _, _ = select.select([fd], [], [], 0.03)
        if not ready:
            break
        chunk = os.read(fd, 1)
        if not chunk:
            break
        sequence.extend(chunk)
        if chunk in b"~ABCDHF":
            break
    return bytes(sequence)


def editable_input(prompt: str) -> str:
    """
    不依赖 readline 的终端行编辑器。

    支持：
      - 左右方向键移动光标
      - Home / End
      - Backspace / Delete
      - Ctrl+A / Ctrl+E
      - Ctrl+C 取消
      - UTF-8 粘贴（例如中文逗号、顿号、长横线）

    当 stdin/stdout 不是 TTY 时自动回退到普通 input()。
    """
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return input(prompt)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    chars: list[str] = []
    cursor = 0

    def redraw() -> None:
        text = "".join(chars)
        tail = "".join(chars[cursor:])
        sys.stdout.write("\r" + prompt + text + "\x1b[K")
        tail_width = _text_width(tail)
        if tail_width:
            sys.stdout.write(f"\x1b[{tail_width}D")
        sys.stdout.flush()

    sys.stdout.write(prompt)
    sys.stdout.flush()

    try:
        tty.setraw(fd)

        while True:
            first = os.read(fd, 1)
            if not first:
                raise EOFError

            # Enter
            if first in {b"\r", b"\n"}:
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                return "".join(chars)

            # Ctrl+C
            if first == b"\x03":
                sys.stdout.write("^C\r\n")
                sys.stdout.flush()
                raise KeyboardInterrupt

            # Ctrl+D
            if first == b"\x04":
                if not chars:
                    sys.stdout.write("\r\n")
                    sys.stdout.flush()
                    raise EOFError
                continue

            # Ctrl+A / Ctrl+E
            if first == b"\x01":
                cursor = 0
                redraw()
                continue
            if first == b"\x05":
                cursor = len(chars)
                redraw()
                continue

            # Backspace
            if first in {b"\x7f", b"\x08"}:
                if cursor > 0:
                    del chars[cursor - 1]
                    cursor -= 1
                    redraw()
                continue

            # Escape sequences: arrows, Home, End, Delete.
            if first == b"\x1b":
                sequence = _read_escape_sequence(fd)

                if sequence in {b"\x1b[D", b"\x1bOD"}:       # Left
                    if cursor > 0:
                        cursor -= 1
                        redraw()
                elif sequence in {b"\x1b[C", b"\x1bOC"}:     # Right
                    if cursor < len(chars):
                        cursor += 1
                        redraw()
                elif sequence in {
                    b"\x1b[H", b"\x1bOH", b"\x1b[1~", b"\x1b[7~"
                }:                                            # Home
                    cursor = 0
                    redraw()
                elif sequence in {
                    b"\x1b[F", b"\x1bOF", b"\x1b[4~", b"\x1b[8~"
                }:                                            # End
                    cursor = len(chars)
                    redraw()
                elif sequence == b"\x1b[3~":                  # Delete
                    if cursor < len(chars):
                        del chars[cursor]
                        redraw()
                # 上下键不写入 ^[[A / ^[[B；当前不实现历史记录。
                continue

            char = _read_utf8_char(fd, first)
            if char and char.isprintable():
                chars.insert(cursor, char)
                cursor += 1
                redraw()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def parse_octet_ranges(text: str) -> list[int]:
    """
    支持以下格式：
      0-31,36-39,48-127
      0-31, 36-39, 48-127
      0–31、36–39、48–127
      0 — 31；36 — 39；48 — 127
      63,80,96-111
    """
    translations = str.maketrans({
        "–": "-",
        "—": "-",
        "－": "-",
        "−": "-",
        "，": ",",
        "；": ",",
        ";": ",",
        "、": ",",
    })
    text = text.translate(translations).strip()
    text = re.sub(r"\s*-\s*", "-", text)

    # 英文逗号、中文分隔符转换后得到的逗号，以及空白均可分隔。
    parts = [part for part in re.split(r"[,\s]+", text) if part]
    if not parts:
        raise ValueError("范围不能为空")

    values: set[int] = set()

    for part in parts:
        if re.fullmatch(r"\d{1,3}", part):
            number = int(part)
            if not 0 <= number <= 255:
                raise ValueError(f"数值超出 0-255：{part}")
            values.add(number)
            continue

        match = re.fullmatch(r"(\d{1,3})-(\d{1,3})", part)
        if not match:
            raise ValueError(f"无法识别的范围：{part}")

        start, end = map(int, match.groups())
        if not (0 <= start <= 255 and 0 <= end <= 255):
            raise ValueError(f"范围超出 0-255：{part}")
        if start > end:
            raise ValueError(f"范围起点不能大于终点：{part}")

        values.update(range(start, end + 1))

    return sorted(values)


def build_targets(ip_text: str, range_text: str | None) -> list[str]:
    ip_text = ip_text.strip().lower()

    try:
        return [str(ipaddress.ip_address(ip_text))]
    except ValueError:
        pass

    parts = ip_text.split(".")
    if len(parts) != 4 or parts.count(MASK) != 1:
        raise ValueError(
            "请输入标准 IPv4/IPv6 地址，或包含且仅包含一个 xxx 的 IPv4，"
            "例如 63.xxx.142.193"
        )

    for part in parts:
        if part == MASK:
            continue
        if not part.isdigit() or not 0 <= int(part) <= 255:
            raise ValueError(f"无效的 IPv4 字段：{part}")

    if range_text is None:
        range_text = editable_input(
            "请输入 xxx 的范围（例如 0-31, 36-39, 48-127）："
        ).strip()

    octets = parse_octet_ranges(range_text)
    mask_index = parts.index(MASK)

    targets: list[str] = []
    for octet in octets:
        current = parts.copy()
        current[mask_index] = str(octet)
        targets.append(str(ipaddress.ip_address(".".join(current))))

    return targets


def lookup_ptr(ip: str, timeout: int = 5) -> list[str]:
    if DIG:
        try:
            result = subprocess.run(
                [DIG, "+short", "+time=2", "+tries=1", "-x", ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return []

        return sorted({
            line.strip().rstrip(".")
            for line in result.stdout.splitlines()
            if line.strip()
        })

    try:
        hostname, aliases, _ = socket.gethostbyaddr(ip)
    except (socket.herror, socket.gaierror, OSError):
        return []

    names = {hostname.rstrip(".")}
    names.update(alias.rstrip(".") for alias in aliases if alias)
    return sorted(name for name in names if name)


def ip_sort_key(item: tuple[str, list[str]]) -> tuple[int, int]:
    ip, _ = item
    parsed = ipaddress.ip_address(ip)
    return parsed.version, int(parsed)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="批量检查 IP 是否存在 PTR（反向 DNS）解析"
    )
    parser.add_argument(
        "ip",
        nargs="?",
        help="标准 IP，或含一个 xxx 的 IPv4，例如 63.xxx.142.193",
    )
    parser.add_argument(
        "-r",
        "--range",
        dest="range_text",
        help='xxx 范围，例如 "0-31,36-39,48-127"',
    )
    parser.add_argument(
        "-o",
        "--output",
        default="ptr_results.txt",
        help="结果文件，默认 ptr_results.txt",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=30,
        help="并发线程数，默认 30",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    args = parser.parse_args()

    try:
        ip_text = args.ip or editable_input(
            "请输入 IP（例如 63.111.142.193 或 63.xxx.142.193）："
        ).strip()
        targets = build_targets(ip_text, args.range_text)
    except KeyboardInterrupt:
        print("[取消] 用户中止操作", file=sys.stderr)
        return 130
    except EOFError:
        print("[错误] 输入已结束", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1

    if args.workers < 1:
        print("[错误] workers 必须大于等于 1", file=sys.stderr)
        return 1

    total = len(targets)
    workers = min(args.workers, total)
    print(f"[信息] 脚本版本：{VERSION}")
    print(f"[信息] 待检测：{total} 个 IP，并发：{workers}")

    if not DIG:
        print("[提示] 未检测到 dig，将使用系统解析器；建议安装 dnsutils。")

    hits: list[tuple[str, list[str]]] = []
    completed = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(lookup_ptr, ip): ip
            for ip in targets
        }

        for future in as_completed(future_map):
            ip = future_map[future]
            completed += 1

            try:
                ptr_names = future.result()
            except Exception as exc:
                print(f"[失败] {ip}：{exc}")
                ptr_names = []

            if ptr_names:
                hits.append((ip, ptr_names))
                print(f"[PTR] {ip} -> {', '.join(ptr_names)}")

            if completed % 20 == 0 or completed == total:
                print(
                    f"[进度] {completed}/{total}，"
                    f"已发现 PTR：{len(hits)}"
                )

    hits.sort(key=ip_sort_key)
    output_path = Path(args.output).expanduser()

    try:
        with output_path.open("w", encoding="utf-8") as file:
            for ip, ptr_names in hits:
                file.write(f"{ip}\t{', '.join(ptr_names)}\n")
    except OSError as exc:
        print(f"[错误] 无法写入结果文件：{exc}", file=sys.stderr)
        return 1

    print()
    if hits:
        print(f"[完成] 共发现 {len(hits)} 个存在 PTR 的 IP")
        print(f"[完成] 结果已保存到：{output_path.resolve()}")
    else:
        print("[完成] 没有发现存在 PTR 的 IP")
        print(f"[完成] 已生成空结果文件：{output_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
