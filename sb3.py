import os
import subprocess
import datetime

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

def generate_outbounds_config(outbounds_config_content, tag):
    config_path = f"/usr/local/etc/sb3/conf/outbounds_{tag}.json"
    with open(config_path, "w") as config_file:
        config_file.write(outbounds_config_content)
    return config_path

def restart_service():
    subprocess.run(["systemctl", "restart", "sb3"])
    
def status_service():
    subprocess.run(["systemctl", "status", "sb3"])

def main():
    try:
        print("Please select:")
        print("1) Shadowsocks+Shadowsocks")
        print("2) VLESS-Vision-REALITY")        
        print("3) VLESS-gRPC-REALITY+Shadowsocks")
        print("4) VLESS-HTTP2-REALITY+Shadowsocks")
        print("5) Hysteria2+Shadowsocks")
        print("11) Shadowsocks")

        choice = input("Please select:")                
        
        if choice == "" or choice.isspace():
            choice = "2"
            
        if choice == "2":
            print("VLESS-Vision-REALITY")
            
            port = input("listening port: ")
            print(port)

            tag_in = "vless-in"
            tag_in_port = f"{tag_in}_{port}"            
            
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"
            print(domain)

            # 指定目录路径
            directory_path = '/usr/local/etc/sb3/conf/'
            # 获取目录下所有文件名
            files = os.listdir(directory_path)
            # 过滤出以 'outbounds_' 开头并且以 '.json' 结尾的文件
            outbound_files = [file for file in files if file.startswith('outbounds_') and file.endswith('.json')]
            # 对文件名进行排序，确保序号的连续性
            outbound_files.sort()
            # 初始化一个空字典来存储序号和文件标识
            file_dict = {index: filename for index, filename in enumerate(outbound_files, start=1)}
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

                route_config_content = ('{"route":{"rules":[{"inbound":"' + tag_in_port + '","outbound":"' + tag_out + '"}]}}')
                inbounds_config_content = ('{"inbounds":[{"type":"vless","tag":"' + tag_in_port + '","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98","flow":"xtls-rprx-vision"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')

                route_config_path = generate_route_config(route_config_content, port)
                inbounds_config_path = generate_inbounds_config(inbounds_config_content, port)
                
                restart_service()
            
                status_service()            
        
        if choice == "3":
            print("VLESS-gRPC-REALITY+Shadowsocks")

            tag_in = "vless-in"
            tag_in_time = f"{tag_in}_{timestamp}"
            tag_out = "ss-out"
            tag_out_time = f"{tag_out}_{timestamp}"
            
            port = input("listening port: ")
            print(port)
            
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"
            print(domain)
            
            ip = input("remote ip: ")
            print(ip)
            
            port_2 = input("remote port: ")            
            if port_2 == "":
                port_2 = "40001"
            print(port_2)
            
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
            print(method)

            config_content = ('{"inbounds":[{"type":"vless","tag":"' + tag_in_time + '","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"grpc","service_name":"rWZXzPnJ"},"multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}],"outbounds":[{"type":"shadowsocks","tag":"' + tag_out_time + '","server":"' + ip + '","server_port":' + port_2 + ',"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4=","multiplex":{"enabled":true,"protocol":"h2mux","max_connections":8,"min_streams":16,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')

            config_path = generate_config_file(config_content, port)
            
            restart_service()
            
            status_service()
            
        if choice == "4":
            print("VLESS-HTTP2-REALITY+Shadowsocks")

            tag_in = "vless-in"
            tag_in_time = f"{tag_in}_{timestamp}"
            tag_out = "ss-out"
            tag_out_time = f"{tag_out}_{timestamp}"
            
            port = input("listening port: ")
            print(port)
            
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"
            print(domain)
            
            ip = input("remote ip: ")
            print(ip)
            
            port_2 = input("remote port: ")            
            if port_2 == "":
                port_2 = "40001"
            print(port_2)
            
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
            print(method)

            config_content = ('{"inbounds":[{"type":"vless","tag":"' + tag_in_time + '","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"http"},"multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}],"outbounds":[{"type":"shadowsocks","tag":"' + tag_out_time + '","server":"' + ip + '","server_port":' + port_2 + ',"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4=","multiplex":{"enabled":true,"protocol":"h2mux","max_connections":8,"min_streams":16,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')

            config_path = generate_config_file(config_content, port)
            
            restart_service()
            
            status_service()

        if choice == "5":
            print("Hysteria2+Shadowsocks")

            tag_in = "hysteria2-in"
            tag_in_time = f"{tag_in}_{timestamp}"
            tag_out = "ss-out"
            tag_out_time = f"{tag_out}_{timestamp}"
            
            port = input("listening port: ")
            print(port)         
            
            ip = input("remote ip: ")
            print(ip)
            
            port_2 = input("remote port: ")            
            if port_2 == "":
                port_2 = "40001"
            print(port_2)
            
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
            print(method)

            config_content = ('{"inbounds":[{"type":"hysteria2","sniff":true,"sniff_override_destination":true,"tag":"' + tag_in_time + '","listen":"::","listen_port":' + port + ',"users":[{"password":"de0e3ecb-2349-4f17-b4a6-b044a895160c"}],"ignore_client_bandwidth":false,"tls":{"enabled":true,"server_name":"","alpn":["h3"],"min_version":"1.3","max_version":"1.3","certificate_path":"/etc/sing-box/cert/cert.pem","key_path":"/etc/sing-box/cert/private.key"}}],"outbounds":[{"type":"shadowsocks","tag":"' + tag_out_time + '","server":"' + ip + '","server_port":' + port_2 + ',"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4=","multiplex":{"enabled":true,"protocol":"h2mux","max_connections":8,"min_streams":16,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')

            config_path = generate_config_file(config_content, port)
            
            restart_service()
            
            status_service()    
    
    except KeyboardInterrupt:
        print("\nThe program has been interrupted.")

if __name__ == "__main__":
    main()
