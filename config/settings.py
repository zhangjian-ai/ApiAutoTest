"""
用户提供的所有模块、数据均应在此处完成配置
路径信息基于项目路径配置即可
"""
import os
import time
from pathlib import Path

# 项目名称
BASE_NAME = "接口自动化测试"

# 测试进程启动时间
START_TIME = time.strftime('%Y-%m-%d %H:%M:%S')

# 项目根路径
BASE_DIR = Path(__file__).resolve().parent.parent.__str__()

# 初始化参数配置文件
DEBUG_FILE = os.path.join(BASE_DIR, "config", "init.yaml")

# pytest 需要注册的命令行参数。注册时都注册为 字符串，默认是是 ""
CMD_ARGS = ["host", "port", "username", "password", "branch"]

# 测试过程中临时文件存放路径
TEMP_DIR = os.path.join(BASE_DIR, "temporary")

# API配置
# API 文件配置，配置文件只接受 yaml 格式配置，不匹配则忽略
# 字段说明：
# {
# "product": "aiforce", 必填，产品名称。作为调用接口的对象名
# "path": "api/aiforce", 必填，API配置文件存放的目录
# "proto": "http"        选填，http 为默认值。当前暂未使用
# }
API_FILE = [{"product": "httpbin", "path": "api/httpbin"}]

# 测试用例目录
TEST_CASE = "data/demo"

# 数据工厂路径。测试用例中使用的 模版类、模版函数 均应在数据工厂实现
DATA_FACTORY = "utils/factory"

# 前置类。必须继承 utils.framework.core.Setup 类
# 示例: utils.control.control.CustomSetup
SETUP_CLASS = "utils.control.setup.MySetup"

# 后置类。必须继承 utils.framework.core.Teardown 类
TEARDOWN_CLASS = ""

# 自定义夹具模块导包路径
FIXTURES = "utils.fixtures.fixtures"

# 邮件服务器配置，参数key不可修改
EMAIL_CONF = {
    "email_sender": "",  # 发件人邮箱
    "email_receiver": "",  # 收件人邮箱
    "from_name": "测试",
    "subject": "测试报告-{branch}",  # 邮件标题，用 {参数名} 引用命令行参数
    "email_password": "",  # 发件人登陆密码
    "smtp_server": "smtp.exmail.qq.com",
    "ssl_port": "465"
}

# 测试报告环境信息
REPORT_META_CONF = {
    "项目名称": BASE_NAME,
    "测试时间": START_TIME
}
