import subprocess

# 获取用户输入
ip = input("请输入IP地址: ")
port_input = input("请输入端口号（默认为5201，按下空格使用默认值）: ")

# 设置默认端口
if port_input == "":
    port = 5201
else:
    port = int(port_input)

# 获取用户选择
mode_input = input("请选择模式（-RZ或-Z，默认为-RZ，按下空格使用默认值）: ")
if mode_input == "":
    mode = "-RZ"
else:
    mode = mode_input

# 构建iperf3命令
command = f"iperf3 -c {ip} -p {port} {mode}"

# 执行命令
try:
    subprocess.run(command, shell=True, check=True)
except subprocess.CalledProcessError as e:
    print("命令执行失败:", e)
