"""
@Project: bot3-env-verify
@File: __init__.py.py
@Author: Seeker
@Date: 2022/10/3 2:09 下午
"""
import os
from pathlib import Path

# 项目根路径
BASE_DIR = Path(__file__).resolve().parent.parent.__str__()

# 测试过程中临时文件存放路径
TEMP_DIR = os.path.join(BASE_DIR, "temporary")

# 配置路径
CONF_DIR = os.path.join(BASE_DIR, "config")

# 配置文件
CONF_FILE = os.path.join(CONF_DIR, "settings.yaml")

# 测试用例目录
CASE_DIR = os.path.join(CONF_DIR, "data")

# 自定义工具库路径
CUSTOM_LIBS = os.path.join(CONF_DIR, "libs")
