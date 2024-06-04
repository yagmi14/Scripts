import os
import subprocess

def generate_config_file(config_content, port):
    config_path = f"/usr/local/etc/sb3/conf/sb_{port}.json"
    with open(config_path, "w") as config_file:
        config_file.write(config_content)
    return config_path

def restart_service():
    subprocess.run(["systemctl", "restart", "sb3"])
    
def status_service():
    subprocess.run(["systemctl", "status", "sb3"])

def main():
    try:
        print("Please select:")
        print("1) Shadowsocks+Shadowsocks")
        print("2) VLESS-Vision-REALITY+Shadowsocks")        
        print("3) VLESS-gRPC-REALITY+Shadowsocks")
        print("4) VLESS-HTTP2-REALITY+Shadowsocks")

        choice = input("Please select:")                
        
        if choice == "" or choice.isspace():
            choice = "2"
            
        if choice == "2":
            print("VLESS-Vision-REALITY+Shadowsocks")
            
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

            config_content = ('{"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98","flow":"xtls-rprx-vision"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}],"outbounds":[{"type":"shadowsocks","tag":"shadowsocks-out","server":"' + ip + '","server_port":' + port_2 + ',"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}]}')

            config_path = generate_config_file(config_content, port)
            
            restart_service()
            
            status_service()            
        
        if choice == "3":
            print("VLESS-gRPC-REALITY+Shadowsocks")
            
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

            config_content = ('{"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"grpc","service_name":"rWZXzPnJ"},"multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}],"outbounds":[{"type":"shadowsocks","tag":"shadowsocks-out","server":"' + ip + '","server_port":' + port_2 + ',"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}]}')

            config_path = generate_config_file(config_content, port)
            
            restart_service()
            
            status_service()
            
        if choice == "4":
            print("VLESS-HTTP2-REALITY+Shadowsocks")
            
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

            config_content = ('{"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"http"},"multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}],"outbounds":[{"type":"shadowsocks","tag":"shadowsocks-out","server":"' + ip + '","server_port":' + port_2 + ',"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}]}')

            config_path = generate_config_file(config_content, port)
            
            restart_service()
            
            status_service()            
    
    except KeyboardInterrupt:
        print("\nThe program has been interrupted.")

if __name__ == "__main__":
    main()
