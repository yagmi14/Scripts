#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import re
import shutil
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


MASK = "xxx"
DIG = shutil.which("dig")


def parse_octet_ranges(text: str) -> list[int]:
    """
    支持：
      0-31,36-39,48-127
      0–31、36–39、48–127
      0 — 31；36 — 39；48 — 127
      63,80,96-111
    """
    translations = str.maketrans({
        "–": "-",
        "—": "-",
        "－": "-",
        "，": ",",
        "；": ",",
        ";": ",",
        "、": ",",
    })
    text = text.translate(translations).strip()
    text = re.sub(r"\s*-\s*", "-", text)
    parts = [p for p in re.split(r"[,\s]+", text) if p]

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

    # 标准 IP：直接检测。
    try:
        return [str(ipaddress.ip_address(ip_text))]
    except ValueError:
        pass

    # 非标准 IP：当前支持 IPv4 中恰好一个 xxx。
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
        range_text = input(
            "请输入 xxx 的范围（例如 0-31、36-39、48-127）："
        ).strip()

    octets = parse_octet_ranges(range_text)
    mask_index = parts.index(MASK)

    targets: list[str] = []
    for octet in octets:
        current = parts.copy()
        current[mask_index] = str(octet)
        candidate = ".".join(current)
        targets.append(str(ipaddress.ip_address(candidate)))

    return targets


def lookup_ptr(ip: str, timeout: int = 5) -> list[str]:
    """
    优先使用 dig 查询真实 DNS PTR。
    如果系统没有 dig，则回退到 socket.gethostbyaddr()。
    """
    if DIG:
        try:
            result = subprocess.run(
                [
                    DIG,
                    "+short",
                    "+time=2",
                    "+tries=1",
                    "-x",
                    ip,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return []

        names = {
            line.strip().rstrip(".")
            for line in result.stdout.splitlines()
            if line.strip()
        }
        return sorted(names)

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
    args = parser.parse_args()

    ip_text = args.ip or input(
        "请输入 IP（例如 63.111.142.193 或 63.xxx.142.193）："
    ).strip()

    try:
        targets = build_targets(ip_text, args.range_text)
    except ValueError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1

    if args.workers < 1:
        print("[错误] workers 必须大于等于 1", file=sys.stderr)
        return 1

    total = len(targets)
    workers = min(args.workers, total)
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
