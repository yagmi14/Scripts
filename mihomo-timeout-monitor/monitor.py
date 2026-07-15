#!/usr/bin/env python3

import concurrent.futures
import datetime as dt
import html
import json
import logging
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


BASE_DIR = Path("/opt/mihomo-timeout-monitor")
ENV_FILE = BASE_DIR / ".env"
STATE_FILE = Path("/var/lib/mihomo-timeout-monitor/state.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

# 不检测策略组和 Mihomo 内置节点
SKIP_TYPES = {
    "Direct",
    "Reject",
    "RejectDrop",
    "Reject-Drop",
    "Pass",
    "Selector",
    "URLTest",
    "Fallback",
    "LoadBalance",
    "Relay",
}

SKIP_NAMES = {
    "DIRECT",
    "REJECT",
    "REJECT-DROP",
    "PASS",
    "GLOBAL",
}


def load_env_file(path):
    """每轮重新读取 .env，使多数修改无需重启服务。"""
    values = {}

    if not path.exists():
        raise FileNotFoundError("配置文件不存在：{}".format(path))

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {'"', "'"}
        ):
            value = value[1:-1]

        values[key] = value

    return values


def get_int(cfg, key, default, minimum=1):
    try:
        return max(minimum, int(cfg.get(key, str(default))))
    except ValueError:
        logging.warning(
            "%s 不是有效整数，使用默认值 %s",
            key,
            default,
        )
        return default


def api_request(cfg, path, timeout_seconds):
    base = cfg.get(
        "MIHOMO_API",
        "http://127.0.0.1:9090",
    ).rstrip("/")

    request = urllib.request.Request(base + path)

    secret = cfg.get("MIHOMO_SECRET", "")
    if secret:
        request.add_header(
            "Authorization",
            "Bearer {}".format(secret),
        )

    request.add_header("Accept", "application/json")

    with urllib.request.urlopen(
        request,
        timeout=timeout_seconds,
    ) as response:
        body = response.read().decode(
            "utf-8",
            errors="replace",
        )

        return json.loads(body) if body else {}


def list_original_nodes(cfg):
    """
    从 Mihomo API 获取节点。

    策略组一般包含 all 字段，单个原始代理节点不包含。
    SOCKS/HTTP 入站监听不会作为代理节点出现在这里。
    """
    data = api_request(
        cfg,
        "/proxies",
        timeout_seconds=10,
    )

    proxies = data.get("proxies", {})
    nodes = []

    for name, detail in proxies.items():
        if not isinstance(detail, dict):
            continue

        proxy_type = str(detail.get("type", ""))

        # 策略组通常有 all 字段
        if isinstance(detail.get("all"), list):
            continue

        if name.upper() in SKIP_NAMES:
            continue

        if proxy_type in SKIP_TYPES:
            continue

        nodes.append(name)

    return sorted(
        set(nodes),
        key=str.casefold,
    )


def test_one_node(cfg, node):
    test_url = cfg.get(
        "TEST_URL",
        "https://captive.apple.com/generate_204",
    )

    timeout_ms = get_int(
        cfg,
        "TIMEOUT_MS",
        5000,
        100,
    )

    encoded_name = urllib.parse.quote(
        node,
        safe="",
    )

    query = urllib.parse.urlencode(
        {
            "url": test_url,
            "timeout": timeout_ms,
        }
    )

    path = "/proxies/{}/delay?{}".format(
        encoded_name,
        query,
    )

    try:
        data = api_request(
            cfg,
            path,
            timeout_seconds=(timeout_ms / 1000) + 3,
        )

        delay = data.get("delay")

        if isinstance(delay, int) and delay > 0:
            return node, False, delay, ""

        return (
            node,
            True,
            None,
            data.get("message", "未返回有效延迟"),
        )

    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
        except Exception:
            body = ""

        return (
            node,
            True,
            None,
            body or "HTTP {}".format(exc.code),
        )

    except (
        urllib.error.URLError,
        TimeoutError,
        socket.timeout,
    ) as exc:
        return node, True, None, str(exc)

    except Exception as exc:
        return (
            node,
            True,
            None,
            "{}: {}".format(
                type(exc).__name__,
                exc,
            ),
        )



def test_nodes_parallel(cfg, nodes, workers):
    """并发检测一组节点，返回 test_one_node() 的结果列表。"""
    if not nodes:
        return []

    max_workers = min(workers, len(nodes))
    results = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:
        futures = [
            executor.submit(
                test_one_node,
                cfg,
                node,
            )
            for node in nodes
        ]

        for future in concurrent.futures.as_completed(
            futures
        ):
            results.append(future.result())

    return results


def confirm_timeout_nodes(cfg, initial_timeouts, workers):
    """
    对初检超时的节点执行多轮复检。

    只有初检和全部复检都失败的节点，才会被确认为超时。
    任意一次复检成功，就从本轮通知中移除。
    """
    retry_attempts = get_int(
        cfg,
        "RECHECK_ATTEMPTS",
        3,
        0,
    )
    retry_interval = get_int(
        cfg,
        "RECHECK_INTERVAL_SECONDS",
        3,
        0,
    )

    pending = {
        name: reason
        for name, reason in initial_timeouts
    }

    if not pending or retry_attempts == 0:
        return sorted(
            pending.items(),
            key=lambda item: item[0].casefold(),
        )

    initial_count = len(pending)

    logging.info(
        "初检发现 %d 个超时节点，开始复检：次数=%d，间隔=%d秒",
        initial_count,
        retry_attempts,
        retry_interval,
    )

    for attempt in range(1, retry_attempts + 1):
        if retry_interval > 0:
            time.sleep(retry_interval)

        nodes_to_test = sorted(
            pending,
            key=str.casefold,
        )

        results = test_nodes_parallel(
            cfg,
            nodes_to_test,
            workers,
        )

        still_timed_out = {}
        recovered = []

        for name, is_timeout, delay, reason in results:
            if is_timeout:
                still_timed_out[name] = reason
            else:
                recovered.append((name, delay))

        if recovered:
            logging.info(
                "第 %d/%d 次复检恢复 %d 个节点：%s",
                attempt,
                retry_attempts,
                len(recovered),
                ", ".join(
                    "{}({}ms)".format(name, delay)
                    for name, delay in sorted(
                        recovered,
                        key=lambda item: item[0].casefold(),
                    )
                ),
            )

        pending = still_timed_out

        logging.info(
            "第 %d/%d 次复检完成，仍超时=%d",
            attempt,
            retry_attempts,
            len(pending),
        )

        if not pending:
            break

    confirmed = sorted(
        pending.items(),
        key=lambda item: item[0].casefold(),
    )

    logging.info(
        "复检结束：初检超时=%d，确认超时=%d，已过滤波动=%d",
        initial_count,
        len(confirmed),
        initial_count - len(confirmed),
    )

    return confirmed


def telegram_send(cfg, text):
    token = cfg.get("TG_BOT_TOKEN", "")
    chat_id = cfg.get("TG_CHAT_ID", "")

    if not token or not chat_id:
        raise RuntimeError(
            "TG_BOT_TOKEN 或 TG_CHAT_ID 未配置"
        )

    endpoint = (
        "https://api.telegram.org/bot"
        + token
        + "/sendMessage"
    )

    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=15,
    ) as response:
        result = json.loads(
            response.read().decode(
                "utf-8",
                errors="replace",
            )
        )

        if not result.get("ok"):
            raise RuntimeError(
                "Telegram 返回失败：{}".format(result)
            )


def split_messages(header, lines, limit=3900):
    """防止节点过多导致 Telegram 消息超过长度限制。"""
    messages = []
    current = header

    for line in lines:
        candidate = current + "\n" + line

        if len(candidate) > limit and current != header:
            messages.append(current)
            current = header + "\n" + line
        else:
            current = candidate

    if current != header or not messages:
        messages.append(current)

    return messages


def load_previous_timeouts():
    try:
        data = json.loads(
            STATE_FILE.read_text(encoding="utf-8")
        )
        return set(data.get("timeouts", []))
    except Exception:
        return set()


def save_timeouts(nodes):
    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = STATE_FILE.with_suffix(".tmp")

    temp.write_text(
        json.dumps(
            {"timeouts": nodes},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    os.replace(temp, STATE_FILE)


def send_timeout_report(cfg, timed_out, total):
    now = (
        dt.datetime.now()
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S %Z")
    )

    header = (
        "<b>⚠️ Mihomo 节点延迟检测超时</b>\n"
        "时间：<code>{}</code>\n"
        "超时：<b>{}</b> / {}"
    ).format(
        html.escape(now),
        len(timed_out),
        total,
    )

    lines = []

    for index, item in enumerate(timed_out, 1):
        node_name = item[0]

        lines.append(
            "{}. <code>{}</code>".format(
                index,
                html.escape(node_name),
            )
        )

    for message in split_messages(header, lines):
        telegram_send(cfg, message)


def send_monitor_error(cfg, error):
    enabled = cfg.get(
        "NOTIFY_MONITOR_ERRORS",
        "false",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if not enabled:
        return

    now = (
        dt.datetime.now()
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S %Z")
    )

    message = (
        "<b>❌ Mihomo 检测程序异常</b>\n"
        "时间：<code>{}</code>\n"
        "错误：<code>{}</code>"
    ).format(
        html.escape(now),
        html.escape(str(error)),
    )

    telegram_send(cfg, message)


def run_once(cfg):
    nodes = list_original_nodes(cfg)

    if not nodes:
        raise RuntimeError(
            "API 中未找到可检测的原始代理节点"
        )

    workers = min(
        get_int(cfg, "WORKERS", 10, 1),
        len(nodes),
    )

    results = test_nodes_parallel(
        cfg,
        nodes,
        workers,
    )

    initial_timeouts = sorted(
        [
            (name, reason)
            for name, is_timeout, delay, reason in results
            if is_timeout
        ],
        key=lambda item: item[0].casefold(),
    )

    logging.info(
        "初检完成：总节点=%d，初检超时=%d",
        len(nodes),
        len(initial_timeouts),
    )

    timed_out = confirm_timeout_nodes(
        cfg,
        initial_timeouts,
        workers,
    )

    logging.info(
        "本轮检测完成：总节点=%d，确认超时=%d",
        len(nodes),
        len(timed_out),
    )

    mode = cfg.get(
        "NOTIFY_MODE",
        "every",
    ).strip().lower()

    previous = load_previous_timeouts()
    current = {
        name
        for name, reason in timed_out
    }

    should_send = bool(timed_out)

    if mode == "change":
        should_send = (
            bool(timed_out)
            and current != previous
        )

    if should_send:
        send_timeout_report(
            cfg,
            timed_out,
            len(nodes),
        )

        logging.info(
            "已发送 Telegram 超时通知"
        )

    if (
        mode == "change"
        and previous
        and not current
    ):
        recovery_enabled = cfg.get(
            "SEND_RECOVERY",
            "false",
        ).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        if recovery_enabled:
            telegram_send(
                cfg,
                "<b>✅ Mihomo 节点检测恢复</b>\n"
                "当前没有超时节点。",
            )

    save_timeouts(
        sorted(current, key=str.casefold)
    )


def main():
    logging.info(
        "Mihomo 节点超时监控已启动"
    )

    while True:
        interval = 300
        cfg = {}

        try:
            cfg = load_env_file(ENV_FILE)

            interval = get_int(
                cfg,
                "CHECK_INTERVAL_SECONDS",
                300,
                10,
            )

            run_once(cfg)

        except Exception as exc:
            logging.exception(
                "本轮检测失败：%s",
                exc,
            )

            try:
                if cfg:
                    send_monitor_error(cfg, exc)
            except Exception:
                logging.exception(
                    "发送监控异常通知失败"
                )

        time.sleep(interval)


if __name__ == "__main__":
    main()
