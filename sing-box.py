import os
import subprocess

def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"{folder_path} created successfully")
    else:
        print(f"{folder_path} already exists")

def generate_config_file(folder_path, config_content):
    config_path = os.path.join(folder_path, "config.json")
    with open(config_path, "w") as config_file:
        config_file.write(config_content)
    return config_path

def start_service(service_name):
    subprocess.run(["systemctl", "start", service_name])

def stop_service(service_name):
    subprocess.run(["systemctl", "stop", service_name])

def restart_service(service_name):
    subprocess.run(["systemctl", "restart", service_name])

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

        if choice == "1":
            print("vless-xtls-grpc-reality")
            port = input("listening port: ")
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"

            print(domain)

            service_file = f"/etc/systemd/system/sb{port}.service"
            if os.path.exists(service_file):
                print(f"{service_file} exists.")
                stop_service(f"sb{port}")
            else:
                print(f"{service_file} does not exist.")

            folder = f"/usr/local/etc/sb{port}"
            create_folder(folder)

            config_content = ('{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"grpc","service_name":"rWZXzPnJ"}}],"outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}')

            config_path = generate_config_file(folder, config_content)
            if os.path.exists(service_file):
                start_service(f"sb{port}")
            else:
                subprocess.run(["/usr/bin/sing-box", "run", "-c", f"{config_path}"])

        elif choice == "2":
            print("vless-xtls-vision-reality")
            port = input("listening port: ")
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"

            print(domain)

            service_file = f"/etc/systemd/system/sb{port}.service"
            if os.path.exists(service_file):
                print(f"{service_file} exists.")
                stop_service(f"sb{port}")
            else:
                print(f"{service_file} does not exist.")

            folder = f"/usr/local/etc/sb{port}"
            create_folder(folder)

            config_content = ('{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98","flow":"xtls-rprx-vision"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}}}],"outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}')

            config_path = generate_config_file(folder, config_content)
            if os.path.exists(service_file):
                start_service(f"sb{port}")
            else:
                subprocess.run(["/usr/bin/sing-box", "run", "-c", f"{config_path}"])

        elif choice == "3":
            print("shadowsocks")
            port = input("listening port: ")

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

            service_file = f"/etc/systemd/system/sb{port}.service"
            if os.path.exists(service_file):
                print(f"{service_file} exists.")
                stop_service(f"sb{port}")
            else:
                print(f"{service_file} does not exist.")

            folder = f"/usr/local/etc/sb{port}"
            create_folder(folder)

            config_content = ('{"log":{"level":"info","timestamp":true},"inbounds":[{"type":"shadowsocks","tag":"shadowsocks-in","listen":"::","listen_port":' + port + ',"sniff":true,"sniff_override_destination":true,"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"outbounds":[{"type":"direct","tag":"direct"}]}')

            config_path = generate_config_file(folder, config_content)
            if os.path.exists(service_file):
                start_service(f"sb{port}")
            else:
                subprocess.run(["/usr/bin/sing-box", "run", "-c", f"{config_path}"])

        elif choice == "4":
            print("ShadowTLS v3")
            port = input("listening port: ")
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"

            print(domain)

            service_file = f"/etc/systemd/system/sb{port}.service"
            if os.path.exists(service_file):
                print(f"{service_file} exists.")
                stop_service(f"sb{port}")
            else:
                print(f"{service_file} does not exist.")

            folder = f"/usr/local/etc/sb{port}"
            create_folder(folder)

            config_content = ('{"log":{"level":"info","timestamp":true},"route":{"rules":[{"geosite":"cn","geoip":"cn","outbound":"direct"},{"geosite":"category-ads-all","outbound":"block"}]},"inbounds":[{"type":"shadowtls","tag":"st-in","listen":"::","listen_port":' + port + ',"version":3,"users":[{"name":"yagmi14","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"handshake":{"server":"' + domain + '","server_port":443},"strict_mode":true,"detour":"ss-in"},{"type":"shadowsocks","tag":"ss-in","listen":"127.0.0.1","network":"tcp","method":"2022-blake3-aes-256-gcm","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"outbounds":[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]}')
            config_path = generate_config_file(folder, config_content)
            if os.path.exists(service_file):
                start_service(f"sb{port}")
            else:
                subprocess.run(["/usr/bin/sing-box", "run", "-c", f"{config_path}"])

        elif choice == "5":
            print("grpc-reality+shadowsocks")
            port1 = input("listening port: ")
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"

            print(domain)

            ip = input("remote ip: ")
            port2 = input("remote port: ")

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

            service_file = f"/etc/systemd/system/sb{port1}.service"
            if os.path.exists(service_file):
                print(f"{service_file} exists.")
                stop_service(f"sb{port1}")
            else:
                print(f"{service_file} does not exist.")

            folder = f"/usr/local/etc/sb{port1}"
            create_folder(folder)

            config_content = ('{"log":{"level":"info","timestamp":true},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":' + port1 + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}},"transport":{"type":"grpc","service_name":"rWZXzPnJ"}}],"outbounds":[{"type":"shadowsocks","tag":"shadowsocks-out","server":"' + ip + '","server_port":' + port2 + ',"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}]}')
            config_path = generate_config_file(folder, config_content)
            if os.path.exists(service_file):
                start_service(f"sb{port1}")
            else:
                subprocess.run(["/usr/bin/sing-box", "run", "-c", f"{config_path}"])

        elif choice == "6":
            print("tcp-reality+shadowsocks")
            port1 = input("listening port: ")
            domain = input("domain: ")
            if domain == "":
                domain = "cdn-design.tesla.com"

            print(domain)

            ip = input("remote ip: ")
            port2 = input("remote port: ")

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

            service_file = f"/etc/systemd/system/sb{port1}.service"
            if os.path.exists(service_file):
                print(f"{service_file} exists.")
                stop_service(f"sb{port1}")
            else:
                print(f"{service_file} does not exist.")

            folder = f"/usr/local/etc/sb{port1}"
            create_folder(folder)

            config_content = ('{"log":{"level":"info","timestamp":true},"inbounds":[{"type":"vless","tag":"vless-in","listen":"::","listen_port":' + port1 + ',"sniff":true,"sniff_override_destination":true,"users":[{"uuid":"f8b5cc81-d25c-4d22-92b6-d10a055f7e98","flow":"xtls-rprx-vision"}],"tls":{"enabled":true,"server_name":"' + domain + '","reality":{"enabled":true,"handshake":{"server":"' + domain + '","server_port":443},"private_key":"oOyJjI_Cdn5CfDoKK9HtLai8HVS0jfBbHUz3ytRhOUY","short_id":["4c10a4acb2917613"]}}}],"outbounds":[{"type":"shadowsocks","tag":"shadowsocks-out","server":"' + ip + '","server_port":' + port2 + ',"method":"' + method + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}]}')
            config_path = generate_config_file(folder, config_content)
            if os.path.exists(service_file):
                start_service(f"sb{port1}")
            else:
                subprocess.run(["/usr/bin/sing-box", "run", "-c", f"{config_path}"])

        elif choice == "7":
            print("shadowsocks+shadowsocks")
            port1 = input("listening port: ")

            print("Please select the method:")
            print("1. 2022-blake3-aes-256-gcm")
            print("2. aes-256-gcm")

            method1 = input("method: ")
            if method1 == "":
                method1 = "2022-blake3-aes-256-gcm"
            elif method1 == "1":
                method1 = "2022-blake3-aes-256-gcm"
            elif method1 == "2":
                method1 = "aes-256-gcm"
            else:
                print("Incorrect input, please re-enter.")

            print("Your selected method is:", method1)

            ip = input("remote ip: ")
            port2 = input("remote port: ")

            print("Please select the method:")
            print("1. 2022-blake3-aes-256-gcm")
            print("2. aes-256-gcm")

            method2 = input("method: ")
            if method2 == "":
                method2 = "2022-blake3-aes-256-gcm"
            elif method2 == "1":
                method2 = "2022-blake3-aes-256-gcm"
            elif method2 == "2":
                method2 = "aes-256-gcm"
            else:
                print("Incorrect input, please re-enter.")

            print("Your selected method is:", method2)

            service_file = f"/etc/systemd/system/sb{port1}.service"
            if os.path.exists(service_file):
                print(f"{service_file} exists.")
                stop_service(f"sb{port1}")
            else:
                print(f"{service_file} does not exist.")

            folder = f"/usr/local/etc/sb{port1}"
            create_folder(folder)

            config_content = ('{"log":{"level":"info","timestamp":true},"inbounds":[{"type":"shadowsocks","tag":"shadowsocks-in","listen":"::","listen_port":' + port1 + ',"sniff":true,"sniff_override_destination":true,"method":"' + method1 + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}],"outbounds":[{"type":"shadowsocks","tag":"shadowsocks-out","server":"' + ip + '","server_port":' + port2 + ',"method":"' + method2 + '","password":"W46bWMw2ZfuN9BzV2iTjLjp6INdT1oZLZ8WfpLTPRl4="}]}')
            config_path = generate_config_file(folder, config_content)
            if os.path.exists(service_file):
                start_service(f"sb{port1}")
            else:
                subprocess.run(["/usr/bin/sing-box", "run", "-c", f"{config_path}"])

    except KeyboardInterrupt:
        print("\nThe program has been interrupted.")

if __name__ == "__main__":
    main()
