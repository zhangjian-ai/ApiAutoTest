import os
from pathlib import Path

# 项目根路径
BASE_DIR = Path(__file__).resolve().parent.parent.__str__()

# 测试过程中临时文件存放路径
TEMP_DIR = os.path.join(BASE_DIR, "temporary")

# 用户空间
USER_DIR = os.path.join(BASE_DIR, "user")

# 配置文件
CONF_FILE = os.path.join(USER_DIR, "settings.yaml")

# 测试用例目录
CASE_DIR = os.path.join(USER_DIR, "data")

# 用户工具库
USER_UTILS = os.path.join(USER_DIR, "utils")
