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
"""
from __future__ import annotations

import base64
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
    """If /etc/mihomo/config.yaml already has an EgressWatch-like top-level nodes list,
    keep it synchronized. Real Mihomo uses proxies/listeners; this is only compatibility.
    """
    if "nodes" in mihomo and compatibility_nodes_look_like_egress(mihomo.get("nodes")):
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


def choose_node(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    grouped = print_groups(mihomo, ew)
    gi = read_choice("选择分组序号：", 1, len(COUNTRY_GROUPS))
    if gi is None:
        return None
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


def action_edit(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> None:
    node = choose_node(mihomo, ew)
    if not node:
        return
    old_name = canonical_node_name(node["name"])
    old_port = node.get("port")
    had_listener = node.get("listener") is not None
    old_proxy = copy.deepcopy(find_proxy(mihomo, old_name))

    print(f"\n编辑节点：{old_name}")
    print("粘贴新 ss:// 或 socks5:// 链接；直接回车表示只修改名称并保留原出站配置。")
    uri = input("新链接：").strip()

    parsed_proxy: Optional[Dict[str, Any]] = None
    if uri:
        try:
            parsed_proxy = parse_share_link(uri)
            parsed_name = canonical_node_name(parsed_proxy.get("name"))
            if parsed_name:
                print(f"链接内 name：{parsed_name}")
        except Exception as exc:
            print(f"解析失败：{exc}")
            return

    new_name = canonical_node_name(ask("节点 name", old_name, required=True))
    if not new_name:
        print("节点 name 不能为空。")
        return

    port = int(old_port) if old_port else choose_free_port(mihomo, ew)
    socks_url = make_socks_url(port)

    if node_key(new_name) != node_key(old_name) and (find_ew_node(ew, new_name) or find_proxy(mihomo, new_name)):
        if not ask_bool(f"目标名称 {new_name} 已存在，是否覆盖", False):
            return
        target = find_ew_node(ew, new_name)
        target_port = parse_port_from_url(norm_name(target.get("socks"))) if target else None
        remove_named_items(mihomo, ew, new_name, target_port)

    new_proxy = parsed_proxy if parsed_proxy is not None else old_proxy
    if new_proxy is not None:
        new_proxy["name"] = new_name
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


def action_ip_check(mihomo: Dict[str, Any], ew: Dict[str, Any]) -> None:
    node = choose_node(mihomo, ew)
    if not node:
        return
    proxy = proxy_for_ip_check(node)
    if not proxy:
        print("该节点没有可用 socks 入站，无法执行检测。")
        return
    print(f"\n将执行等价命令：bash <(curl -Ls https://IP.Check.Place) -x {proxy}")
    if not ask_bool("确认执行远程检测脚本", False):
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
    choice = read_choice("选择模式：", 1, 2, allow_q=True)
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
            print("q. 退出")
            choice = input("请选择：").strip().lower()

            if choice in {"q", "quit", "exit"}:
                return
            if choice == "7":
                action_change_cron_interval()
                pause()
            elif choice in {"1", "2", "3", "4", "5", "6", "8"}:
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
                    action_ip_check(mihomo, ew)
                    pause()
                elif choice == "6":
                    action_sync_groups(mihomo, ew)
                    pause()
                elif choice == "8":
                    action_speedtest(mihomo, ew)
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
        main()
    except KeyboardInterrupt:
        print("\n已退出。")
        raise SystemExit(0)
