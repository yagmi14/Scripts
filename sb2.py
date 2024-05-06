import os
import subprocess

def generate_config_file(config_content, port):
    config_path = f"/etc/sing-box/conf/sb{port}.json"
    with open(config_path, "w") as config_file:
        config_file.write(config_content)
    return config_path

def restart_service():
    subprocess.run(["systemctl", "restart", "sing-box"])
    
def status_service():
    subprocess.run(["systemctl", "status", "sing-box"])

def main():
    try:
        print("Please select:")
        print("1) vless-xtls-grpc-reality")
        print("2) vless-xtls-vision-reality")
        print("3) shadowsocks")
        print("4) ShadowTLS v3")
        print("5) grpc-reality+shadowsocks")
        print("6) tcp-reality+shadowsocks")
        print("7) shadowsocks+shadowsocks")

        choice = input("Please select:")
        
        if choice == "" or choice.isspace():
            choice = "3"
        
        if choice == "3":
            print("shadowsocks")
            port = input("listening port: ")
            if port == "":
                port = "40001"

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
            
            config_content = ('{"inbounds":[{"type":"shadowsocks","tag":"shadowsocks-in","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4=","multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')
            
            config_path = generate_config_file(config_content, port)
            
            restart_service()
            
            status_service()
        
        if choice == "4":
            print("ShadowTLS")
            port = input("listening port: ")
            if port == "":
                port = "40003"
            
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"

            print(domain)

            config_content = ('{"inbounds":[{"type":"shadowtls","sniff":true,"sniff_override_destination":true,"tag":"test","listen":"::","listen_port": ' + port + ',"detour":"shadowtls-in","version":3,"users":[{"password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"handshake":{"server":"' + domain + '","server_port":443},"strict_mode":true},{"type":"shadowsocks","tag":"shadowtls-in","listen":"127.0.0.1","network":"tcp","method":"2022-blake3-aes-256-gcm","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4=","multiplex":{"enabled":true,"padding":true,"brutal":{"enabled":true,"up_mbps":1000,"down_mbps":1000}}}]}')
            
            config_path = generate_config_file(config_content, port)
            
            restart_service()
            
            status_service()
            
    except KeyboardInterrupt:
        print("\nThe program has been interrupted.")

if __name__ == "__main__":
    main()