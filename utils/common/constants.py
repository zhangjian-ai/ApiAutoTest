import os

from pathlib import Path

# 项目目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent.__str__()

# 配置文件目录
CONF_DIR = os.path.join(BASE_DIR, "config")

# 接口文档目录
API_DIR = os.path.join(BASE_DIR, "api")

# 测试过程中临时文件目录
TEMP_DIR = os.path.join(BASE_DIR, "temporary")

# 测试报告
REPORT = os.path.join(BASE_DIR, "report", "report.html")
