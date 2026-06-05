#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egressctl.py

Interactive helper for maintaining Mihomo outbound proxies, per-node SOCKS listeners,
and /root/projects/EgressWatch/config.yaml nodes.

Default paths can be overridden with environment variables:
  MIHOMO_CONFIG=/etc/mihomo/config.yaml
  EGRESSWATCH_CONFIG=/root/projects/EgressWatch/config.yaml
  MIHOMO_SERVICE=mihomo
  EW_PORT_MIN=11000
  EW_PORT_MAX=11999
  EW_SKIP_TEST=1        # skip `mihomo -t -f ...` validation
  EW_SKIP_RELOAD=1      # skip systemctl reload/restart
  EW_PROJECT_DIR=/root/projects/EgressWatch
  EW_CRON_MARKER=egressctl:EgressWatch
  EW_SPEEDTEST_URL=https://updates.cdn-apple.com/2024FallFCS/fullrestores/072-56000/8475F789-7D9E-4676-8344-803B762D1F3C/iPhone12%2C3%2CiPhone12%2C5_18.2.1_22C161_Restore.ipsw
  EW_SPEEDTEST_DURATION=15
  EW_SPEEDTEST_CONNECT_TIMEOUT=15
  MIHOMO_SUB_URL=                  # optional; if unset, menu 9 will prompt for input
  EGRESSWATCH_SUB_URL=            # optional; if unset, menu 9 will prompt for input
  SUBSCRIPTION_TIMEOUT=30
  SUBSCRIPTION_SYNC_HOURS=4
  SUBSCRIPTION_CRON_MARKER=egressctl:SubscriptionSync
  EGRESSCTL_STATE_FILE=~/.config/egressctl/state.yaml  # stores last subscription URLs
  EGRESSCTL_SOURCE_URL=https://raw.githubusercontent.com/yagmi14/Scripts/refs/heads/main/egressctl.py
  EGRESSCTL_COMMAND="python3 <(curl --compressed -fsSL https://raw.githubusercontent.com/yagmi14/Scripts/refs/heads/main/egressctl.py)"
  EGRESSCTL_EXEC=/usr/local/sbin/egressctl  # optional, only used when explicitly set
"""
from __future__ import annotations

import argparse
import base64
import io
import copy
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

MIHOMO_CONFIG = Path(os.environ.get("MIHOMO_CONFIG", "/etc/mihomo/config.yaml"))
EGRESSWATCH_CONFIG = Path(os.environ.get("EGRESSWATCH_CONFIG", "/root/projects/EgressWatch/config.yaml"))
MIHOMO_SERVICE = os.environ.get("MIHOMO_SERVICE", "mihomo")
PORT_MIN = int(os.environ.get("EW_PORT_MIN", "11000"))
PORT_MAX = int(os.environ.get("EW_PORT_MAX", "11999"))
LOCAL_LISTEN = os.environ.get("EW_LOCAL_LISTEN", "127.0.0.1")
EGRESSWATCH_PROJECT_DIR = Path(os.environ.get("EW_PROJECT_DIR", "/root/projects/EgressWatch"))
EGRESSWATCH_ENV = Path(os.environ.get("EW_ENV_FILE", str(EGRESSWATCH_PROJECT_DIR / ".env")))
EGRESSWATCH_PYTHON = Path(os.environ.get("EW_PYTHON", str(EGRESSWATCH_PROJECT_DIR / ".venv/bin/python")))
EGRESSWATCH_SCRIPT = os.environ.get("EW_SCRIPT", "egress_watch.py")
EGRESSWATCH_LOG = os.environ.get("EW_LOG", "run.log")
EGRESSWATCH_CRON_MARKER = os.environ.get("EW_CRON_MARKER", "egressctl:EgressWatch")
APPLE_CDN_SPEEDTEST_URL = os.environ.get(
    "EW_SPEEDTEST_URL",
    "https://updates.cdn-apple.com/2024FallFCS/fullrestores/072-56000/8475F789-7D9E-4676-8344-803B762D1F3C/iPhone12%2C3%2CiPhone12%2C5_18.2.1_22C161_Restore.ipsw",
)
SPEEDTEST_DURATION = int(os.environ.get("EW_SPEEDTEST_DURATION", "15"))
SPEEDTEST_CONNECT_TIMEOUT = int(os.environ.get("EW_SPEEDTEST_CONNECT_TIMEOUT", "15"))
MIHOMO_SUBSCRIPTION_URL = os.environ.get("MIHOMO_SUB_URL", "").strip()
EGRESSWATCH_SUBSCRIPTION_URL = os.environ.get("EGRESSWATCH_SUB_URL", "").strip()
SUBSCRIPTION_TIMEOUT = int(os.environ.get("SUBSCRIPTION_TIMEOUT", "30"))
SUBSCRIPTION_DEFAULT_INTERVAL_HOURS = int(os.environ.get("SUBSCRIPTION_SYNC_HOURS", "4"))
SUBSCRIPTION_CRON_MARKER = os.environ.get("SUBSCRIPTION_CRON_MARKER", "egressctl:SubscriptionSync")
EGRESSCTL_SOURCE_URL = os.environ.get(
    "EGRESSCTL_SOURCE_URL",
    "https://raw.githubusercontent.com/yagmi14/Scripts/refs/heads/main/egressctl.py",
)
# For cron jobs, aliases from ~/.zshrc are not available. Use a real command string.
# If EGRESSCTL_COMMAND is empty, the script uses:
#   python3 <(curl --compressed -fsSL "$EGRESSCTL_SOURCE_URL")
# EGRESSCTL_EXEC remains supported for users who installed a local executable.
EGRESSCTL_COMMAND = os.environ.get("EGRESSCTL_COMMAND", "")
EGRESSCTL_EXEC = os.environ.get("EGRESSCTL_EXEC", "")
SUBSCRIPTION_SYNC_LOG = os.environ.get("SUBSCRIPTION_SYNC_LOG", "subscription_sync.log")
EGRESSCTL_STATE_FILE = Path(os.environ.get("EGRESSCTL_STATE_FILE", str(Path.home() / ".config" / "egressctl" / "state.yaml")))
BACKUP_KEEP = int(os.environ.get("EGRESSCTL_BACKUP_KEEP", "3"))

COUNTRY_GROUPS = ["HK", "JP", "SG", "TW", "KR", "US", "Intl"]
COUNTRY_CODES = set(COUNTRY_GROUPS[:-1])
MANAGED_GROUPS = set(COUNTRY_GROUPS)

try:
    from ruamel.yaml import YAML  # type: ignore

    _YAML_KIND = "ruamel"
except Exception:
    YAML = None  # type: ignore
    _YAML_KIND = "pyyaml"
    try:
        import yaml as pyyaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        print("缺少 YAML 库：请先安装 python3-ruamel.yaml 或 PyYAML。", file=sys.stderr)
        print(f"导入错误：{exc}", file=sys.stderr)
        sys.exit(1)


def yaml_loader() -> Any:
    if _YAML_KIND == "ruamel":
        y = YAML()  # type: ignore[operator]
        y.preserve_quotes = True
        y.width = 4096
        y.indent(mapping=2, sequence=4, offset=2)
        return y
    return None


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        if _YAML_KIND == "ruamel":
            data = yaml_loader().load(f)
        else:
            data = pyyaml.safe_load(f)  # type: ignore[name-defined]
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} 的顶层不是 YAML map/object")
    return data


def dump_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if _YAML_KIND == "ruamel":
                yaml_loader().dump(data, f)
            else:
                pyyaml.safe_dump(  # type: ignore[name-defined]
                    data,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def make_backups(paths: Iterable[Path]) -> List[Tuple[Path, Path]]:
    ts = time.strftime("%Y%m%d%H%M%S")
    backups: List[Tuple[Path, Path]] = []
    for path in paths:
        if path.exists():
            backup = path.with_name(f"{path.name}.bak.{ts}")
            shutil.copy2(path, backup)
            backups.append((path, backup))
            print(f"已备份：{path} -> {backup}")
    return backups


def cleanup_old_backups(paths: Iterable[Path], keep: int = BACKUP_KEEP) -> None:
    """Keep only the newest backup files for each configured file.

    Backups are named like config.yaml.bak.20260605090002. Cleanup is
    intentionally called only after config validation/reload succeeds, so a
    failed save still has its just-created backup available for rollback.
    Set EGRESSCTL_BACKUP_KEEP=0 to delete all old backups, or a larger number
    to keep more history.
    """
    try:
        keep = max(int(keep), 0)
    except Exception:
        keep = 3

    for path in paths:
        parent = path.parent
        if not parent.exists():
            continue
        pattern = f"{path.name}.bak.*"
        backups = [p for p in parent.glob(pattern) if p.is_file()]
        backups.sort(key=lambda p: (p.name.rsplit(".bak.", 1)[-1], p.stat().st_mtime), reverse=True)
        for old_backup in backups[keep:]:
            try:
                old_backup.unlink()
                print(f"已删除旧备份：{old_backup}")
            except Exception as exc:
                print(f"警告：删除旧备份失败：{old_backup}：{exc}", file=sys.stderr)


def restore_backups(backups: List[Tuple[Path, Path]]) -> None:
    for path, backup in backups:
        if backup.exists():
            shutil.copy2(backup, path)
            print(f"已回滚：{path} <- {backup}")


def ensure_list(cfg: Dict[str, Any], key: str) -> List[Any]:
    val = cfg.get(key)
    if not isinstance(val, list):
        cfg[key] = []
    return cfg[key]


def as_dict(obj: Any) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}


def norm_name(value: Any) -> str:
    return str(value or "").strip()


def canonical_node_name(value: Any) -> str:
    """Return the logical outbound node name.

    Legacy/compat SOCKS entries are often named like:
      HK / CMHK α / Socks

    The real Mihomo outbound proxy is usually:
      HK / CMHK α

    For menu display and edit/delete operations, both names are treated as
    the same logical node.
    """
    s = norm_name(value)
    if not s:
        return ""
    s = re.sub(r"\s*/\s*", " / ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*/\s*Socks\s*$", "", s, flags=re.IGNORECASE).strip()
    return s


def leading_flag_country_code(value: str) -> Tuple[Optional[str], str]:
    """Return (country_code, remaining_text) when a name starts with a flag emoji.

    Regional-indicator flag emojis are two Unicode code points. This converts
    the leading flag to its ISO two-letter country code, e.g. 🇭🇰 -> HK.
    Multiple leading flags are stripped; the first flag code is used.
    """
    s = str(value or "").lstrip()
    first_code: Optional[str] = None

    def is_regional_indicator(ch: str) -> bool:
        return 0x1F1E6 <= ord(ch) <= 0x1F1FF

    while len(s) >= 2 and is_regional_indicator(s[0]) and is_regional_indicator(s[1]):
        code = chr(ord("A") + ord(s[0]) - 0x1F1E6) + chr(ord("A") + ord(s[1]) - 0x1F1E6)
        if first_code is None:
            first_code = code
        s = s[2:].lstrip()
    return first_code, s


def normalize_subscription_node_name(value: Any) -> str:
    """Normalize names coming from subscriptions.

    Examples:
      🇭🇰 CMHK α       -> HK / CMHK α
      🇭🇰 HK / CMHK α  -> HK / CMHK α
      JP / IIJ α      -> JP / IIJ α

    Non-subscription/manual names still use canonical_node_name().
    """
    raw = norm_name(value)
    if not raw:
        return ""

    flag_code, rest = leading_flag_country_code(raw)
    rest = canonical_node_name(rest if flag_code else raw)
    if not rest and flag_code:
        return flag_code

    if flag_code:
        # Avoid duplicating names that already start with the same country code.
        m = re.match(rf"^{re.escape(flag_code)}(?:[\s/_-]+|$)(?P<tail>.*)$", rest, flags=re.IGNORECASE)
        if m:
            tail = canonical_node_name(m.group("tail"))
            return f"{flag_code} / {tail}" if tail else flag_code
        return f"{flag_code} / {rest}" if rest else flag_code

    return rest


def node_key(value: Any) -> str:
    return canonical_node_name(value).casefold()


def logical_name_matches(value: Any, logical_name: Any) -> bool:
    return bool(node_key(value)) and node_key(value) == node_key(logical_name)


def socks_node_name(base_name: str) -> str:
    base = canonical_node_name(base_name)
    return f"{base} / Socks" if base else ""


def group_of_name(name: str) -> str:
    up = canonical_node_name(name).upper()
    tokens = [t for t in re.split(r"[^A-Z0-9]+", up) if t]
    for code in COUNTRY_GROUPS[:-1]:
        if code in tokens:
            return code
    return "Intl"


def parse_port_from_url(url: str) -> Optional[int]:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.port
    except Exception:
        return None


def parse_host_from_url(url: str) -> Optional[str]:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.hostname
    except Exception:
        return None


def make_socks_url(port: int, host: str = LOCAL_LISTEN) -> str:
    host = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
    return f"socks5h://{host}:{int(port)}"


def find_entry_by_name(items: List[Any], name: str) -> Optional[Dict[str, Any]]:
    for item in items:
        d = as_dict(item)
        if norm_name(d.get("name")) == name:
            return d
    return None


def find_entries_by_logical_name(items: List[Any], name: str) -> List[Dict[str, Any]]:
    target = node_key(name)
    if not target:
        return []
    return [as_dict(item) for item in items if logical_name_matches(as_dict(item).get("name"), target)]


def prefer_logical_entry(items: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    if not items:
        return None
    base = canonical_node_name(name)
    # Prefer the real outbound/proxy-style name without " / Socks".
    for item in items:
        if norm_name(item.get("name")) == base:
            return item
    # Then prefer any entry that has useful SOCKS information.
    for item in items:
        if item.get("socks"):
            return item
    return items[0]


def find_entry_by_logical_name(items: List[Any], name: str) -> Optional[Dict[str, Any]]:
    return prefer_logical_entry(find_entries_by_logical_name(items, name), name)


def find_proxy(mihomo: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    return find_entry_by_logical_name(mihomo.get("proxies") or [], name)


def find_ew_node(ew: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    return find_entry_by_logical_name(ew.get("nodes") or [], name)


def listener_matches(listener: Dict[str, Any], name: str, port: Optional[int] = None) -> bool:
    lname = norm_name(listener.get("name"))
    proxy_name = norm_name(listener.get("proxy"))
    if logical_name_matches(proxy_name, name) or logical_name_matches(lname, name):
        return True
    if port is not None:
        try:
            return int(listener.get("port")) == int(port)
        except Exception:
            return False
    return False


def find_listener(mihomo: Dict[str, Any], name: str, port: Optional[int] = None) -> Optional[Dict[str, Any]]:
    for item in mihomo.get("listeners") or []:
        d = as_dict(item)
        if listener_matches(d, name, port):
            return d
    return None


def listener_socks_url(listener: Optional[Dict[str, Any]]) -> Optional[str]:
    if not listener:
        return None
    try:
        port = int(listener.get("port"))
    except Exception:
        return None
    listen = norm_name(listener.get("listen")) or LOCAL_LISTEN
    if listen in ("0.0.0.0", "::"):
        listen = "127.0.0.1"
    return make_socks_url(port, listen)


def compatibility_nodes_look_like_egress(nodes: Any) -> bool:
    if not isinstance(nodes, list):
        return False
    if not nodes:
        return True
    hit = 0
    for n in nodes:
        d = as_dict(n)
        if "name" in d and "socks" in d:
            hit += 1
    return hit == len(nodes)


def sync_mihomo_compat_nodes(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> None:
    """Keep an existing EgressWatch-like top-level nodes list synchronized.

    Real Mihomo uses proxies/listeners. Some earlier configs also kept a
    compatibility top-level nodes list. Normal add/edit/delete operations keep
    that list aligned with EgressWatch nodes. Subscription sync can provide an
    override so /etc/mihomo/config.yaml keeps SOCKS entries for every Mihomo
    subscription node while /root/projects/EgressWatch/config.yaml only keeps
    the EgressWatch subscription subset.
    """
    override = mihomo.pop("__egressctl_compat_nodes_override", None)
    if "nodes" not in mihomo or not compatibility_nodes_look_like_egress(mihomo.get("nodes")):
        return
    if isinstance(override, list):
        mihomo["nodes"] = copy.deepcopy(override)
    else:
        mihomo["nodes"] = copy.deepcopy(ensure_list(ew, "nodes"))


def collect_node_views(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}

    def add_name(n: Any) -> None:
        base = canonical_node_name(n)
        if not base:
            return
        key = node_key(base)
        if key not in buckets:
            buckets[key] = {"name": base, "aliases": []}
        raw = norm_name(n)
        if raw and raw not in buckets[key]["aliases"]:
            buckets[key]["aliases"].append(raw)

    for item in ew.get("nodes") or []:
        add_name(as_dict(item).get("name"))
    for item in mihomo.get("proxies") or []:
        add_name(as_dict(item).get("name"))
    for item in mihomo.get("listeners") or []:
        d = as_dict(item)
        add_name(d.get("proxy"))
        add_name(d.get("name"))
    if compatibility_nodes_look_like_egress(mihomo.get("nodes")):
        for item in mihomo.get("nodes") or []:
            add_name(as_dict(item).get("name"))

    views: List[Dict[str, Any]] = []
    for bucket in buckets.values():
        name = bucket["name"]
        ew_nodes = find_entries_by_logical_name(ew.get("nodes") or [], name)
        ew_node = prefer_logical_entry(ew_nodes, name)
        ew_socks = ""
        for candidate in ew_nodes:
            ew_socks = norm_name(candidate.get("socks"))
            if ew_socks:
                break
        port = parse_port_from_url(ew_socks) if ew_socks else None
        proxy = find_proxy(mihomo, name)
        listener = find_listener(mihomo, name, port)
        socks = ew_socks or listener_socks_url(listener) or ""
        if port is None and socks:
            port = parse_port_from_url(socks)
        if port is None and listener and listener.get("port"):
            try:
                port = int(listener.get("port"))
            except Exception:
                port = None
        views.append(
            {
                "name": name,
                "aliases": bucket.get("aliases", []),
                "group": group_of_name(name),
                "socks": socks,
                "port": port,
                "proxy": proxy,
                "listener": listener,
                "ew_node": ew_node,
            }
        )
    return views

def group_views(views: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped = {g: [] for g in COUNTRY_GROUPS}
    for view in views:
        grouped.setdefault(view["group"], []).append(view)
    return grouped


def print_groups(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    grouped = group_views(collect_node_views(mihomo, ew))
    print("\n节点分组：")
    for gi, group in enumerate(COUNTRY_GROUPS, start=1):
        nodes = grouped.get(group, [])
        print(f"[{gi}] {group} ({len(nodes)})")
        for ni, node in enumerate(nodes, start=1):
            ptype = as_dict(node.get("proxy")).get("type") or "no-proxy"
            print(f"    {ni}. {node['name']}  [{ptype}]")
    print("")
    return grouped

def read_choice(prompt: str, low: int, high: int, allow_q: bool = True) -> Optional[int]:
    while True:
        raw = input(prompt).strip()
        if allow_q and raw.lower() in {"q", "quit", "exit", "返回"}:
            return None
        if raw.isdigit():
            val = int(raw)
            if low <= val <= high:
                return val
        print(f"请输入 {low}-{high} 的数字" + ("，或 q 返回。" if allow_q else "。"))


def read_choice_default(prompt: str, low: int, high: int, default: int, allow_q: bool = True) -> Optional[int]:
    if not (low <= default <= high):
        raise ValueError("默认值不在可选范围内。")
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        if allow_q and raw.lower() in {"q", "quit", "exit", "返回"}:
            return None
        if raw.isdigit():
            val = int(raw)
            if low <= val <= high:
                return val
        print(f"请输入 {low}-{high} 的数字" + ("，或 q 返回；直接回车使用默认值。" if allow_q else "；直接回车使用默认值。"))


def node_from_group_selection(grouped: Dict[str, List[Dict[str, Any]]], group_index: int, node_index: int) -> Optional[Dict[str, Any]]:
    if not (1 <= group_index <= len(COUNTRY_GROUPS)):
        print(f"分组号请输入 1-{len(COUNTRY_GROUPS)}。")
        return None

    group = COUNTRY_GROUPS[group_index - 1]
    nodes = grouped.get(group, [])
    if not nodes:
        print("该分组没有节点。")
        return None

    if not (1 <= node_index <= len(nodes)):
        print(f"{group} 分组节点号请输入 1-{len(nodes)}。")
        return None

    return nodes[node_index - 1]


def choose_node(
    mihomo: Dict[str, Any],
    ew: Dict[str, Any],
    allow_quick_pair: bool = False,
    quick_pair: Optional[Tuple[int, int]] = None,
) -> Optional[Dict[str, Any]]:
    grouped = print_groups(mihomo, ew)

    if quick_pair is not None:
        return node_from_group_selection(grouped, quick_pair[0], quick_pair[1])

    while True:
        if allow_quick_pair:
            raw = input("选择分组序号，或输入 分组号 节点号 直接选择：").strip()
        else:
            raw = input("选择分组序号：").strip()

        if raw.lower() in {"q", "quit", "exit", "返回"}:
            return None

        if allow_quick_pair:
            parts = raw.split()
            if len(parts) == 2 and all(part.isdigit() for part in parts):
                node = node_from_group_selection(grouped, int(parts[0]), int(parts[1]))
                if node is not None:
                    return node
                continue

        if raw.isdigit():
            gi = int(raw)
            if 1 <= gi <= len(COUNTRY_GROUPS):
                break
        print(f"请输入 1-{len(COUNTRY_GROUPS)} 的数字" + ("，或输入类似 6 2 的分组号+节点号，或 q 返回。" if allow_quick_pair else "，或 q 返回。"))

    group = COUNTRY_GROUPS[gi - 1]
    nodes = grouped.get(group, [])
    if not nodes:
        print("该分组没有节点。")
        return None
    ni = read_choice("选择节点序号：", 1, len(nodes))
    if ni is None:
        return None
    return nodes[ni - 1]


def b64decode_text(value: str) -> str:
    s = value.strip()
    s += "=" * ((4 - len(s) % 4) % 4)
    raw = base64.urlsafe_b64decode(s.encode("utf-8"))
    return raw.decode("utf-8")


def parse_host_port(hostport: str) -> Tuple[str, int]:
    parsed = urllib.parse.urlparse("//" + hostport)
    if not parsed.hostname or parsed.port is None:
        raise ValueError(f"无法解析 host:port：{hostport}")
    return parsed.hostname, int(parsed.port)


def parse_plugin_opts(plugin_raw: str) -> Tuple[str, Dict[str, Any]]:
    plugin_raw = urllib.parse.unquote(plugin_raw)
    parts = [p for p in plugin_raw.split(";") if p]
    if not parts:
        return "", {}
    plugin_name = parts[0].strip()
    opts: Dict[str, Any] = {}
    for part in parts[1:]:
        if "=" in part:
            k, v = part.split("=", 1)
            opts[k.strip()] = urllib.parse.unquote(v.strip())
        else:
            opts[part.strip()] = True

    lower = plugin_name.lower()
    if lower in {"obfs", "obfs-local", "simple-obfs"}:
        out: Dict[str, Any] = {}
        mode = opts.get("obfs") or opts.get("mode")
        host = opts.get("obfs-host") or opts.get("host")
        if mode:
            out["mode"] = mode
        if host:
            out["host"] = host
        return "obfs", out

    if "v2ray" in lower:
        out = {"mode": opts.get("mode", "websocket")}
        if opts.get("host"):
            out["host"] = opts["host"]
        if opts.get("path"):
            out["path"] = opts["path"]
        if str(opts.get("tls", "")).lower() in {"1", "true", "tls"}:
            out["tls"] = True
        if opts.get("mux"):
            out["mux"] = str(opts["mux"]).lower() in {"1", "true", "yes"}
        return "v2ray-plugin", out

    return plugin_name, opts


def parse_ss_uri(uri: str) -> Dict[str, Any]:
    raw = uri.strip()
    if not raw.lower().startswith("ss://"):
        raise ValueError("不是 ss:// 链接")

    parsed = urllib.parse.urlparse(raw)
    name = urllib.parse.unquote(parsed.fragment or "")

    body = raw[5:]
    body_no_frag = body.split("#", 1)[0]
    main, _, query = body_no_frag.partition("?")

    method: str
    password: str
    server: str
    port: int

    if "@" in main:
        userinfo, hostport = main.rsplit("@", 1)
        userinfo = urllib.parse.unquote(userinfo)
        if ":" not in userinfo:
            userinfo = b64decode_text(userinfo)
        method, password = userinfo.split(":", 1)
        server, port = parse_host_port(hostport)
    else:
        decoded = b64decode_text(urllib.parse.unquote(main))
        userinfo, hostport = decoded.rsplit("@", 1)
        method, password = userinfo.split(":", 1)
        server, port = parse_host_port(hostport)

    proxy: Dict[str, Any] = {
        "name": name or f"{server}:{port}",
        "type": "ss",
        "server": server,
        "port": int(port),
        "cipher": urllib.parse.unquote(method),
        "password": urllib.parse.unquote(password),
        "udp": True,
    }

    qs = urllib.parse.parse_qs(query, keep_blank_values=True)
    if qs.get("plugin"):
        plugin, plugin_opts = parse_plugin_opts(qs["plugin"][0])
        if plugin:
            proxy["plugin"] = plugin
        if plugin_opts:
            proxy["plugin-opts"] = plugin_opts

    return proxy


def parse_socks_uri(uri: str) -> Dict[str, Any]:
    parsed = urllib.parse.urlparse(uri.strip())
    if parsed.scheme.lower() not in {"socks", "socks5", "socks5h"}:
        raise ValueError("不是 socks/socks5/socks5h 链接")
    if not parsed.hostname or parsed.port is None:
        raise ValueError("SOCKS 链接缺少 host 或 port")
    name = urllib.parse.unquote(parsed.fragment or "") or f"{parsed.hostname}:{parsed.port}"
    proxy: Dict[str, Any] = {
        "name": name,
        "type": "socks5",
        "server": parsed.hostname,
        "port": int(parsed.port),
        "udp": True,
    }
    if parsed.username:
        proxy["username"] = urllib.parse.unquote(parsed.username)
    if parsed.password:
        proxy["password"] = urllib.parse.unquote(parsed.password)
    return proxy


def parse_share_link(uri: str) -> Dict[str, Any]:
    scheme = urllib.parse.urlparse(uri.strip()).scheme.lower()
    if scheme == "ss":
        return parse_ss_uri(uri)
    if scheme in {"socks", "socks5", "socks5h"}:
        return parse_socks_uri(uri)
    raise ValueError(f"暂不支持该链接协议：{scheme or 'unknown'}；本脚本内置 ss:// 与 socks/socks5://。")


def ask(prompt: str, default: Optional[str] = None, required: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default not in (None, "") else ""
        value = input(f"{prompt}{suffix}: ").strip()
        if not value and default is not None:
            value = default
        if value or not required:
            return value
        print("该项不能为空。")


def ask_int(prompt: str, default: Optional[int] = None, low: int = 1, high: int = 65535) -> int:
    while True:
        raw = ask(prompt, str(default) if default is not None else None, required=True)
        try:
            val = int(raw)
            if low <= val <= high:
                return val
        except Exception:
            pass
        print(f"请输入 {low}-{high} 之间的整数。")


def ask_bool(prompt: str, default: bool = True) -> bool:
    mark = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} [{mark}]: ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes", "1", "true", "是"}:
            return True
        if raw in {"n", "no", "0", "false", "否"}:
            return False
        print("请输入 y 或 n。")


def manual_proxy() -> Dict[str, Any]:
    print("\n手动新增协议：")
    print("1. Shadowsocks")
    print("2. SOCKS5")
    choice = read_choice("选择协议：", 1, 2, allow_q=False)
    assert choice is not None
    if choice == 1:
        name = ask("节点 name", required=True)
        server = ask("server", required=True)
        port = ask_int("port")
        cipher = ask("cipher/method", "aes-128-gcm", required=True)
        password = ask("password", required=True)
        udp = ask_bool("udp", True)
        return {
            "name": name,
            "type": "ss",
            "server": server,
            "port": port,
            "cipher": cipher,
            "password": password,
            "udp": udp,
        }

    name = ask("节点 name", required=True)
    server = ask("server", required=True)
    port = ask_int("port")
    username = ask("username，留空表示无认证")
    password = ask("password，留空表示无认证") if username else ""
    tls = ask_bool("tls", False)
    udp = ask_bool("udp", True)
    proxy = {
        "name": name,
        "type": "socks5",
        "server": server,
        "port": port,
        "udp": udp,
    }
    if username:
        proxy["username"] = username
    if password:
        proxy["password"] = password
    if tls:
        proxy["tls"] = True
    return proxy


def used_local_ports(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> set[int]:
    ports: set[int] = set()
    for key in ["port", "socks-port", "mixed-port", "redir-port", "tproxy-port"]:
        try:
            if mihomo.get(key) is not None:
                ports.add(int(mihomo[key]))
        except Exception:
            pass
    for item in mihomo.get("listeners") or []:
        d = as_dict(item)
        try:
            ports.add(int(d.get("port")))
        except Exception:
            pass
    for item in ew.get("nodes") or []:
        d = as_dict(item)
        p = parse_port_from_url(norm_name(d.get("socks")))
        if p:
            ports.add(p)
    if compatibility_nodes_look_like_egress(mihomo.get("nodes")):
        for item in mihomo.get("nodes") or []:
            d = as_dict(item)
            p = parse_port_from_url(norm_name(d.get("socks")))
            if p:
                ports.add(p)
    return ports


def can_bind_local(port: int) -> bool:
    for family, host in [(socket.AF_INET, "127.0.0.1")]:
        s = socket.socket(family, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, int(port)))
            return True
        except OSError:
            return False
        finally:
            s.close()
    return False


def choose_free_port(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> int:
    used = used_local_ports(mihomo, ew)
    candidates = list(range(PORT_MIN, PORT_MAX + 1))
    random.shuffle(candidates)
    for port in candidates:
        if port not in used and can_bind_local(port):
            return port
    raise RuntimeError(f"{PORT_MIN}-{PORT_MAX} 范围内没有可用端口；可用 EW_PORT_MIN/EW_PORT_MAX 调整范围。")


def remove_named_items(mihomo: Dict[str, Any], ew: Dict[str, Any], name: str, port: Optional[int] = None) -> None:
    base = canonical_node_name(name)

    if isinstance(mihomo.get("proxies"), list):
        mihomo["proxies"] = [
            p for p in mihomo["proxies"]
            if not logical_name_matches(as_dict(p).get("name"), base)
        ]

    if isinstance(mihomo.get("listeners"), list):
        mihomo["listeners"] = [
            l for l in mihomo["listeners"]
            if not listener_matches(as_dict(l), base, port)
        ]

    if compatibility_nodes_look_like_egress(mihomo.get("nodes")):
        mihomo["nodes"] = [
            n for n in mihomo.get("nodes") or []
            if not logical_name_matches(as_dict(n).get("name"), base)
        ]

    if isinstance(ew.get("nodes"), list):
        ew["nodes"] = [
            n for n in ew["nodes"]
            if not logical_name_matches(as_dict(n).get("name"), base)
        ]

    for group in mihomo.get("proxy-groups") or []:
        gd = as_dict(group)
        proxies = gd.get("proxies")
        if isinstance(proxies, list):
            seen: set[str] = set()
            cleaned: List[Any] = []
            for p in proxies:
                if logical_name_matches(p, base):
                    continue
                k = str(p)
                if k not in seen:
                    seen.add(k)
                    cleaned.append(p)
            gd["proxies"] = cleaned

def rename_references(mihomo: Dict[str, Any], old_name: str, new_name: str) -> None:
    old_base = canonical_node_name(old_name)
    new_base = canonical_node_name(new_name)
    if node_key(old_base) == node_key(new_base):
        return

    for group in mihomo.get("proxy-groups") or []:
        gd = as_dict(group)
        proxies = gd.get("proxies")
        if isinstance(proxies, list):
            seen: set[str] = set()
            updated: List[Any] = []
            for p in proxies:
                value = new_base if logical_name_matches(p, old_base) else p
                key = str(value)
                if key not in seen:
                    seen.add(key)
                    updated.append(value)
            gd["proxies"] = updated

    for listener in mihomo.get("listeners") or []:
        ld = as_dict(listener)
        if logical_name_matches(ld.get("proxy"), old_base):
            ld["proxy"] = new_base
        if logical_name_matches(ld.get("name"), old_base):
            ld["name"] = socks_node_name(new_base)

def upsert_proxy(mihomo: Dict[str, Any], old_name: Optional[str], proxy: Dict[str, Any]) -> None:
    proxies = ensure_list(mihomo, "proxies")
    target_name = canonical_node_name(proxy.get("name"))
    proxy["name"] = target_name

    existing = None
    if old_name:
        existing = find_entry_by_logical_name(proxies, old_name)
    if existing is None:
        existing = find_entry_by_logical_name(proxies, target_name)

    if existing is None:
        proxies.append(proxy)
        existing = proxy
    else:
        existing.clear()
        existing.update(proxy)

    # Collapse duplicate outbound entries that only differ by the legacy " / Socks" suffix.
    proxies[:] = [
        p for p in proxies
        if p is existing or not logical_name_matches(as_dict(p).get("name"), target_name)
    ]


def upsert_listener(mihomo: Dict[str, Any], old_name: Optional[str], new_name: str, port: int) -> None:
    listeners = ensure_list(mihomo, "listeners")
    new_base = canonical_node_name(new_name)
    existing = None
    if old_name:
        existing = find_listener(mihomo, old_name, port)
    if existing is None:
        existing = find_listener(mihomo, new_base, port)
    if existing is None:
        existing = {}
        listeners.append(existing)
    existing.clear()
    existing.update(
        {
            "name": socks_node_name(new_base),
            "type": "socks",
            "listen": LOCAL_LISTEN,
            "port": int(port),
            "udp": True,
            "users": [],
            "proxy": new_base,
        }
    )

    listeners[:] = [
        l for l in listeners
        if l is existing or not listener_matches(as_dict(l), new_base, port)
    ]


def upsert_egress_node(ew: Dict[str, Any], old_name: Optional[str], new_name: str, socks_url: str) -> None:
    nodes = ensure_list(ew, "nodes")
    new_base = canonical_node_name(new_name)
    stored_name = socks_node_name(new_base)

    existing = None
    if old_name:
        existing = find_entry_by_logical_name(nodes, old_name)
    if existing is None:
        existing = find_entry_by_logical_name(nodes, new_base)

    if existing is None:
        existing = {"name": stored_name, "socks": socks_url}
        nodes.append(existing)
    else:
        existing["name"] = stored_name
        existing["socks"] = socks_url

    # Keep only one EgressWatch node per logical node.
    nodes[:] = [
        n for n in nodes
        if n is existing or not logical_name_matches(as_dict(n).get("name"), new_base)
    ]

def rebuild_managed_proxy_groups(mihomo: Dict[str, Any]) -> None:
    proxies = ensure_list(mihomo, "proxies")
    names_by_group = {g: [] for g in COUNTRY_GROUPS}
    for proxy in proxies:
        name = canonical_node_name(as_dict(proxy).get("name"))
        if not name:
            continue
        if name not in names_by_group[group_of_name(name)]:
            names_by_group[group_of_name(name)].append(name)

    groups = ensure_list(mihomo, "proxy-groups")
    existing_by_name: Dict[str, Dict[str, Any]] = {}
    for group in groups:
        gd = as_dict(group)
        gname = norm_name(gd.get("name"))
        if gname in MANAGED_GROUPS:
            existing_by_name[gname] = gd

    # Remove empty managed groups from config to avoid invalid/meaningless empty groups.
    groups[:] = [
        g
        for g in groups
        if not (norm_name(as_dict(g).get("name")) in MANAGED_GROUPS and not names_by_group.get(norm_name(as_dict(g).get("name"))))
    ]

    for gname in COUNTRY_GROUPS:
        names = names_by_group[gname]
        if not names:
            continue
        group = existing_by_name.get(gname)
        if group is None or group not in groups:
            group = {"name": gname, "type": "select", "proxies": names}
            groups.append(group)
        else:
            group["type"] = group.get("type") or "select"
            group["proxies"] = names


def mihomo_binary() -> Optional[str]:
    for name in ["mihomo", "clash-meta", "clash"]:
        path = shutil.which(name)
        if path:
            return path
    return None


def test_mihomo_config(path: Path) -> bool:
    if os.environ.get("EW_SKIP_TEST") == "1":
        print("已跳过 Mihomo 配置测试：EW_SKIP_TEST=1")
        return True
    binary = mihomo_binary()
    if not binary:
        print("未找到 mihomo/clash-meta/clash 可执行文件，跳过配置测试。")
        return True
    proc = subprocess.run([binary, "-t", "-f", str(path)], text=True, capture_output=True)
    if proc.returncode == 0:
        print("Mihomo 配置测试通过。")
        return True
    print("Mihomo 配置测试失败：", file=sys.stderr)
    if proc.stdout:
        print(proc.stdout, file=sys.stderr)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return False


def reload_mihomo() -> None:
    if os.environ.get("EW_SKIP_RELOAD") == "1":
        print("已跳过重载：EW_SKIP_RELOAD=1")
        return
    systemctl = shutil.which("systemctl")
    if not systemctl:
        print("未找到 systemctl，请手动重载/重启 Mihomo。")
        return

    for action in ["reload", "restart"]:
        proc = subprocess.run([systemctl, action, MIHOMO_SERVICE], text=True, capture_output=True)
        if proc.returncode == 0:
            print(f"已执行：systemctl {action} {MIHOMO_SERVICE}")
            return
        if action == "reload":
            print("systemctl reload 失败，尝试 restart。")
        else:
            print(f"systemctl restart {MIHOMO_SERVICE} 失败。", file=sys.stderr)
            if proc.stdout:
                print(proc.stdout, file=sys.stderr)
            if proc.stderr:
                print(proc.stderr, file=sys.stderr)


def save_validate_reload(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> bool:
    sync_mihomo_compat_nodes(mihomo, ew)
    rebuild_managed_proxy_groups(mihomo)
    backups = make_backups([MIHOMO_CONFIG, EGRESSWATCH_CONFIG])
    try:
        dump_yaml(MIHOMO_CONFIG, mihomo)
        dump_yaml(EGRESSWATCH_CONFIG, ew)
        if not test_mihomo_config(MIHOMO_CONFIG):
            restore_backups(backups)
            return False
        reload_mihomo()
        cleanup_old_backups([MIHOMO_CONFIG, EGRESSWATCH_CONFIG])
        return True
    except Exception as exc:
        print(f"保存失败：{exc}", file=sys.stderr)
        restore_backups(backups)
        return False


def action_add(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> None:
    print("\n新增节点：")
    print("1. 粘贴 ss:// 或 socks5:// 通用链接")
    print("2. 手动输入参数")
    choice = read_choice("选择方式：", 1, 2, allow_q=True)
    if choice is None:
        return
    if choice == 1:
        uri = ask("粘贴链接", required=True)
        try:
            proxy = parse_share_link(uri)
        except Exception as exc:
            print(f"解析失败：{exc}")
            return
        default_name = norm_name(proxy.get("name"))
        name = ask("节点 name", default_name or None, required=True)
        name = canonical_node_name(name)
        proxy["name"] = name
    else:
        proxy = manual_proxy()
        name = canonical_node_name(proxy["name"])
        proxy["name"] = name

    if find_ew_node(ew, name) or find_proxy(mihomo, name):
        if not ask_bool(f"节点 {name} 已存在，是否覆盖", False):
            return
        old_port = None
        old = find_ew_node(ew, name)
        if old:
            old_port = parse_port_from_url(norm_name(old.get("socks")))
        remove_named_items(mihomo, ew, name, old_port)

    port = choose_free_port(mihomo, ew)
    socks_url = make_socks_url(port)
    upsert_proxy(mihomo, None, proxy)
    upsert_listener(mihomo, None, name, port)
    upsert_egress_node(ew, None, name, socks_url)
    if save_validate_reload(mihomo, ew):
        print(f"新增完成：{name} -> {socks_url}，分组：{group_of_name(name)}")


def bool_default(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y", "on", "是"}:
        return True
    if s in {"0", "false", "no", "n", "off", "否"}:
        return False
    return default


def ask_optional_clear(prompt: str, current: Any = None) -> str:
    current_s = norm_name(current)
    value = ask(f"{prompt}（输入 - 清空）", current_s if current_s else None, required=False)
    if value.strip() == "-":
        return ""
    return value


def editable_port_default(proxy: Optional[Dict[str, Any]]) -> Optional[int]:
    if not proxy:
        return None
    try:
        return int(proxy.get("port"))
    except Exception:
        return None


def edit_proxy_params(existing_proxy: Optional[Dict[str, Any]], old_name: str) -> Dict[str, Any]:
    """Interactively edit an existing Mihomo outbound proxy.

    Extra fields that are not prompted are preserved, so plugin/plugin-opts and
    other Mihomo-specific options are not lost when editing common parameters.
    """
    if existing_proxy is None:
        print("未找到 Mihomo 出站配置，请手动输入节点参数。")
        proxy = manual_proxy()
        proxy["name"] = canonical_node_name(proxy.get("name") or old_name)
        return proxy

    proxy = copy.deepcopy(existing_proxy)
    ptype = norm_name(proxy.get("type")).lower()
    print(f"\n当前出站协议：{ptype or 'unknown'}")

    if ptype in {"ss", "shadowsocks"}:
        proxy["name"] = canonical_node_name(ask("节点 name", old_name, required=True))
        proxy["type"] = "ss"
        proxy["server"] = ask("server", norm_name(proxy.get("server")) or None, required=True)
        proxy["port"] = ask_int("port", editable_port_default(proxy), low=1, high=65535)
        proxy["cipher"] = ask("cipher/method", norm_name(proxy.get("cipher")) or "aes-128-gcm", required=True)
        proxy["password"] = ask("password", str(proxy.get("password")) if proxy.get("password") is not None else None, required=True)
        proxy["udp"] = ask_bool("udp", bool_default(proxy.get("udp"), True))
        return proxy

    if ptype in {"socks", "socks5"}:
        proxy["name"] = canonical_node_name(ask("节点 name", old_name, required=True))
        proxy["type"] = "socks5"
        proxy["server"] = ask("server", norm_name(proxy.get("server")) or None, required=True)
        proxy["port"] = ask_int("port", editable_port_default(proxy), low=1, high=65535)
        username = ask_optional_clear("username", proxy.get("username"))
        password = ask_optional_clear("password", proxy.get("password")) if username else ""
        if username:
            proxy["username"] = username
        else:
            proxy.pop("username", None)
        if password:
            proxy["password"] = password
        else:
            proxy.pop("password", None)
        tls = ask_bool("tls", bool_default(proxy.get("tls"), False))
        if tls:
            proxy["tls"] = True
        else:
            proxy.pop("tls", None)
        proxy["udp"] = ask_bool("udp", bool_default(proxy.get("udp"), True))
        return proxy

    print("该协议暂不支持逐项编辑，将保留原有协议字段，只允许修改通用字段。")
    proxy["name"] = canonical_node_name(ask("节点 name", old_name, required=True))
    if "server" in proxy:
        proxy["server"] = ask("server", norm_name(proxy.get("server")) or None, required=True)
    if "port" in proxy:
        proxy["port"] = ask_int("port", editable_port_default(proxy), low=1, high=65535)
    if "udp" in proxy:
        proxy["udp"] = ask_bool("udp", bool_default(proxy.get("udp"), True))
    return proxy


def action_edit(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> None:
    node = choose_node(mihomo, ew)
    if not node:
        return
    old_name = canonical_node_name(node["name"])
    old_port = node.get("port")
    had_listener = node.get("listener") is not None
    old_proxy = copy.deepcopy(find_proxy(mihomo, old_name))

    print(f"\n编辑节点：{old_name}")
    print("1. 输入新链接（ss:// 或 socks5://）")
    print("2. 修改节点参数")
    edit_mode = read_choice("选择编辑方式：", 1, 2, allow_q=True)
    if edit_mode is None:
        return

    new_proxy: Optional[Dict[str, Any]] = None

    if edit_mode == 1:
        uri = ask("新链接", required=True)
        try:
            new_proxy = parse_share_link(uri)
            parsed_name = canonical_node_name(new_proxy.get("name"))
            if parsed_name:
                print(f"链接内 name：{parsed_name}")
        except Exception as exc:
            print(f"解析失败：{exc}")
            return

        default_name = canonical_node_name(new_proxy.get("name")) or old_name
        new_name = canonical_node_name(ask("节点 name", default_name, required=True))
        if not new_name:
            print("节点 name 不能为空。")
            return
        new_proxy["name"] = new_name
    else:
        new_proxy = edit_proxy_params(old_proxy, old_name)
        new_name = canonical_node_name(new_proxy.get("name") or old_name)
        if not new_name:
            print("节点 name 不能为空。")
            return
        new_proxy["name"] = new_name

    port = int(old_port) if old_port else choose_free_port(mihomo, ew)
    socks_url = make_socks_url(port)

    if node_key(new_name) != node_key(old_name) and (find_ew_node(ew, new_name) or find_proxy(mihomo, new_name)):
        if not ask_bool(f"目标名称 {new_name} 已存在，是否覆盖", False):
            return
        target = find_ew_node(ew, new_name)
        target_port = parse_port_from_url(norm_name(target.get("socks"))) if target else None
        remove_named_items(mihomo, ew, new_name, target_port)

    if new_proxy is not None:
        upsert_proxy(mihomo, old_name, new_proxy)

    rename_references(mihomo, old_name, new_name)

    if new_proxy is not None or had_listener:
        upsert_listener(mihomo, old_name, new_name, port)
    upsert_egress_node(ew, old_name, new_name, socks_url)

    if save_validate_reload(mihomo, ew):
        print(f"编辑完成：{old_name} -> {new_name}，socks：{socks_url}，分组：{group_of_name(new_name)}")

def action_delete(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> None:
    node = choose_node(mihomo, ew)
    if not node:
        return
    name = canonical_node_name(node["name"])
    port = node.get("port")
    related = [name, socks_node_name(name)]
    print("将同步删除以下逻辑关联项：")
    for item in related:
        print(f"  - {item}")
    if not ask_bool(f"确认删除 {name}", False):
        return
    remove_named_items(mihomo, ew, name, int(port) if port else None)
    if save_validate_reload(mihomo, ew):
        print(f"已删除：{name}")


def action_sync_groups(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> None:
    print_groups(mihomo, ew)
    if not ask_bool("确认根据当前 proxies 重建 Mihomo HK/JP/SG/TW/KR/US/Intl 策略组", True):
        return
    if save_validate_reload(mihomo, ew):
        print("分组同步完成。")


def proxy_for_ip_check(node: Dict[str, Any]) -> Optional[str]:
    socks = norm_name(node.get("socks"))
    if socks:
        return socks
    listener = as_dict(node.get("listener"))
    return listener_socks_url(listener)


def action_ip_check(mihomo: Dict[str, Any], ew: Dict[str, Any], quick_pair: Optional[Tuple[int, int]] = None) -> None:
    node = choose_node(mihomo, ew, allow_quick_pair=True, quick_pair=quick_pair)
    if not node:
        return
    proxy = proxy_for_ip_check(node)
    if not proxy:
        print("该节点没有可用 socks 入站，无法执行检测。")
        return
    print(f"\n将执行等价命令：bash <(curl -Ls https://IP.Check.Place) -x {proxy}")
    if not ask_bool("确认执行远程检测脚本", True):
        return

    curl = subprocess.Popen(["curl", "-fsSL", "https://IP.Check.Place"], stdout=subprocess.PIPE)
    assert curl.stdout is not None
    bash = subprocess.Popen(["bash", "-s", "--", "-x", proxy], stdin=curl.stdout)
    curl.stdout.close()
    bash_rc = bash.wait()
    curl_rc = curl.wait()
    if curl_rc != 0:
        print(f"curl 下载检测脚本失败，退出码：{curl_rc}", file=sys.stderr)
    if bash_rc != 0:
        print(f"检测脚本执行失败，退出码：{bash_rc}", file=sys.stderr)


def shell_quote(value: Any) -> str:
    """Small POSIX-safe single-quote helper for crontab commands."""
    s = str(value)
    return "'" + s.replace("'", "'\"'\"'") + "'"


def current_crontab_lines() -> List[str]:
    proc = subprocess.run(["crontab", "-l"], text=True, capture_output=True)
    if proc.returncode == 0:
        return proc.stdout.splitlines()
    # crontab -l returns 1 when the current user has no crontab.
    combined = f"{proc.stdout}\n{proc.stderr}".lower()
    if "no crontab" in combined or "no crontab for" in combined:
        return []
    raise RuntimeError((proc.stderr or proc.stdout or "读取 crontab 失败").strip())


def install_crontab_lines(lines: List[str]) -> None:
    content = "\n".join(lines).rstrip() + "\n"
    proc = subprocess.run(["crontab", "-"], input=content, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "写入 crontab 失败").strip())


def is_egresswatch_cron_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    if EGRESSWATCH_CRON_MARKER in stripped:
        return True
    return "egress_watch.py" in stripped and "EgressWatch" in stripped


def build_egresswatch_cron_line(interval_minutes: int) -> str:
    if interval_minutes < 1:
        raise ValueError("分钟间隔必须大于等于 1。")

    project_dir = shell_quote(EGRESSWATCH_PROJECT_DIR)
    env_file = shell_quote(EGRESSWATCH_ENV)
    python_bin = shell_quote(EGRESSWATCH_PYTHON)
    script = shell_quote(EGRESSWATCH_SCRIPT)
    log_file = shell_quote(EGRESSWATCH_LOG)

    # Cron has only five fields, so arbitrary intervals such as 90 minutes cannot
    # be represented exactly with a simple "*/N" expression. Running once per
    # minute with an epoch-minute modulo guard gives an exact N-minute interval.
    # Percent signs must be escaped in crontab commands.
    return (
        f"* * * * * "
        f"cd {project_dir} && "
        f"[ $(( $(date +\\%s) / 60 \\% {interval_minutes} )) -eq 0 ] && "
        f". {env_file} && "
        f"{python_bin} {script} >> {log_file} 2>&1 "
        f"# {EGRESSWATCH_CRON_MARKER}; interval={interval_minutes}m"
    )


def describe_current_egresswatch_cron(lines: List[str]) -> None:
    matches = [line for line in lines if is_egresswatch_cron_line(line)]
    if not matches:
        print("当前 crontab 未找到 EgressWatch 定时任务。")
        return
    print("当前 EgressWatch 定时任务：")
    for line in matches:
        print(f"  {line}")


def action_change_cron_interval() -> None:
    print("\n修改定时检测 IP 时间间隔")
    lines = current_crontab_lines()
    describe_current_egresswatch_cron(lines)

    interval = ask_int("输入检测间隔，单位：分钟", 10, low=1, high=43200)
    new_line = build_egresswatch_cron_line(interval)

    kept_lines = [line for line in lines if not is_egresswatch_cron_line(line)]
    kept_lines.append(new_line)

    print("\n将写入当前用户 crontab：")
    print(f"  {new_line}")
    if not ask_bool("确认覆盖原 EgressWatch 定时任务", True):
        return

    install_crontab_lines(kept_lines)
    print(f"已更新：EgressWatch 将每 {interval} 分钟检测一次 IP。")
    print("提示：该操作写入的是当前运行 egressctl 的用户 crontab；用 sudo 运行时就是 root 的 crontab。")


def is_subscription_sync_cron_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped and not stripped.startswith("#") and SUBSCRIPTION_CRON_MARKER in stripped)


def egressctl_command_for_cron() -> str:
    """Return a shell command that can run this script in cron.

    Do not rely on the interactive `egressctl` alias from ~/.zshrc here:
    cron does not load zsh aliases, and process substitution requires bash/zsh.
    """
    configured_command = norm_name(EGRESSCTL_COMMAND)
    if configured_command:
        return configured_command

    configured_exec = norm_name(EGRESSCTL_EXEC)
    if configured_exec:
        return shell_quote(configured_exec)

    # Match the user's interactive alias behavior, but make it cron-safe by
    # having build_subscription_sync_cron_line wrap the command in /bin/bash -lc.
    return f"python3 <(curl --compressed -fsSL {shell_quote(EGRESSCTL_SOURCE_URL)})"


def build_subscription_sync_cron_line(interval_hours: int, mihomo_url: str, egress_url: str) -> str:
    if interval_hours < 1:
        raise ValueError("订阅同步间隔必须大于等于 1 小时。")

    command = egressctl_command_for_cron()
    log_path = shell_quote(EGRESSWATCH_PROJECT_DIR / SUBSCRIPTION_SYNC_LOG)
    mihomo_arg = shell_quote(mihomo_url)
    egress_arg = shell_quote(egress_url)

    # Use an hourly cron entry with an epoch-hour modulo guard so values greater
    # than 23 hours still work exactly. Percent signs must be escaped in crontab.
    #
    # The inner command is executed by bash because the default command uses
    # process substitution: python3 <(curl ...).
    inner_command = (
        f"[ $(( $(date +\\%s) / 3600 \\% {interval_hours} )) -eq 0 ] && "
        f"{command} --sync-subscriptions "
        f"--mihomo-sub-url {mihomo_arg} "
        f"--egress-sub-url {egress_arg} "
        f">> {log_path} 2>&1"
    )
    return (
        f"0 * * * * "
        f"/bin/bash -lc {shell_quote(inner_command)} "
        f"# {SUBSCRIPTION_CRON_MARKER}; interval={interval_hours}h"
    )


def mask_sensitive_line(line: str, *urls: str) -> str:
    masked = line
    for url in urls:
        if url:
            masked = masked.replace(url, mask_url(url))
            masked = masked.replace(shell_quote(url), shell_quote(mask_url(url)))
    return masked


def install_subscription_sync_cron(interval_hours: int, mihomo_url: str, egress_url: str) -> None:
    lines = current_crontab_lines()
    new_line = build_subscription_sync_cron_line(interval_hours, mihomo_url, egress_url)
    kept_lines = [line for line in lines if not is_subscription_sync_cron_line(line)]
    kept_lines.append(new_line)

    install_crontab_lines(kept_lines)
    print(f"已更新订阅同步定时任务：每 {interval_hours} 小时执行一次。")
    print("当前写入当前运行用户的 crontab；用 sudo 运行时就是 root 的 crontab。")
    print("定时任务：")
    print(f"  {mask_sensitive_line(new_line, mihomo_url, egress_url)}")


def load_egressctl_state() -> Dict[str, Any]:
    try:
        data = load_yaml(EGRESSCTL_STATE_FILE)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_egressctl_state(state: Dict[str, Any]) -> None:
    try:
        EGRESSCTL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        dump_yaml(EGRESSCTL_STATE_FILE, state)
        try:
            os.chmod(EGRESSCTL_STATE_FILE, 0o600)
        except Exception:
            pass
    except Exception as exc:
        print(f"警告：保存脚本状态失败（{EGRESSCTL_STATE_FILE}）：{exc}", file=sys.stderr)


def saved_subscription_urls() -> Tuple[str, str]:
    state = load_egressctl_state()
    subs = state.get("subscriptions")
    if not isinstance(subs, dict):
        return "", ""
    return norm_name(subs.get("mihomo_url")), norm_name(subs.get("egresswatch_url"))


def save_subscription_urls(mihomo_url: str, egress_url: str) -> None:
    state = load_egressctl_state()
    subs = state.get("subscriptions")
    if not isinstance(subs, dict):
        subs = {}
    subs["mihomo_url"] = norm_name(mihomo_url)
    subs["egresswatch_url"] = norm_name(egress_url)
    subs["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S %z")
    state["subscriptions"] = subs
    save_egressctl_state(state)
    print(f"已保存本次订阅 URL，后续同步可直接回车复用：{EGRESSCTL_STATE_FILE}")


def ask_subscription_url(label: str, env_default_url: str = "", saved_url: str = "") -> str:
    """Prompt for a subscription URL.

    Pressing Enter prefers the most recently saved URL. If no saved URL exists,
    the environment-provided URL is used as the fallback default.
    """
    env_default_url = norm_name(env_default_url)
    saved_url = norm_name(saved_url)
    while True:
        if saved_url:
            print(f"{label} 最近保存：{mask_url(saved_url)}")
            if env_default_url and env_default_url != saved_url:
                print(f"{label} 环境变量：{mask_url(env_default_url)}（输入 env 使用）")
            value = input(f"{label}，直接回车使用最近保存，或输入新的 URL：").strip()
            if not value:
                value = saved_url
            elif value.lower() == "env" and env_default_url:
                value = env_default_url
        elif env_default_url:
            print(f"{label} 当前环境变量默认：{mask_url(env_default_url)}")
            value = input(f"{label}，直接回车使用上面的默认，或输入新的 URL：").strip()
            value = value or env_default_url
        else:
            value = input(f"{label}（必填）：").strip()

        if not value:
            print("订阅 URL 不能为空。")
            continue

        parsed = urllib.parse.urlparse(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            print("请输入完整的 http:// 或 https:// 订阅 URL。")
            continue

        return value


def human_size(num_bytes: float) -> str:
    value = float(num_bytes)
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    for unit in units:
        if abs(value) < 1024.0 or unit == units[-1]:
            return f"{value:.2f} {unit}" if unit != "B" else f"{value:.0f} {unit}"
        value /= 1024.0
    return f"{value:.2f} TiB"


def human_speed(bytes_per_second: float) -> str:
    mib = float(bytes_per_second) / 1024.0 / 1024.0
    mbps = float(bytes_per_second) * 8.0 / 1000.0 / 1000.0
    return f"{mib:.2f} MiB/s ({mbps:.2f} Mbps)"


def speedtest_stat_from_output(stdout: str, stderr: str, returncode: int, wall_time: float) -> Dict[str, Any]:
    stats: Dict[str, Any] = {
        "ok": False,
        "returncode": returncode,
        "size_download": 0.0,
        "time_total": max(float(wall_time), 0.001),
        "speed_download": 0.0,
        "http_code": "",
        "remote_ip": "",
        "stderr": stderr.strip(),
        "stdout": stdout.strip(),
    }

    m = re.search(
        r"__EWSTATS__\s+size=(?P<size>[0-9.]+)\s+time=(?P<time>[0-9.]+)\s+speed=(?P<speed>[0-9.]+)\s+code=(?P<code>[0-9]{3})\s+ip=(?P<ip>\S*)",
        stdout,
    )
    if m:
        stats["size_download"] = float(m.group("size") or 0)
        stats["time_total"] = max(float(m.group("time") or 0), 0.001)
        stats["speed_download"] = float(m.group("speed") or 0)
        stats["http_code"] = m.group("code") or ""
        stats["remote_ip"] = m.group("ip") or ""

    # curl 28 is expected when --max-time stops an in-progress large download.
    # Treat it as successful if bytes were actually downloaded.
    stats["ok"] = returncode == 0 or (returncode == 28 and stats["size_download"] > 0)
    return stats


def build_speedtest_curl_args(url: str, proxy: str, duration: int, worker_index: int) -> List[str]:
    args = [
        "curl",
        "-L",
        "--silent",
        "--proxy",
        proxy,
        "--connect-timeout",
        str(SPEEDTEST_CONNECT_TIMEOUT),
        "--max-time",
        str(duration),
        "-o",
        "/dev/null",
        "-w",
        "__EWSTATS__ size=%{size_download} time=%{time_total} speed=%{speed_download} code=%{http_code} ip=%{remote_ip}\n",
    ]

    # In multi-thread mode, request different byte ranges so the workers do not
    # all start from exactly the same offset. Large Apple restore images are big
    # enough for these offsets; if the server ignores Range, curl still downloads normally.
    if worker_index > 0:
        start = worker_index * 512 * 1024 * 1024
        args.extend(["--range", f"{start}-"])

    args.append(url)
    return args


def run_apple_cdn_speedtest(proxy: str, workers: int, duration: int, url: str) -> List[Dict[str, Any]]:
    if not shutil.which("curl"):
        raise RuntimeError("未找到 curl，无法测速。请先安装 curl。")
    if workers < 1:
        raise ValueError("线程数必须大于等于 1。")

    processes: List[Tuple[int, float, subprocess.Popen[str]]] = []
    for index in range(workers):
        args = build_speedtest_curl_args(url, proxy, duration, index)
        start = time.monotonic()
        proc = subprocess.Popen(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append((index, start, proc))

    results: List[Dict[str, Any]] = []
    for index, start, proc in processes:
        stdout, stderr = proc.communicate()
        wall_time = max(time.monotonic() - start, 0.001)
        stat = speedtest_stat_from_output(stdout or "", stderr or "", proc.returncode, wall_time)
        stat["worker"] = index + 1
        stat["wall_time"] = wall_time
        results.append(stat)

    return results


def print_speedtest_results(node_name: str, proxy: str, workers: int, duration: int, url: str, results: List[Dict[str, Any]]) -> None:
    ok_results = [r for r in results if r.get("ok")]
    total_bytes = sum(float(r.get("size_download") or 0) for r in results)
    elapsed = max([float(r.get("time_total") or 0.001) for r in results] + [0.001])
    aggregate_speed = total_bytes / elapsed

    print("\n测速结果：")
    print(f"节点：{node_name}")
    print(f"模式：{'单线程' if workers == 1 else str(workers) + '线程'}")
    print(f"代理：{proxy}")
    print(f"下载源：{url}")
    print(f"测速时长：{duration} 秒")
    print(f"总下载：{human_size(total_bytes)}")
    print(f"聚合速度：{human_speed(aggregate_speed)}")

    if workers > 1:
        print("\n各线程：")
        for r in results:
            size = float(r.get("size_download") or 0)
            seconds = max(float(r.get("time_total") or 0.001), 0.001)
            speed = size / seconds
            status = "OK" if r.get("ok") else f"失败 rc={r.get('returncode')}"
            remote_ip = str(r.get("remote_ip") or "-")
            print(f"  线程 {r.get('worker')}: {human_speed(speed)}，下载 {human_size(size)}，HTTP {r.get('http_code') or '-'}，CDN IP {remote_ip}，{status}")

    failed = [r for r in results if not r.get("ok")]
    if failed and not ok_results:
        print("\n测速失败详情：")
        for r in failed:
            msg = r.get("stderr") or r.get("stdout") or "无错误输出"
            print(f"  线程 {r.get('worker')}: rc={r.get('returncode')} {msg}")
    elif failed:
        print("\n部分线程失败：")
        for r in failed:
            msg = r.get("stderr") or r.get("stdout") or "无错误输出"
            print(f"  线程 {r.get('worker')}: rc={r.get('returncode')} {msg}")


def action_speedtest(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> None:
    node = choose_node(mihomo, ew)
    if not node:
        return

    proxy = proxy_for_ip_check(node)
    if not proxy:
        print("该节点没有可用 socks 入站，无法测速。")
        return

    print("\n选择 Apple CDN 下载测速模式：")
    print("1. 单线程")
    print("2. 4线程")
    choice = read_choice_default("选择模式，直接回车默认单线程", 1, 2, default=1, allow_q=True)
    if choice is None:
        return

    workers = 1 if choice == 1 else 4
    duration = ask_int("测速时长，单位：秒", SPEEDTEST_DURATION, low=5, high=600)
    url = ask("Apple CDN 测速文件 URL", APPLE_CDN_SPEEDTEST_URL, required=True)

    print(f"\n即将通过 {proxy} 下载 Apple CDN 文件测速：")
    print(f"节点：{node['name']}")
    print(f"模式：{'单线程' if workers == 1 else '4线程'}")
    print(f"时长：{duration} 秒")
    if not ask_bool("确认开始测速", True):
        return

    try:
        results = run_apple_cdn_speedtest(proxy, workers, duration, url)
    except KeyboardInterrupt:
        print("\n测速已中止。")
        return

    print_speedtest_results(node["name"], proxy, workers, duration, url, results)


def mask_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        masked_qs = []
        for key, value in qs:
            if key.lower() in {"token", "key", "access_token"} and value:
                if len(value) > 10:
                    value = value[:6] + "..." + value[-4:]
                else:
                    value = "***"
            masked_qs.append((key, value))
        query = urllib.parse.urlencode(masked_qs)
        return urllib.parse.urlunparse(parsed._replace(query=query))
    except Exception:
        return url


def fetch_url_text(url: str, label: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "egressctl/1.0",
            "Accept": "text/yaml, application/yaml, text/plain, */*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=SUBSCRIPTION_TIMEOUT) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            charset = "utf-8"
            m = re.search(r"charset=([A-Za-z0-9_.-]+)", content_type)
            if m:
                charset = m.group(1)
            try:
                return raw.decode(charset, errors="replace")
            except LookupError:
                return raw.decode("utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"下载{label}订阅失败：{exc}") from exc


def load_yaml_text(text: str) -> Any:
    if _YAML_KIND == "ruamel":
        return yaml_loader().load(io.StringIO(text))
    return pyyaml.safe_load(text)  # type: ignore[name-defined]


def try_parse_yaml_subscription(text: str) -> Any:
    try:
        return load_yaml_text(text)
    except Exception:
        return None


def maybe_decode_subscription_text(text: str) -> str:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return text
    if not re.fullmatch(r"[A-Za-z0-9+/=_-]+", compact):
        return text
    try:
        decoded = b64decode_text(compact)
    except Exception:
        return text
    # Avoid replacing a valid YAML payload with random decoded binary-like text.
    if any(marker in decoded for marker in ("proxies:", "ss://", "socks5://", "socks5h://")):
        return decoded
    return text


def normalize_subscription_proxies(raw_proxies: Any, source_name: str) -> List[Dict[str, Any]]:
    if not isinstance(raw_proxies, list):
        raise ValueError(f"{source_name}订阅中未找到 proxies 列表。")

    proxies: List[Dict[str, Any]] = []
    seen: set[str] = set()
    skipped = 0
    for item in raw_proxies:
        d = copy.deepcopy(as_dict(item))
        if not d:
            skipped += 1
            continue
        name = normalize_subscription_node_name(d.get("name"))
        if not name:
            skipped += 1
            continue
        key = node_key(name)
        if key in seen:
            print(f"{source_name}订阅发现重复节点，已跳过：{name}")
            continue
        seen.add(key)
        d["name"] = name
        proxies.append(d)

    if not proxies:
        raise ValueError(f"{source_name}订阅没有可用节点。")
    if skipped:
        print(f"{source_name}订阅跳过无效节点：{skipped} 个。")
    return proxies


def parse_subscription_proxies(text: str, source_name: str) -> List[Dict[str, Any]]:
    candidates = [text, maybe_decode_subscription_text(text)]
    checked: set[str] = set()

    for candidate in candidates:
        if candidate in checked:
            continue
        checked.add(candidate)
        data = try_parse_yaml_subscription(candidate)
        if isinstance(data, dict):
            if isinstance(data.get("proxies"), list):
                return normalize_subscription_proxies(data.get("proxies"), source_name)
            if isinstance(data.get("Proxy"), list):
                return normalize_subscription_proxies(data.get("Proxy"), source_name)
        if isinstance(data, list):
            return normalize_subscription_proxies(data, source_name)

    # Fallback for plain/base64 share-link subscription. This script only has
    # built-in conversion for ss:// and socks/socks5:// links.
    share_proxies: List[Dict[str, Any]] = []
    fallback_text = candidates[-1]
    for line in re.split(r"[\r\n]+", fallback_text):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        scheme = urllib.parse.urlparse(line).scheme.lower()
        if scheme in {"ss", "socks", "socks5", "socks5h"}:
            try:
                share_proxies.append(parse_share_link(line))
            except Exception as exc:
                print(f"{source_name}订阅跳过无法解析的链接：{exc}")
    if share_proxies:
        return normalize_subscription_proxies(share_proxies, source_name)

    raise ValueError(f"{source_name}订阅格式无法识别；需要 Clash/Mihomo YAML 或 ss/socks 链接订阅。")


def fetch_subscription_proxies(url: str, source_name: str) -> List[Dict[str, Any]]:
    print(f"正在下载{source_name}订阅：{mask_url(url)}")
    text = fetch_url_text(url, source_name)
    proxies = parse_subscription_proxies(text, source_name)
    print(f"{source_name}订阅节点数：{len(proxies)}")
    return proxies


def proxy_key_set(proxies: Iterable[Dict[str, Any]]) -> set[str]:
    return {node_key(as_dict(proxy).get("name")) for proxy in proxies if node_key(as_dict(proxy).get("name"))}


def existing_egress_ports_by_key(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for view in collect_node_views(mihomo, ew):
        key = node_key(view.get("name"))
        port = view.get("port")
        if key and port:
            try:
                mapping[key] = int(port)
            except Exception:
                pass
    return mapping


def egress_node_keys(ew: Dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for item in ew.get("nodes") or []:
        key = node_key(as_dict(item).get("name"))
        if key:
            keys.add(key)
    return keys


def existing_node_keys_from_views(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for view in collect_node_views(mihomo, ew):
        key = node_key(view.get("name"))
        if key:
            keys.add(key)
    return keys


def build_compat_node(name: str, socks_url: str) -> Dict[str, str]:
    return {"name": socks_node_name(name), "socks": socks_url}


def remove_egress_managed_listeners(mihomo: Dict[str, Any], keys: set[str]) -> None:
    if not keys or not isinstance(mihomo.get("listeners"), list):
        return

    def should_remove(listener: Any) -> bool:
        d = as_dict(listener)
        if norm_name(d.get("type")).lower() != "socks":
            return False
        lname_key = node_key(d.get("name"))
        proxy_key = node_key(d.get("proxy"))
        return lname_key in keys or proxy_key in keys

    mihomo["listeners"] = [l for l in mihomo.get("listeners") or [] if not should_remove(l)]


def choose_free_port_with_used(mihomo: Dict[str, Any], ew: Dict[str, Any], used: set[int]) -> int:
    candidates = list(range(PORT_MIN, PORT_MAX + 1))
    random.shuffle(candidates)
    for port in candidates:
        if port not in used and can_bind_local(port):
            used.add(port)
            return port
    raise RuntimeError(f"{PORT_MIN}-{PORT_MAX} 范围内没有可用端口；可用 EW_PORT_MIN/EW_PORT_MAX 调整范围。")


def clean_proxy_group_references(mihomo: Dict[str, Any]) -> None:
    proxies = ensure_list(mihomo, "proxies")
    groups = ensure_list(mihomo, "proxy-groups")

    proxy_names = {canonical_node_name(as_dict(proxy).get("name")) for proxy in proxies if canonical_node_name(as_dict(proxy).get("name"))}
    group_names = {norm_name(as_dict(group).get("name")) for group in groups if norm_name(as_dict(group).get("name"))}
    builtins = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "GLOBAL", "COMPATIBLE"}
    allowed = proxy_names | group_names | builtins

    for group in groups:
        gd = as_dict(group)
        refs = gd.get("proxies")
        if not isinstance(refs, list):
            continue

        cleaned: List[Any] = []
        seen: set[str] = set()
        for ref in refs:
            ref_s = str(ref)
            canonical_ref = canonical_node_name(ref_s)
            keep = ref_s in allowed or canonical_ref in allowed
            if keep:
                value = canonical_ref if canonical_ref in proxy_names else ref
                key = str(value)
                if key not in seen:
                    seen.add(key)
                    cleaned.append(value)

        if not cleaned:
            # Avoid invalid empty select/url-test/fallback groups after full subscription replacement.
            cleaned = ["DIRECT"]
        gd["proxies"] = cleaned


def sync_subscriptions_apply(
    mihomo: Dict[str, Any],
    ew: Dict[str, Any],
    mihomo_url: str,
    egress_url: str,
    confirm: bool = True,
) -> bool:
    print("\n同步订阅节点")
    print("说明：Mihomo proxies 将按 Mihomo 订阅全量同步。")
    print("Mihomo 订阅中的每个节点都会在 /etc/mihomo/config.yaml 生成/覆盖对应的本地 socks 入站 listener。")
    print("只有 EgressWatch 订阅中存在的节点，才会写入 /root/projects/EgressWatch/config.yaml。")
    print(f"Mihomo 订阅：{mask_url(mihomo_url)}")
    print(f"EgressWatch 订阅：{mask_url(egress_url)}")

    mihomo_sub = fetch_subscription_proxies(mihomo_url, "Mihomo")
    egress_sub = fetch_subscription_proxies(egress_url, "EgressWatch")

    mihomo_keys = proxy_key_set(mihomo_sub)
    egress_keys_new = proxy_key_set(egress_sub)
    missing = [
        canonical_node_name(proxy.get("name"))
        for proxy in egress_sub
        if node_key(proxy.get("name")) not in mihomo_keys
    ]
    if missing:
        preview = "、".join(missing[:10])
        suffix = " ..." if len(missing) > 10 else ""
        raise ValueError(f"EgressWatch 订阅中有 {len(missing)} 个节点不在 Mihomo 订阅中：{preview}{suffix}")

    old_proxy_count = len(mihomo.get("proxies") or [])
    old_listener_count = len(mihomo.get("listeners") or [])
    old_egress_count = len(ew.get("nodes") or [])
    print("\n同步计划：")
    print(f"  Mihomo proxies：{old_proxy_count} -> {len(mihomo_sub)}")
    print(f"  Mihomo socks listeners：{old_listener_count} -> 至少 {len(mihomo_sub)} 个订阅节点 listener")
    print(f"  EgressWatch nodes：{old_egress_count} -> {len(egress_sub)}")
    print(f"  将为 Mihomo 订阅中的 {len(mihomo_sub)} 个节点生成/保留本地 socks 入站。")
    print(f"  其中 {len(egress_sub)} 个 EgressWatch 订阅节点会写入 EgressWatch 配置。")

    if confirm and not ask_bool("确认开始同步订阅节点", True):
        return False

    old_ports = existing_egress_ports_by_key(mihomo, ew)
    old_all_keys = existing_node_keys_from_views(mihomo, ew)

    # Full Mihomo outbound sync.
    mihomo["proxies"] = copy.deepcopy(mihomo_sub)

    # Remove old managed SOCKS listeners for both old nodes and current Mihomo
    # subscription nodes, then recreate one listener for every Mihomo subscription
    # node. This keeps /etc/mihomo/config.yaml complete even when EgressWatch only
    # monitors a subset.
    remove_egress_managed_listeners(mihomo, old_all_keys | mihomo_keys)

    # Avoid reserving stale compatibility top-level nodes while assigning ports.
    # If the file originally has this compatibility list, save_validate_reload()
    # will write the refreshed full Mihomo subscription list back via override.
    has_compat_nodes = "nodes" in mihomo and compatibility_nodes_look_like_egress(mihomo.get("nodes"))
    if has_compat_nodes:
        mihomo["nodes"] = []

    ew["nodes"] = []
    used = used_local_ports(mihomo, ew)
    socks_by_key: Dict[str, str] = {}
    compat_nodes: List[Dict[str, str]] = []

    for proxy in mihomo_sub:
        name = canonical_node_name(proxy.get("name"))
        key = node_key(name)
        port = old_ports.get(key)
        if port and int(port) not in used:
            used.add(int(port))
        else:
            port = choose_free_port_with_used(mihomo, ew, used)

        socks_url = make_socks_url(int(port))
        upsert_listener(mihomo, None, name, int(port))
        socks_by_key[key] = socks_url
        compat_nodes.append(build_compat_node(name, socks_url))

    for proxy in egress_sub:
        name = canonical_node_name(proxy.get("name"))
        key = node_key(name)
        socks_url = socks_by_key.get(key)
        if not socks_url:
            raise ValueError(f"内部错误：未找到 EgressWatch 节点对应的 Mihomo socks 入站：{name}")
        upsert_egress_node(ew, None, name, socks_url)

    if has_compat_nodes:
        mihomo["__egressctl_compat_nodes_override"] = compat_nodes

    clean_proxy_group_references(mihomo)

    if save_validate_reload(mihomo, ew):
        print("订阅同步完成。")
        print(f"Mihomo 节点：{len(mihomo_sub)} 个；Mihomo socks 入站：{len(mihomo_sub)} 个；EgressWatch 监控节点：{len(egress_sub)} 个。")
        return True
    return False


def action_sync_subscriptions(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> None:
    print("\n同步订阅节点")
    print("脚本不再内置默认订阅链接；请在下面输入订阅 URL。")
    print("如果已保存过订阅 URL，直接回车默认使用最近保存的值；也可输入新的 URL 覆盖保存。")
    print("如果已设置环境变量 MIHOMO_SUB_URL / EGRESSWATCH_SUB_URL，但同时存在最近保存值，默认优先使用最近保存值。")

    saved_mihomo_url, saved_egress_url = saved_subscription_urls()
    mihomo_url = ask_subscription_url("Mihomo 订阅 URL", MIHOMO_SUBSCRIPTION_URL, saved_mihomo_url)
    egress_url = ask_subscription_url("EgressWatch 订阅 URL", EGRESSWATCH_SUBSCRIPTION_URL, saved_egress_url)

    if not sync_subscriptions_apply(mihomo, ew, mihomo_url, egress_url, confirm=True):
        return

    save_subscription_urls(mihomo_url, egress_url)

    interval = ask_int("订阅自动同步间隔，单位：小时", SUBSCRIPTION_DEFAULT_INTERVAL_HOURS, low=1, high=8760)
    print("订阅同步定时任务将使用本次输入的 Mihomo / EgressWatch 订阅 URL。")
    install_subscription_sync_cron(interval, mihomo_url, egress_url)


def parse_cli_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EgressWatch / Mihomo 节点管理工具")
    parser.add_argument(
        "--sync-subscriptions",
        action="store_true",
        help="非交互模式：同步 Mihomo 与 EgressWatch 订阅节点。",
    )
    parser.add_argument(
        "--mihomo-sub-url",
        default=MIHOMO_SUBSCRIPTION_URL,
        help="Mihomo 订阅 URL。--sync-subscriptions 模式下必填，或通过 MIHOMO_SUB_URL 环境变量提供。",
    )
    parser.add_argument(
        "--egress-sub-url",
        default=EGRESSWATCH_SUBSCRIPTION_URL,
        help="EgressWatch 订阅 URL。--sync-subscriptions 模式下必填，或通过 EGRESSWATCH_SUB_URL 环境变量提供。",
    )
    return parser.parse_args(argv)


def require_subscription_url_for_cli(label: str, value: str) -> str:
    value = norm_name(value)
    if not value:
        print(f"错误：非交互订阅同步必须提供 {label}。", file=sys.stderr)
        print("请使用 --mihomo-sub-url / --egress-sub-url，或设置 MIHOMO_SUB_URL / EGRESSWATCH_SUB_URL。", file=sys.stderr)
        raise SystemExit(2)

    parsed = urllib.parse.urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        print(f"错误：{label} 不是有效的 http:// 或 https:// URL。", file=sys.stderr)
        raise SystemExit(2)
    return value


def run_cli_if_requested(argv: List[str]) -> bool:
    if not argv:
        return False
    args = parse_cli_args(argv)
    if args.sync_subscriptions:
        mihomo_url = require_subscription_url_for_cli("Mihomo 订阅 URL", args.mihomo_sub_url)
        egress_url = require_subscription_url_for_cli("EgressWatch 订阅 URL", args.egress_sub_url)

        mihomo, ew = load_configs()
        ok = sync_subscriptions_apply(
            mihomo,
            ew,
            mihomo_url,
            egress_url,
            confirm=False,
        )
        if ok:
            save_subscription_urls(mihomo_url, egress_url)
        raise SystemExit(0 if ok else 1)
    return False

def load_configs() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    mihomo = load_yaml(MIHOMO_CONFIG)
    ew = load_yaml(EGRESSWATCH_CONFIG)
    ensure_list(ew, "nodes")
    return mihomo, ew


def print_header() -> None:
    print("=" * 72)
    print("EgressWatch / Mihomo 节点管理")
    print(f"Mihomo 配置：{MIHOMO_CONFIG}")
    print(f"EgressWatch 配置：{EGRESSWATCH_CONFIG}")
    print(f"Mihomo 服务：{MIHOMO_SERVICE}")
    print(f"YAML 引擎：{_YAML_KIND}")
    print("=" * 72)


def pause() -> None:
    input("按回车继续...")


def main() -> None:
    if PORT_MIN > PORT_MAX:
        raise SystemExit("EW_PORT_MIN 不能大于 EW_PORT_MAX")
    if os.geteuid() != 0:
        print("提示：当前不是 root。写入 /etc/mihomo 或重载 systemd 可能失败。")

    while True:
        try:
            print_header()
            print("1. 查看分组/节点")
            print("2. 新增节点")
            print("3. 编辑节点")
            print("4. 删除节点")
            print("5. 选择节点执行 IP 质量检测")
            print("6. 仅同步/重建 Mihomo 分组")
            print("7. 修改定时检测 IP 时间间隔")
            print("8. 选择节点测速（Apple CDN）")
            print("9. 同步订阅节点")
            print("q. 退出")
            choice_raw = input("请选择：").strip().lower()
            choice_parts = choice_raw.split()
            quick_ip_pair: Optional[Tuple[int, int]] = None
            if len(choice_parts) == 3 and choice_parts[0] == "5" and choice_parts[1].isdigit() and choice_parts[2].isdigit():
                choice = "5"
                quick_ip_pair = (int(choice_parts[1]), int(choice_parts[2]))
            else:
                choice = choice_raw

            if choice in {"q", "quit", "exit"}:
                return
            if choice == "7":
                action_change_cron_interval()
                pause()
            elif choice in {"1", "2", "3", "4", "5", "6", "8", "9"}:
                mihomo, ew = load_configs()
                if choice == "1":
                    print_groups(mihomo, ew)
                    pause()
                elif choice == "2":
                    action_add(mihomo, ew)
                    pause()
                elif choice == "3":
                    action_edit(mihomo, ew)
                    pause()
                elif choice == "4":
                    action_delete(mihomo, ew)
                    pause()
                elif choice == "5":
                    action_ip_check(mihomo, ew, quick_ip_pair)
                    pause()
                elif choice == "6":
                    action_sync_groups(mihomo, ew)
                    pause()
                elif choice == "8":
                    action_speedtest(mihomo, ew)
                    pause()
                elif choice == "9":
                    action_sync_subscriptions(mihomo, ew)
                    pause()
            else:
                print("无效选择。")
                pause()
        except KeyboardInterrupt:
            print("\n已退出。")
            return
        except Exception as exc:
            print(f"错误：{exc}", file=sys.stderr)
            try:
                pause()
            except KeyboardInterrupt:
                print("\n已退出。")
                return


if __name__ == "__main__":
    try:
        run_cli_if_requested(sys.argv[1:])
        main()
    except KeyboardInterrupt:
        print("\n已退出。")
        raise SystemExit(0)
