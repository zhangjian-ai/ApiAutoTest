import sys
import pytest
import argparse
import multiprocessing


parser = argparse.ArgumentParser()

# 在此处添加自己的命令行参数
parser.add_argument("--host", default="http://httpbin.org", help="主机地址")
parser.add_argument("--port", default="80", help="主机端口")

parser.add_argument("--mark", default="smoke", help="测试mark。smoke daily")
parser.add_argument("--nums", default=str(multiprocessing.cpu_count() // 2), help="测试并发进程数")

args = parser.parse_args()

# 自定义参数 命令行
# 此变量衔接 entrypoint.py 和 conftest.py 中的变量
custom = f"--host {args.host} --port {args.port}"

# pytest 命令行
line = f"--capture=sys -v --html report/report.html --self-contained-html -n {args.nums} " \
       f"--reruns 1 --reruns-delay 3 -m {args.mark} {custom}"

# 运行测试进程
try:
    code = pytest.main(line.split(" ")).value
except SystemExit as exc:
    code = exc.code

# 主进程退出
sys.exit(code)
