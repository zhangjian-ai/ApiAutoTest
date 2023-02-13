import sys
import pytest
import argparse
import multiprocessing

from utils.common import REPORT

parser = argparse.ArgumentParser()

# 在此处添加自己的命令行参数
parser.add_argument("--host", default="http://www.baidu.com", help="主机地址")
parser.add_argument("--port", default="80", help="主机端口")

parser.add_argument("--level", default="SMOKE", help="测试mark。SMOKE DAILY")
parser.add_argument("--nums", default=str(multiprocessing.cpu_count() // 2), help="测试并发进程数")

args = parser.parse_args()

# 自定义参数 命令行
# 此变量衔接 entry.py 和 conftest.py 中的变量
custom = f"--host {args.host} --port {args.port}"

# pytest 命令行
line = f"--capture=sys -v --html {REPORT} --self-contained-html -n {args.nums} " \
       f"--reruns 1 --reruns-delay 3 -m {args.level} {custom}"

# 运行测试进程
try:
    code = pytest.main(line.split(" ")).value
except SystemExit as exc:
    code = exc.code

# 主进程退出
sys.exit(code)
