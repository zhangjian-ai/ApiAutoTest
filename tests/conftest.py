import os
import xdist

from copy import deepcopy

from utils.common.report import *
from utils.common import load_yaml, REPORT, Mail, CONF_DIR
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

    # 测试报告增加元数据
    metadata = session.config._metadata
    metadata.clear()
    metadata["项目名称"] = "接口自动化测试"
    metadata["项目名称"] = time.strftime('%Y-%m-%d %H:%M:%S')

    # 会话级别的前置可在此处执行
    # come baby


def pytest_generate_tests(metafunc):
    """
    用例收集阶段钩子
    生成（多个）对测试函数的参数化调用
    """
    full = metafunc.module.__file__
    file = os.path.basename(full).replace(".py", ".yaml")
    path = os.path.dirname(full).replace("tests", "data", 1)

    case_name = metafunc.function.__name__
    config = metafunc.config

    # 获取用例数据
    data = load_yaml(os.path.join(path, file)).get(case_name)
    parameters = data.pop("param", None)
    items = []

    # 参数化逻辑
    if parameters:
        # 参数值处理
        Executor.parameter_replace(parameters)

        # 将参数拆分成参数化对象
        keys = [key for key in parameters.keys()]
        # 将所有非列表值修正为列表
        for key in keys:
            if not isinstance(parameters[key], (list, tuple)):
                parameters[key] = [parameters[key]]
        # 生成参数化结果
        for i in range(len(parameters[keys[0]])):
            param = {}
            for key in keys:
                param[key] = parameters[key][i]
            item = deepcopy(data)
            item["param"] = param
            items.append(item)
    else:
        items.append(data)

    # 用例使用到的夹具
    fixtures = metafunc.definition._fixtureinfo.argnames

    # 构建ids
    ids = []
    if len(items) > 1:
        for idx, item in enumerate(items):
            ids.append(f"{item['info']['description']} - {idx}")
    else:
        ids.append(f"{items[0]['info']['description']}")

    # 夹具参数化
    for fixture in fixtures:
        # 维护需要参数化的夹具
        if fixture in ('executor',):
            metafunc.parametrize(argnames=fixture, argvalues=items, ids=ids, indirect=True)


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


def pytest_collection_modifyitems(session, config, items):
    """
    处理参数化乱码问题
    """
    # item表示每个测试用例，解决console中文显示问题
    for item in items:
        item.name = item.name.encode("utf-8").decode("unicode-escape")
        item._nodeid = item._nodeid.encode("utf-8").decode("unicode-escape")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    根据测试结果打印用例完成的日志
    """
    out = yield

    if call.when == 'call':
        report = out.get_result()
        flag = report.outcome

        printer = getattr(log, 'info' if flag == 'passed' else 'error')
        printer(f'执行结束: {report.outcome.upper()}')


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    if xdist.is_xdist_master(session):
        # 测试报告也仅在主节点发送一次
        if os.path.exists(REPORT):
            with open(REPORT, "r") as f:
                Mail.config = session.config
                subject = "测试报告"
                Mail.send_mail(content=f.read(), subject=subject, annex_files=[REPORT])

        # 分布式测试时，在主节点执行数据清理逻辑
        log.info("清理测试数据")

    log.info(f"测试进程结束，Exit Code:{exitstatus}")


@pytest.fixture()
def executor(request, record_property):
    """
    用例执行器
    """

    # 返回一个执行器实例
    return Executor(request, record_property)
