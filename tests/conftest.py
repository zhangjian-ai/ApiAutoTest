import os
import xdist

from typing import List
from copy import deepcopy

from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.fixtures import SubRequest
from _pytest.main import Session
from _pytest.nodes import Item, Collector
from _pytest.python import Metafunc
from _pytest.runner import CallInfo
from py._path.local import LocalPath

from utils.common.report import *
from utils.core import InterfaceManager, Executor
from utils.common import REPORT, Mail, CONF_DIR, Magic, BASE_DIR, load_data, build_func, load_yaml


def pytest_addoption(parser: Parser):
    """
    命令行注册
    初始化时最先调用的Hook
    """
    # 内置固定命令行
    parser.addoption("--case", action="store", default=None)

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


def pytest_configure(config: Config):
    """
    初始化配置，在这里配置自定义的一些属性
    此时已经可以使用上一Hook注册的命令行参数
    """
    # 测试进程开始
    log.info("测试进程启动")

    # 接口管理对象
    config.im = InterfaceManager(config)


def pytest_sessionstart(session: Session):
    """
    创建Session对象后调用的Hook
    config对象配置为session的属性
    """

    # 测试报告增加元数据
    metadata = session.config._metadata
    metadata.clear()
    metadata["项目名称"] = "接口自动化测试"
    metadata["测试时间"] = time.strftime('%Y-%m-%d %H:%M:%S')

    # 会话级别的前置可在此处执行
    # come baby


def pytest_pycollect_makemodule(path: LocalPath, parent: Collector):
    """
    pytest收集到测试模块后调用的hook函数
    """
    # 从入口文件开始配置测试
    if path.purebasename == "test_entrypoint":

        # 获取用例名称及其文件路径的映射关系
        data_source = load_data(target_dir=os.path.join(BASE_DIR, "data"),
                                target_case=parent.config.getoption("case"))

        # 导入入口模块，加载用例
        from importlib import import_module
        module = import_module("tests.test_entrypoint")

        # 构建用例
        for key in data_source.keys():
            setattr(module, key, build_func(key))

        # 传递测试数据
        parent.config.data_source = data_source


def pytest_generate_tests(metafunc: Metafunc):
    """
    用例收集阶段钩子
    生成（多个）对测试函数的参数化调用
    """

    # 获取用例数据
    data = metafunc.config.data_source.get(metafunc.function.__name__)
    parameters = data.pop("param", None)
    items = []

    # 参数化逻辑
    if parameters:
        # 参数值处理
        Magic.trans_parameters(parameters)

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
            ids.append(f"{item.get('meta', {}).get('desc', ' T')} - {idx}")
    else:
        ids.append(f"{items[0].get('meta', {}).get('desc', ' T')}")

    # 夹具参数化
    for fixture in fixtures:
        # 维护需要参数化的夹具
        if fixture in ('executor',):
            metafunc.parametrize(argnames=fixture, argvalues=items, ids=ids, indirect=True)


def pytest_collection_modifyitems(session: Session, config: Config, items: List[Item]):
    """
    用例参数化完成后调用的hook
    """

    # item表示每个测试用例
    for item in items:
        # 处理console中文显示问题
        item.name = item.name.encode("utf-8").decode("unicode-escape")
        item._nodeid = item._nodeid.encode("utf-8").decode("unicode-escape")

        # 为item添加mark
        for mark in config.data_source.get(item.originalname).get("spec", {}).get("marks", ""):
            item.add_marker(mark)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: CallInfo[None]):
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
def pytest_sessionfinish(session: Session, exitstatus: int):
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
def executor(request: SubRequest, record_property):
    """
    用例执行器
    """

    # 返回一个执行器实例
    return Executor(request, record_property)
