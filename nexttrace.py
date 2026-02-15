#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
from typing import List, Tuple, Dict

options = [
    "0) IPV6",
    "1) CT",
    "2) CU",
    "3) CM",
    "4) Others",
    "5) SJW",
    "6) SHA",
    "7) CAN",
    "8) HK",
    "9) TW",
    "10) JP",
    "11) SG",
    "12) US",
    "13) EU",
    "14) AU",
    "15) TG",
]

TraceItem = Tuple[str, List[str]]

TRACES: Dict[int, List[TraceItem]] = {
    0: [
        ("CT-IPV6", ["nexttrace", "-MT", "dlied4.csy.tcdnos.com"]),
        ("CU-IPV6", ["nexttrace", "-MT", "ml-dlied4.bytes.tcdnos.com"]),
        ("CM-IPV6", ["nexttrace", "-MT", "875e1151af8aa9e3b793f51f6049996d.dlied1.cdntips.net"]),
    ],
    1: [
        ("CT-219.141.150.166", ["nexttrace", "-MT", "-p", "65499", "219.141.150.166"]),
        ("CT-27.185.201.1", ["nexttrace", "-MT", "-p", "65499", "27.185.201.1"]),
        ("CT-124.74.52.254", ["nexttrace", "-MT", "-p", "65499", "124.74.52.254"]),
        ("CT-61.150.151.122", ["nexttrace", "-MT", "-p", "65499", "61.150.151.122"]),
        ("CT-61.144.6.18", ["nexttrace", "-MT", "-p", "65499", "61.144.6.18"]),
    ],
    2: [
        ("CU-61.135.214.54", ["nexttrace", "-MT", "-p", "65499", "61.135.214.54"]),
        ("CU-61.240.159.62", ["nexttrace", "-MT", "-p", "65499", "61.240.159.62"]),
        ("CU-210.51.57.10", ["nexttrace", "-MT", "-p", "65499", "210.51.57.10"]),
        ("CU-58.20.176.94", ["nexttrace", "-MT", "-p", "65499", "58.20.176.94"]),
        ("CU-218.107.8.18", ["nexttrace", "-MT", "-p", "65499", "218.107.8.18"]),
    ],
    3: [
        ("CM-112.34.111.194", ["nexttrace", "-MT", "112.34.111.194"]),
        ("CM-111.62.68.17", ["nexttrace", "-MT", "111.62.68.17"]),
        ("CM-120.204.34.2", ["nexttrace", "-MT", "-p", "65499", "120.204.34.2"]),
        ("CM-111.8.9.73", ["nexttrace", "-MT", "111.8.9.73"]),
        ("CM-218.204.182.226", ["nexttrace", "-MT", "-p", "65499", "218.204.182.226"]),
    ],
    4: [
        ("CN2", ["nexttrace", "-MT", "58.32.4.1"]),
        ("9929", ["nexttrace", "-MT", "210.13.67.106"]),
        ("CMIN2", ["nexttrace", "-MT", "223.70.155.77"]),
        ("CBN", ["nexttrace", "-MT", "211.156.140.17"]),
        ("Cernet", ["nexttrace", "-M", "166.111.4.5"]),
        ("CSTNET", ["nexttrace", "-MT", "159.226.254.1"]),
        ("Alibaba-CAN", ["nexttrace", "-MT", "oss-cn-guangzhou.aliyuncs.com"]),
        ("AWS-PEK", ["nexttrace", "-MT", "52.80.5.207"]),
        ("AWS-Ningxia", ["nexttrace", "-MT", "52.83.214.0"]),
        ("Azure-SHA", ["nexttrace", "-MT", "42.159.128.11"]),
        ("Huawei-CAN", ["nexttrace", "-MT", "feitsui-can.obs.cn-south-1.myhuaweicloud.com"]),
        ("Tencent-CAN", ["nexttrace", "-MT", "cos.ap-guangzhou.myqcloud.com"]),
    ],
    5: [
        ("SJW-CT", ["nexttrace", "-MT", "-p", "65499", "27.185.201.1"]),
        ("SJW-CU", ["nexttrace", "-MT", "-p", "65499", "61.240.159.62"]),
        ("SJW-CM", ["nexttrace", "-MT", "111.62.68.17"]),
    ],
    6: [
        ("SHA-CT", ["nexttrace", "-MT", "-p", "65499", "124.74.52.254"]),
        ("SHA-CU", ["nexttrace", "-MT", "-p", "65499", "210.51.57.10"]),
        ("SHA-CM", ["nexttrace", "-MT", "-p", "65499", "120.204.34.2"]),
    ],
    7: [
        ("CAN-CT", ["nexttrace", "-MT", "-p", "65499", "61.144.6.18"]),
        ("CAN-CU", ["nexttrace", "-MT", "-p", "65499", "218.107.8.18"]),
        ("CAN-CM", ["nexttrace", "-MT", "-p", "65499", "218.204.182.226"]),
    ],
    8: [
        ("Akari-HKG", ["nexttrace", "-M", "143.14.86.11"]),
        ("Alibaba-HKG", ["nexttrace", "-MT", "oss-cn-hongkong.aliyuncs.com"]),
        ("Apernet-HKG", ["nexttrace", "-M", "23.247.139.10"]),
        ("Asymptote-HKG", ["nexttrace", "-M", "43.254.164.1"]),
        ("Beecloud-HKG", ["nexttrace", "-M", "203.168.224.1"]),
        ("BWH-HKG", ["nexttrace", "-M", "93.179.124.10"]),
        ("Cera-HKG", ["nexttrace", "-M", "156.251.180.1"]),
        ("CMHK-HKG", ["nexttrace", "-MT", "-p", "8080", "speedtestbb.hk.chinamobile.com"]),
        ("CTCSCI-HKG", ["nexttrace", "-MT", "-p", "8080", "speedtest.hk210.hkg.cn.ctcsci.com"]),
        ("Datacamp-HKG", ["nexttrace", "-MT4", "hkg.download.datapacket.com"]),
        ("Dmit-HKG", ["nexttrace", "-M", "154.3.33.110"]),
        ("Eons-HKG", ["nexttrace", "-M", "209.146.125.10"]),
        ("Gcore-HKG", ["nexttrace", "-M", "91.199.84.1"]),
        ("HGC-HKG", ["nexttrace", "-MT", "-p", "8080", "ookla-speedtest-central.hgconair.hgc.com.hk"]),
        ("HKBN-HKG", ["nexttrace", "-MT", "-p", "8080", "speedtest12.hkbn.net"]),
        ("HKT-HKG", ["nexttrace", "-MT", "-p", "8080", "suntechspeedtest.com"]),
        ("HostHatch-HKG", ["nexttrace", "-MT", "lg.hkg.hosthatch.com"]),
        ("Huawei-HKG", ["nexttrace", "-MT", "feitsui-hkg.obs.ap-southeast-1.myhuaweicloud.com"]),
        ("Hytron-HKG", ["nexttrace", "-M", "38.150.13.64"]),
        ("Jinx-HKG", ["nexttrace", "-M", "103.116.72.2"]),
        ("Kirino-HKG", ["nexttrace", "-M", "37.123.198.10"]),
        ("LANDUPS-HKG", ["nexttrace", "-M", "103.46.184.1"]),
        ("Misaka-HKG", ["nexttrace", "-MT4", "-p", "8080", "hk-hkg12.speed.misaka.one"]),
        ("Nearoute-HKG", ["nexttrace", "-MT4", "-p", "8080", "hk-bgp-speedtest.nearoute.io.prod.hosts.ooklaserver.net"]),
        ("Sakura-HKG", ["nexttrace", "-MT", "-p", "8080", "speedtest.hkg01.node.as9516.com"]),
        ("Sharon-HKG", ["nexttrace", "-M", "157.254.32.1"]),
        ("Skywolf-HKG", ["nexttrace", "-M", "103.213.4.13"]),
        ("Tencent-HKG", ["nexttrace", "-MT", "feitsui-hkg-1251417183.cos.ap-hongkong.myqcloud.com"]),
        ("WTT-HKG", ["nexttrace", "-M", "43.251.133.23"]),
        ("xTom-HKG", ["nexttrace", "-M", "157.119.103.1"]),
        ("XNNET-HKG", ["nexttrace", "-M", "43.254.164.1"]),
        ("Zenlayer-HKG", ["nexttrace", "-M", "156.59.103.1"]),
        ("AWS-HKG", ["nexttrace", "-MT", "ec2.ap-east-1.amazonaws.com"]),
        ("Azure-HKG", ["nexttrace", "-MT", "q9eastasia.blob.core.windows.net"]),
        ("GCP-HKG", ["nexttrace", "-M", "hk.starxn.ggff.net"]),
    ],
    9: [
        ("GCP-TW", ["nexttrace", "-M", "35.229.225.8"]),
        ("HiNet-TPE", ["nexttrace", "-M", "hinet.net"]),
    ],
    10: [
        ("Akamai-NRT", ["nexttrace", "-M4", "speedtest.tokyo2.linode.com"]),
        ("Datacamp-NRT", ["nexttrace", "-M4", "tyo.download.datapacket.com"]),
        ("Dmit-NRT", ["nexttrace", "-M", "45.88.193.5"]),
        ("Eons-NRT", ["nexttrace", "-M", "103.168.154.1"]),
        ("Jinx-NRT", ["nexttrace", "-M", "185.188.5.1"]),
        ("Kddi-NRT", ["nexttrace", "-M", "106.180.224.1"]),
        ("Kirino-NRT", ["nexttrace", "-M", "212.107.30.1"]),
        ("Misaka-NRT", ["nexttrace", "-M", "103.170.232.48"]),
        ("Nearoute-NRT", ["nexttrace", "-M", "89.116.88.18"]),
        ("NeroCloud-NRT", ["nexttrace", "-M", "103.90.136.3"]),
        ("NttPC-NRT", ["nexttrace", "-M", "140.227.118.6"]),
        ("Sharon-NRT", ["nexttrace", "-M", "157.254.198.1"]),
        ("Softbank-NRT", ["nexttrace", "-M", "126.40.32.184"]),
        ("Vultr-NRT", ["nexttrace", "-M4", "hnd-jp-ping.vultr.com"]),
        ("xTom-NRT", ["nexttrace", "-M", "149.62.44.1"]),
        ("AWS-NRT", ["nexttrace", "-M", "ec2.ap-northeast-1.amazonaws.com"]),
        ("Azure-NRT", ["nexttrace", "-M", "s8japaneast.blob.core.windows.net"]),
        ("GCP-NRT", ["nexttrace", "-M", "34.146.177.11"]),
    ],
    11: [
        ("Akamai-SIN", ["nexttrace", "-M", "-4", "speedtest.singapore.linode.com"]),
        ("Akari-SIN", ["nexttrace", "-M", "103.84.216.2"]),
        ("Datacamp-SIN", ["nexttrace", "-M4", "sgp.download.datapacket.com"]),
        ("DigitalOcean-SIN", ["nexttrace", "-M", "159.89.192.4"]),
        ("Eons-SIN", ["nexttrace", "-M", "38.150.8.1"]),
        ("Huawei-SIN", ["nexttrace", "-M", "159.138.84.2"]),
        ("Kirino-SIN", ["nexttrace", "-M", "103.142.140.1"]),
        ("Misaka-SIN", ["nexttrace", "-M", "194.156.163.2"]),
        ("Nearoute-SIN", ["nexttrace", "-M", "185.151.146.2"]),
        ("NeroCloud-SIN", ["nexttrace", "-M", "178.173.235.128"]),
        ("OVH-SIN", ["nexttrace", "-M4", "sgp.proof.ovh.net"]),
        ("SpeedyPage-SIN", ["nexttrace", "-M4", "sg.lg.speedypage.com"]),
        ("Vultr-SIN", ["nexttrace", "-M4", "sgp-ping.vultr.com"]),
        ("xTom-SIN", ["nexttrace", "-M", "185.194.54.1"]),
        ("AWS-SIN", ["nexttrace", "-M", "ec2.ap-southeast-1.amazonaws.com"]),
        ("Azure-SIN", ["nexttrace", "-M", "s8southeastasia.blob.core.windows.net"]),
        ("GCP-SIN", ["nexttrace", "-M", "34.87.56.6"]),
    ],
    12: [
        ("Akamai-LAX", ["nexttrace", "-M4", "speedtest.los-angeles.linode.com"]),
        ("Clouvider-LAX", ["nexttrace", "-M", "77.247.126.11"]),
        ("Datacamp-LAX", ["nexttrace", "-M4", "lax.download.datapacket.com"]),
        ("FranTech-LAS", ["nexttrace", "-M4", "speedtest.lv.buyvm.net"]),
        ("Hetzner-HIL", ["nexttrace", "-M4", "hil-speed.hetzner.com"]),
        ("Hostodo-MIA", ["nexttrace", "-M4", "mia.hostodo.com"]),
        ("Misaka-SEA", ["nexttrace", "-MT4", "-p", "8080", "us-sea02.speed.misaka.one"]),
        ("Comcast-SEA", ["nexttrace", "-MT4", "-p", "8080", "stosat-rvlt-01.sys.comcast.net.prod.hosts.ooklaserver.net"]),
        ("Ziply-SEA", ["nexttrace", "-MT4", "-p", "8080", "speedtest1-sttlwawb.as20055.net"]),
        ("OVH-HIL", ["nexttrace", "-M4", "hil.proof.ovh.us"]),
        ("Vultr-LAX", ["nexttrace", "-M4", "lax-ca-us-ping.vultr.com"]),
        ("AWS-OR", ["nexttrace", "-M", "ec2.us-west-2.amazonaws.com"]),
        ("GCP-OR", ["nexttrace", "-M", "35.247.10.7"]),
    ],
    13: [
        ("Akamai-FRA", ["nexttrace", "-M4", "speedtest.frankfurt.linode.com"]),
        ("Clouvider-LHR", ["nexttrace", "-M", "185.42.223.2"]),
        ("Datacamp-PAR", ["nexttrace", "-M4", "par.download.datapacket.com"]),
        ("FranTech-LUX", ["nexttrace", "-M4", "speedtest.lu.buyvm.net"]),
        ("Hetzner-NUE", ["nexttrace", "-M4", "nbg1-speed.hetzner.com"]),
        ("Hivelocity-FRA", ["nexttrace", "-M4", "speedtest.fra1.hivelocity.net"]),
        ("Kirino-FRA", ["nexttrace", "-M", "38.59.228.10"]),
        ("Misaka-BER", ["nexttrace", "-M", "45.142.247.4"]),
        ("Misaka-MOW", ["nexttrace", "-M", "45.142.246.240"]),
        ("Netcup-NUE", ["nexttrace", "-M4", "lookingglass.netcup.net"]),
        ("OVH-GRA", ["nexttrace", "-M4", "gra.proof.ovh.net"]),
        ("Vultr-FRA", ["nexttrace", "-M4", "fra-de-ping.vultr.com"]),
        ("AWS-FRA", ["nexttrace", "-M", "ec2.eu-central-1.amazonaws.com"]),
        ("GCP-LON", ["nexttrace", "-M", "34.89.121.0"]),
    ],
    14: [
        ("Akamai-SDY", ["nexttrace", "-M4", "speedtest.syd1.linode.com"]),
        ("GCP-SDY", ["nexttrace", "-M", "34.116.127.76"]),
        ("AWS-SDY", ["nexttrace", "-M", "ec2.ap-southeast-2.amazonaws.com"]),
    ],
    15: [
        ("Telegram-SG", ["nexttrace", "-M", "91.108.56.100"]),
        ("Telegram-NL", ["nexttrace", "-M", "149.154.167.100"]),
        ("Telegram-US", ["nexttrace", "-M", "149.154.175.100"]),
    ],
}


def run_nexttrace(label: str, cmd: List[str]) -> int:
    """运行 nexttrace，并在执行开始前显示备注（label），分割线更明显。"""
    sep = "═" * 92
    print(f"\n{sep}")
    print(f"▶ 备注: {label}")
    print("$ " + " ".join(cmd))
    print(sep)

    try:
        # 不捕获输出，让 nexttrace 直接打印到终端
        p = subprocess.run(cmd)
        rc = p.returncode
    except FileNotFoundError:
        print("\n[错误] 未找到 nexttrace 命令：请确认已安装并已加入 PATH\n")
        return 127

    # 如果 nexttrace 因为 SIGINT(CTRL+C) 退出（某些环境下 Python 不一定抛 KeyboardInterrupt），也直接终止脚本
    if rc == 130:
        raise KeyboardInterrupt

    status = "OK" if rc == 0 else f"EXIT={rc}"
    # 结束后也给一个明显的结束分隔（不再把备注放在最后，而是强调状态）
    print(f"{sep}")
    print(f"■ 完成: {label}  ({status})")
    print(sep)
    print("")
    return rc


def main() -> int:
    num_columns = 3
    num_options = len(options)
    num_rows = (num_options + num_columns - 1) // num_columns

    # 让三列对齐：用“显示宽度”补空格（比 \t 更稳定，10) 这类两位数也能对齐）
    try:
        from wcwidth import wcswidth  # pip 包 wcwidth
    except Exception:
        import unicodedata
        def wcswidth(s: str) -> int:
            w = 0
            for ch in s:
                w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
            return w

    def pad_cell(s: str, width: int) -> str:
        return s + " " * max(0, width - wcswidth(s))

    col_width = max(wcswidth(o) for o in options) + 4  # 每列额外留点空隙
    formatted_options = ""
    for r in range(num_rows):
        line = ""
        for c in range(num_columns):
            idx = r + c * num_rows
            if idx < num_options:
                line += pad_cell(options[idx], col_width)
        formatted_options += line.rstrip() + "\n"

    print("请选择:")
    print(formatted_options)

    try:
        choice = int(input("输入选择: ").strip())
    except ValueError:
        print("无效输入，请输入一个数字。")
        return 2
    except KeyboardInterrupt:
        print("\n程序已被中断。")
        return 130

    if choice not in range(len(options)):
        print("无效输入，请重试！")
        return 2

    sep = "═" * 92
    print(f"\n{sep}")
    print(f"◆ 选项: {options[choice]}")
    print(f"{sep}\n")
    items = TRACES.get(choice, [])
    if not items:
        print("该选项暂无检测项。\n")
        return 0

    done_labels: List[str] = []
    last_rc = 0
    try:
        for label, cmd in items:
            last_rc = run_nexttrace(label, cmd)
            done_labels.append(label)
            # 如果你希望某条失败就停止，把下面两行取消注释即可：
            # if last_rc != 0:
            #     break
    except KeyboardInterrupt:
        print("\n[中断] 检测已被终止，退出脚本。")
        if done_labels:
            print("已完成: " + ", ".join(done_labels))
        print("")
        return 130

    # 汇总：一次性列出本次执行的所有备注（每个选项都会显示，不限 HK）
    sep2 = "═" * 92
    print(sep2)
    print("◆ 本次检测备注汇总")
    print(", ".join(done_labels))
    print(sep2 + "\n")
    return last_rc


if __name__ == "__main__":
    sys.exit(main())
