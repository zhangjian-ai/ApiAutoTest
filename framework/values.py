import os

from pathlib import Path

from framework.loads import load_yaml


# 项目根路径
workdir = Path(__file__).resolve().parent.parent.__str__()

# 测试用例目录
case_dir = os.path.join(workdir, "tests")

# 请求协议类型
protos = ["HTTP", "HTPB", "HOOK"]

# 业务配置
settings = load_yaml(os.path.join(workdir, "configure.yml"))["settings"]

