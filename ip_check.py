#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import ipaddress
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

PORTS = [22, 80, 443]
TIMEOUT = 0.8
MAX_WORKERS = 80


def ptr_lookup(ip: str):
    print("\n[1] PTR 反解")
    try:
        hostname, aliases, addresses = socket.gethostbyaddr(ip)
        print(f"IP       : {ip}")
        print(f"PTR      : {hostname}")
        if aliases:
            print(f"Aliases  : {aliases}")
        if addresses:
            print(f"Addresses: {addresses}")
        return hostname
    except socket.herror:
        print(f"IP       : {ip}")
        print("PTR      : 无 PTR 记录")
        return None
    except Exception as e:
        print(f"PTR 查询失败: {e}")
        return None


def check_port(ip: str, port: int, timeout: float = TIMEOUT) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def scan_host(ip: str):
    result = {
        "ip": ip,
        "22": False,
        "80": False,
        "443": False,
        "open_ports": []
    }

    for port in PORTS:
        if check_port(ip, port):
            result[str(port)] = True
            result["open_ports"].append(port)

    return result


def scan_24(ip: str):
    print("\n[2] /24 端口检测")

    ip_obj = ipaddress.ip_address(ip)
    network = ipaddress.ip_network(f"{ip_obj}/24", strict=False)

    hosts = [str(h) for h in network.hosts()]

    print(f"目标 IP : {ip}")
    print(f"扫描网段: {network}")
    print(f"检测端口: {PORTS}")
    print(f"超时时间: {TIMEOUT}s")
    print(f"并发数量: {MAX_WORKERS}")
    print("开始扫描...\n")

    start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {
            executor.submit(scan_host, host): host
            for host in hosts
        }

        for future in as_completed(future_map):
            res = future.result()
            results.append(res)

            if res["open_ports"]:
                ports_str = ",".join(map(str, res["open_ports"]))
                print(f"[OPEN] {res['ip']:<15} ports: {ports_str}")

    elapsed = time.time() - start

    return network, results, elapsed


def analyze_results(network, results, elapsed):
    total_hosts = len(results)

    open_any = [r for r in results if r["open_ports"]]
    open_22 = [r for r in results if r["22"]]
    open_80 = [r for r in results if r["80"]]
    open_443 = [r for r in results if r["443"]]

    print("\n[3] 统计结果")
    print(f"扫描网段       : {network}")
    print(f"总主机数       : {total_hosts}")
    print(f"任意端口开放   : {len(open_any)} / {total_hosts} ({len(open_any) / total_hosts:.2%})")
    print(f"22 端口开放    : {len(open_22)} / {total_hosts} ({len(open_22) / total_hosts:.2%})")
    print(f"80 端口开放    : {len(open_80)} / {total_hosts} ({len(open_80) / total_hosts:.2%})")
    print(f"443 端口开放   : {len(open_443)} / {total_hosts} ({len(open_443) / total_hosts:.2%})")
    print(f"耗时           : {elapsed:.2f}s")

    open_ratio = len(open_any) / total_hosts

    print("\n[4] 粗略判断")

    if open_ratio >= 0.30:
        print("判断: 该 /24 大量主机开放服务，偏 IDC / 服务器段 / 企业服务网段。")
    elif open_ratio >= 0.12:
        print("判断: 该 /24 有较多开放服务，可能是企业/商宽/托管混合段。")
    elif len(open_22) >= 10:
        print("判断: 22 端口开放数量偏多，存在服务器段或管理网段特征。")
    elif len(open_80) + len(open_443) >= 20:
        print("判断: Web 服务数量偏多，可能不是普通住宅动态池。")
    else:
        print("判断: 该 /24 开放服务不算密集，未呈现明显机房服务段特征。")

    print("\n注意: 端口稀疏并不能直接证明是真家宽；端口密集则更偏服务器/企业/IDC。")


def save_csv(results, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ip", "port_22", "port_80", "port_443", "open_ports"])

        for r in sorted(results, key=lambda x: ipaddress.ip_address(x["ip"])):
            writer.writerow([
                r["ip"],
                int(r["22"]),
                int(r["80"]),
                int(r["443"]),
                ",".join(map(str, r["open_ports"]))
            ])

    print(f"\n结果已保存: {filename}")


def main():
    print("=== IP PTR + /24 端口密度检测 ===")
    ip = input("请输入 IP: ").strip()

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        print("输入的不是合法 IP")
        return

    ptr_lookup(ip)

    confirm = input("\n是否扫描该 IP 所在 /24 的 22/80/443？[y/N]: ").strip().lower()
    if confirm != "y":
        print("已取消扫描")
        return

    network, results, elapsed = scan_24(ip)
    analyze_results(network, results, elapsed)

    save = input("\n是否保存 CSV 结果？[y/N]: ").strip().lower()
    if save == "y":
        filename = f"scan_{network.network_address}_{network.prefixlen}.csv".replace("/", "_")
        save_csv(results, filename)


if __name__ == "__main__":
    main()
