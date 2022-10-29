import os
import xdist

from copy import deepcopy

from utils.common.report import *
from utils.common import load_yaml, REPORT, mail_instance, send_mail, CONF_DIR
from utils.core import InterfaceManager, Executor


def pytest_addoption(parser):
    """
    命令行注册
    初始化时最先调用的Hook
    """
    # 根据默认配置注册命令行
    # 根据环境信息覆盖默认配置
    full = load_yaml(os.path.join(CONF_DIR, "default.yaml"))

    default = full["default"]
    env_conf = full.get(full["env"])

    if env_conf:
        default.update(env_conf)

    # 注册命令行
    for key, value in default.items():
        parser.addoption(f"--{key}", action="store", default=value)


def pytest_configure(config):
    """
    初始化配置，在这里配置自定义的一些属性
    此时已经可以使用上一Hook注册的命令行参数
    """
    # 测试进程开始
    log.info("测试进程启动")

    # 接口管理对象
    config.im = InterfaceManager(config)


def pytest_sessionstart(session):
    """
    创建Session对象后调用的Hook
    config对象配置为session的属性
    """
    # 测试进程启动时间
    session.session_start = time.strftime('%Y-%m-%d %H:%M:%S')


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    根据测试结果打印用例完成的日志
    """
    out = yield

    if call.when == 'call':
        result = out.get_result()
        flag = result.outcome

        printer = getattr(log, 'info' if flag == 'passed' else 'error')
        printer(f'执行结束: {result.outcome.upper()}')


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    if xdist.is_xdist_master(session):
        # 测试报告也仅在主节点发送一次
        if os.path.exists(REPORT):
            with open(REPORT, "r") as f:
                title = f"测试报告"
                recipients = session.config.getoption("recipients")
                email_instance = mail_instance(f.read(), recipients, title, [REPORT])
                send_mail(email_instance)

        # 分布式测试时，在主节点执行数据清理逻辑
        log.info("清理测试数据")

    log.info(f"测试进程结束，Exit Code:{exitstatus}")


@pytest.fixture(scope="module")
def module_data(request):
    """
    模块维度加载测试数据
    """
    full = request.module.__file__
    file = os.path.basename(full).replace(".py", ".yaml")
    path = os.path.dirname(full).replace("tests", "data", 1)

    data_path = os.path.join(path, file)

    return load_yaml(data_path)


@pytest.fixture()
def executor(request, record_property, module_data):
    """
    用例执行器
    """
    func_name = request.function.__name__
    data = deepcopy(module_data.get(func_name))

    # 绑定用例信息
    info = data.get("info", {})
    [record_property(key, val) for key, val in info.items()]

    # 用例开始执行
    log.info(f"执行用例: {func_name} <{info.get('desc')}>")

    # 返回一个执行器实例
    return Executor(request.config, data.get("steps"))
