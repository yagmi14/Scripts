import os
import subprocess
import datetime
import sys
import re

# 获取当前时间戳
now = datetime.datetime.now()
timestamp = now.strftime('%Y%m%d%H%M%S')

def generate_route_config(route_config_content, port):
    route_config_path = f"/usr/local/etc/sb3/conf/route_{port}.json"
    with open(route_config_path, "w") as route_config:
        route_config.write(route_config_content)
    return route_config_path

def generate_inbounds_config(inbounds_config_content, port):
    inbounds_config_path = f"/usr/local/etc/sb3/conf/inbounds_{port}.json"
    with open(inbounds_config_path, "w") as inbounds_config:
        inbounds_config.write(inbounds_config_content)
    return inbounds_config_path

def generate_outbounds_config(outbounds_config_content, tag_out):
    outbounds_config_path = f"/usr/local/etc/sb3/conf/outbounds_{tag_out}.json"
    with open(outbounds_config_path, "w") as outbounds_config:
        outbounds_config.write(outbounds_config_content)
    return outbounds_config_path

def restart_service():
    subprocess.run(["systemctl", "restart", "sb3"])
    
def status_service():
    subprocess.run(["systemctl", "status", "sb3"])

def list_outbound_files(directory_path):
    """
    列出指定目录下所有以 'outbounds_' 开头并且以 '.json' 结尾的文件。
    参数:
        directory_path: 指定的目录路径。
    返回:
        file_dict: 一个包含序号和文件标识的字典。
    """
    # 获取目录下所有文件名
    files = os.listdir(directory_path)
    # 过滤出以 'outbounds_' 开头并且以 '.json' 结尾的文件
    outbound_files = [file for file in files if file.startswith('outbounds_') and file.endswith('.json')]
    # 对文件名进行排序，确保序号的连续性
    outbound_files.sort()
    # 初始化一个空字典来存储序号和文件标识
    file_dict = {index: filename.replace('outbounds_', '').replace('.json', '') for index, filename in enumerate(outbound_files, start=1)}
    # 返回字典
    return file_dict

def find_next_available_port(directory):
    """
    在指定目录中查找以'sb_'开头并以'.json'结尾的文件名中的最大数字，
    将这个数字加1后返回，作为下一个可用的端口号。
    如果没有找到符合条件的文件，则返回默认的端口号43001。
    
    参数:
    directory (str): 要搜索的目录路径。

    返回:
    int: 下一个可用的端口号，如果没有找到符合条件的文件，则返回43001。
    """
    max_number = -1
    for filename in os.listdir(directory):
        if filename.startswith('inbounds_') and filename.endswith('.json'):
            number = re.findall(r'inbounds_(\d+).json', filename)
            if number:
                max_number = max(max_number, int(number[0]))
    return max_number + 1 if max_number != -1 else 43001

def main():
    while True:
        try:
            print("Please select:")
            print("1) inbounds")
            print("2) outbounds")
            print("3) inbounds_rm")
            print("4) outbounds_rm")

            choice = input("Please select:")                
        
            if choice == "" or choice.isspace():
                choice = "1"

            if choice == "1":
                option_1()
                continue

            elif choice == "2":
                option_2()

            elif choice == "3":
                option_3()

            elif choice == "4":
                option_4() 
    
        except KeyboardInterrupt:
            print("\nThe program has been interrupted.")
            break

def option_1():
    try:
        print("inbounds")

        # 使用示例
        directory = '/usr/local/etc/sb3/conf/'
        max_num = find_next_available_port(directory)
        
        port = input("port: ")
        if port == "":                    
            port = f"{max_num}"
        print(f'port: {port}')

        # 使用函数
        directory_path = '/usr/local/etc/sb3/conf/'
        file_dict = list_outbound_files(directory_path)
        # 打印序号和文件名
        for index, filename in file_dict.items():
            print(f"{index}) {filename}")
    
        choice = input("请选择: ")

        # 如果用户选择了序号
        if int(choice) in file_dict:
            # 从字典中获取对应的文件名
            tag_out = file_dict[int(choice)]
            # 打印结果
            print(f"Selected file: {tag_out}")
        else:
            print("您输入的序号不正确，请重新输入。")
            
        print("1) Shadowsocks")
        print("2) VLESS-Vision-REALITY")        
        print("3) VLESS-gRPC-REALITY")
        print("4) VLESS-HTTP2-REALITY")
        print("5) Hysteria2")
        print("6) VLESS-Vision-REALITY_2")

        choice = input("Please select:")

        if choice == "1":
            print("Shadowsocks")
            
            tag_in = "shadowsocks-in"
            tag_in_port = f"{tag_in}_{port}"
            
            print("Please select the method:")
            print("1. 2022-blake3-aes-256-gcm")
            print("2. aes-256-gcm")

            method = input("method: ")
            if method == "":
                method = "2022-blake3-aes-256-gcm"
            elif method == "1":
                method = "2022-blake3-aes-256-gcm"
            elif method == "2":
                method = "aes-256-gcm"
            else:
                print("Incorrect input, please re-enter.")

            print("Your selected method is:", method)

            route_config_content = ('{"route":{"rules":[{"inbound":"' + tag_in_port + '","outbound":"' + tag_out + '"}]}}')
            inbounds_config_content = ('{"inbounds":[{"type":"shadowsocks","tag":"' + tag_in + '","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4=","multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')

            route_config_path = generate_route_config(route_config_content, port)
            inbounds_config_path = generate_inbounds_config(inbounds_config_content, port)
                
            restart_service()
            
            status_service()
            
        elif choice == "2":
            print("VLESS-Vision-REALITY")
            
            tag_in = "vless-in"
            tag_in_port = f"{tag_in}_{port}"            
            
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"
            print(domain)

            route_config_content = ('{"route":{"rules":[{"inbound":"' + tag_in_port + '","outbound":"' + tag_out + '"}]}}')
            inbounds_config_content = ('{"inbounds":[{"type":"vless","tag":"' + tag_in_port + '","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98","flow":"xtls-rprx-vision"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')

            route_config_path = generate_route_config(route_config_content, port)
            inbounds_config_path = generate_inbounds_config(inbounds_config_content, port)
                
            restart_service()
            
            status_service()            
        
        elif choice == "3":
            print("VLESS-gRPC-REALITY")

            tag_in = "vless-in"
            tag_in_port = f"{tag_in}_{port}"            
            
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"
            print(domain)

            route_config_content = ('{"route":{"rules":[{"inbound":"' + tag_in_port + '","outbound":"' + tag_out + '"}]}}')
            inbounds_config_content = ('{"inbounds":[{"type":"vless","tag":"' + tag_in_port + '","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"grpc","service_name":"rWZXzPnJ"},"multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')

            route_config_path = generate_route_config(route_config_content, port)
            inbounds_config_path = generate_inbounds_config(inbounds_config_content, port)
            
            restart_service()
                
            status_service()
            
        elif choice == "4":
            print("VLESS-HTTP2-REALITY")

            tag_in = "vless-in"
            tag_in_port = f"{tag_in}_{port}"            
            
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"
            print(domain)

            route_config_content = ('{"route":{"rules":[{"inbound":"' + tag_in_port + '","outbound":"' + tag_out + '"}]}}')              
            inbounds_config_content = ('{"inbounds":[{"type":"vless","tag":"' + tag_in_port + '","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"http"},"multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')

            route_config_path = generate_route_config(route_config_content, port)
            inbounds_config_path = generate_inbounds_config(inbounds_config_content, port)
            
            restart_service()
                
            status_service()

        elif choice == "5":
            print("Hysteria2")

            tag_in = "hysteria2-in"
            tag_in_port = f"{tag_in}_{port}"

            route_config_content = ('{"route":{"rules":[{"inbound":"' + tag_in_port + '","outbound":"' + tag_out + '"}]}}')               
            inbounds_config_content = ('{"inbounds":[{"type":"hysteria2","sniff":true,"sniff_override_destination":true,"tag":"' + tag_in_port + '","listen":"::","listen_port":' + port + ',"users":[{"password":"de0e3ecb-2349-4f17-b4a6-b044a895160c"}],"ignore_client_bandwidth":false,"tls":{"enabled":true,"server_name":"","alpn":["h3"],"min_version":"1.3","max_version":"1.3","certificate_path":"/etc/sing-box/cert/cert.pem","key_path":"/etc/sing-box/cert/private.key"}}]}')

            route_config_path = generate_route_config(route_config_content, port)
            inbounds_config_path = generate_inbounds_config(inbounds_config_content, port)
            
            restart_service()
                
            status_service()

        elif choice == "6":
            print("VLESS-Vision-REALITY_2")
            
            tag_in = "vless-in"
            tag_in_port = f"{tag_in}_{port}"            
            
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"
            print(domain)

            route_config_content = ('{"route":{"rules":[{"inbound":"' + tag_in_port + '","outbound":"' + tag_out + '"}]}}')
            inbounds_config_content = ('{"inbounds":[{"type":"vless","tag":"' + tag_in_port + '","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98","flow":"xtls-rprx-vision"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}}}]}')

            route_config_path = generate_route_config(route_config_content, port)
            inbounds_config_path = generate_inbounds_config(inbounds_config_content, port)
                
            restart_service()
            
            status_service()    

    except KeyboardInterrupt:
        print("\nThe program has been interrupted.")
    
    sys.exit()

def option_2():
    try:
        print("outbounds")

        # 使用函数
        directory_path = '/usr/local/etc/sb3/conf/'
        file_dict = list_outbound_files(directory_path)
        # 打印序号和文件名
        for index, filename in file_dict.items():
            print(f"{index}) {filename}")

        tag_out = input("outbounds tag: ")
        print(tag_out)

        ip = input("remote ip: ")
        print(ip)

        port = input("remote port: ")
        if port == "":
            port = "40001"
        print(port)

        print("Please select the method:")
        print("1. 2022-blake3-aes-256-gcm")
        print("2. aes-256-gcm")
        print("3. aes-128-gcm")

        method = input("method: ")
        if method == "":
            method = "2022-blake3-aes-256-gcm"
        elif method == "1":
            method = "2022-blake3-aes-256-gcm"
        elif method == "2":
            method = "aes-256-gcm"
        elif method == "3":
            method = "aes-128-gcm"
        else:
            print("Incorrect input, please re-enter.")

        print("Your selected method is:", method)

        password = input("password: ")
        if password == "":
            password = "W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="
        print(password)

        outbounds_config_content = ('{"outbounds":[{"type":"shadowsocks","tag":"' + tag_out + '","server":"' + ip + '","server_port":' + port + ',"method":"' + method + '","password":"' + password + '","multiplex":{"enabled":true,"protocol":"h2mux","max_connections":8,"min_streams":16,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')            
                  
        outbounds_config_path = generate_outbounds_config(outbounds_config_content, tag_out)
            
        restart_service()
            
        status_service()

    except KeyboardInterrupt:
        print("\nThe program has been interrupted.")
    
    sys.exit()

def option_3():
    try:
        print("inbounds_rm")

        port = input("listen port: ")
        print(port)

        route_config = f"/usr/local/etc/sb3/conf/route_{port}.json"
        inbounds_config = f"/usr/local/etc/sb3/conf/inbounds_{port}.json"
            
        subprocess.run(["rm", "-f", route_config], check=True)
        subprocess.run(["rm", "-f", inbounds_config], check=True)
        print(f"已删除route_{port}.json")
        print(f"已删除inbounds_{port}.json")
            
        restart_service()
            
        status_service()

    except KeyboardInterrupt:
        print("\nThe program has been interrupted.")
    
    sys.exit()  # 添加这行代码来退出程序

def option_4():
    try:
        print("outbounds_rm")

        # 使用函数
        directory_path = '/usr/local/etc/sb3/conf/'
        file_dict = list_outbound_files(directory_path)
        # 打印序号和文件名
        for index, filename in file_dict.items():
            print(f"{index}) {filename}")

        choice = input("请选择: ")

        # 如果用户选择了序号
        if int(choice) in file_dict:
            # 从字典中获取对应的文件名
            tag_out = file_dict[int(choice)]
            # 打印结果
            print(f"Selected file: {tag_out}")
        else:
            print("您输入的序号不正确，请重新输入。")

        outbounds_config = f"/usr/local/etc/sb3/conf/outbounds_{tag_out}.json"
            
        subprocess.run(["rm", "-f", outbounds_config], check=True)
        print(f"已删除outbounds_{tag_out}.json")

        restart_service()
            
        status_service()

    except KeyboardInterrupt:
        print("\nThe program has been interrupted.")

    sys.exit()

if __name__ == "__main__":
    main()
