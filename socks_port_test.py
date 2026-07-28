#!/usr/bin/env python3

import getpass
import ipaddress
import socket
import struct

PORTS = [
    80, 443, 8080, 8443, 8000, 8888,
    22, 21, 25, 465, 587, 110, 143,
    993, 995, 5222, 5223, 1935, 3478,
    5349, 9000
]

REPLY_CODES = {
    0x00: "允许连接",
    0x01: "SOCKS5 通用错误",
    0x02: "被代理规则屏蔽",
    0x03: "目标网络不可达",
    0x04: "目标主机不可达",
    0x05: "目标端口拒绝连接",
    0x06: "TTL 已过期",
    0x07: "不支持 CONNECT 命令",
    0x08: "不支持该地址类型",
}


def recv_exact(sock, size):
    data = b""

    while len(data) < size:
        chunk = sock.recv(size - len(data))

        if not chunk:
            raise ConnectionError("连接被提前关闭")

        data += chunk

    return data


def test_port(proxy_host, proxy_port, username, password,
              target_host, target_port, timeout):

    sock = None

    try:
        sock = socket.create_connection(
            (proxy_host, proxy_port),
            timeout=timeout
        )
        sock.settimeout(timeout)

        if username:
            sock.sendall(b"\x05\x02\x00\x02")
        else:
            sock.sendall(b"\x05\x01\x00")

        version, method = recv_exact(sock, 2)

        if version != 5:
            return False, "返回的不是 SOCKS5 协议"

        if method == 0xFF:
            return False, "代理不接受当前认证方式"

        if method == 0x02:
            if not username:
                return False, "代理要求用户名密码"

            user_bytes = username.encode()
            pass_bytes = password.encode()

            auth_packet = (
                b"\x01"
                + bytes([len(user_bytes)])
                + user_bytes
                + bytes([len(pass_bytes)])
                + pass_bytes
            )

            sock.sendall(auth_packet)

            _, auth_status = recv_exact(sock, 2)

            if auth_status != 0:
                return False, "用户名或密码错误"

        elif method != 0x00:
            return False, f"不支持的认证方式：0x{method:02x}"

        try:
            target_ip = ipaddress.ip_address(target_host)

            if target_ip.version == 4:
                address = b"\x01" + target_ip.packed
            else:
                address = b"\x04" + target_ip.packed

        except ValueError:
            domain = target_host.encode("idna")

            if len(domain) > 255:
                return False, "目标域名过长"

            address = b"\x03" + bytes([len(domain)]) + domain

        request = (
            b"\x05"
            b"\x01"
            b"\x00"
            + address
            + struct.pack("!H", target_port)
        )

        sock.sendall(request)

        version, reply, _, address_type = recv_exact(sock, 4)

        if version != 5:
            return False, "SOCKS5 响应格式错误"

        if address_type == 0x01:
            recv_exact(sock, 4)
        elif address_type == 0x03:
            domain_length = recv_exact(sock, 1)[0]
            recv_exact(sock, domain_length)
        elif address_type == 0x04:
            recv_exact(sock, 16)
        else:
            return False, f"未知地址类型：0x{address_type:02x}"

        recv_exact(sock, 2)

        result = REPLY_CODES.get(
            reply,
            f"未知返回码：0x{reply:02x}"
        )

        return reply == 0x00, result

    except socket.timeout:
        return False, "连接超时"
    except ConnectionRefusedError:
        return False, "SOCKS5 代理端口拒绝连接"
    except Exception as exc:
        return False, str(exc)
    finally:
        if sock is not None:
            sock.close()


def main():
    proxy_host = input("SOCKS5 地址：").strip()
    proxy_port = int(input("SOCKS5 端口：").strip())

    username = input("用户名（无认证直接回车）：").strip()

    if username:
        password = getpass.getpass("密码：")
    else:
        password = ""

    target_host = input("测试 VPS 公网 IP 或域名：").strip()

    timeout_text = input("单端口超时秒数 [6]：").strip()
    timeout = float(timeout_text or "6")

    print()
    print(f"代理：{proxy_host}:{proxy_port}")
    print(f"目标：{target_host}")
    print("-" * 58)

    allowed = []
    blocked = []
    failed = []

    for port in PORTS:
        success, message = test_port(
            proxy_host,
            proxy_port,
            username,
            password,
            target_host,
            port,
            timeout
        )

        if success:
            status = "允许"
            allowed.append(port)
        elif message == "被代理规则屏蔽":
            status = "屏蔽"
            blocked.append(port)
        else:
            status = "失败"
            failed.append((port, message))

        print(f"{port:<6} {status:<6} {message}")

    print("-" * 58)
    print("允许端口：", ", ".join(map(str, allowed)) or "无")
    print("明确屏蔽：", ", ".join(map(str, blocked)) or "无")

    if failed:
        print("其他失败：")

        for port, message in failed:
            print(f"  {port}: {message}")


if __name__ == "__main__":
    main()
