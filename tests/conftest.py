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

from utils.framework.report import *
from utils.framework.mail import Mail
from utils.framework.magic import Magic
from utils.framework.core import Entry, InterfaceManager
from utils.framework.loads import load_case, load_yaml, load_fixture, render_string
from utils.framework.runner import build_func, Executor, run_setup, run_teardown
from config.settings import TEMP_DIR, BASE_DIR, TEST_CASE, SETUP_CLASS, TEARDOWN_CLASS, EMAIL_CONF, INIT_FILE, FIXTURES, \
    REPORT_ENV


def pytest_addoption(parser: Parser):
    """
    命令行注册
    初始化时最先调用的Hook
    """
    # 加载舒适化文件
    conf = load_yaml(INIT_FILE)

    default = conf["default"]

    if conf.get("env"):
        env_conf = conf.get(conf["env"])

        if env_conf:
            default.update(env_conf)

    # 内置固定命令行
    if "case" not in default:
        parser.addoption("--case", action="store", default="")

    if "branch" not in default:
        parser.addoption("--branch", action="store", default="master")

    # 注册命初始化令行
    for key, value in default.items():
        parser.addoption(f"--{key}", action="store", default=value)

    # 注册邮箱配置参数
    for key, value in EMAIL_CONF.items():
        parser.addoption(f"--{key}", action="store", default=value)


def pytest_configure(config: Config):
    """
    初始化配置，在这里配置自定义的一些属性
    此时已经可以使用上一Hook注册的命令行参数
    """
    # 测试进程开始
    log.info("测试进程启动")

    # 测试开始时间
    config.start_time = time.strftime('%Y-%m-%d %H:%M:%S')

    # 接口管理
    config.im = InterfaceManager()

    # 为Entry类配置config
    Entry.config = config

    # 执行前置
    run_setup(SETUP_CLASS, config)

    # 加载自定义夹具
    load_fixture(FIXTURES)


def pytest_sessionstart(session: Session):
    """
    创建Session对象后调用的Hook
    config对象配置为session的属性
    """
    # 删除测试临时目录
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    # 测试报告增加元数据
    metadata = session.config._metadata
    metadata.clear()

    for key, val in REPORT_ENV.items():
        metadata[key] = render_string(val, session.config)


def pytest_pycollect_makemodule(path: LocalPath, parent: Collector):
    """
    pytest收集到测试模块后调用的hook函数
    """
    # 从入口文件开始配置测试
    if path.purebasename == "test_entrypoint":

        # 获取用例名称及其文件路径的映射关系
        cases = load_case(target_dir=os.path.join(BASE_DIR, TEST_CASE),
                          target=parent.config.getoption("case"))

        # 导入入口模块，加载用例
        from importlib import import_module
        module = import_module("tests.test_entrypoint")

        # 构建用例
        for key, val in cases.items():
            setattr(module, key, build_func(key, extend_fixtures=val.get("spec", {}).get("fixtures", [])))

        # 传递测试数据
        parent.config.cases = cases


def pytest_generate_tests(metafunc: Metafunc):
    """
    用例收集阶段钩子
    生成（多个）对测试函数的参数化调用
    """

    # 获取用例数据
    case_name = metafunc.function.__name__
    data = metafunc.config.cases.get(case_name)

    if not data:
        raise RuntimeError(f"用例数据不存在，用例名称: {case_name}")

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
        for mark in config.cases.get(item.originalname).get("spec", {}).get("marks", ""):
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
        if hasattr(session.config, "_html"):
            with open(session.config._html.logfile, "r") as f:
                Mail.send_mail(config=session.config, content=f.read(), annex_files=[session.config._html.logfile])

        # 分布式测试时，在主节点执行数据清理逻辑
        log.info("执行测试后处理")
        run_teardown(TEARDOWN_CLASS)

        # 删除测试临时目录
        if os.path.exists(TEMP_DIR):
            os.system(f"rm -rf {TEMP_DIR}")

    log.info(f"测试进程结束，Exit Code:{exitstatus}")


@pytest.fixture()
def executor(request: SubRequest, record_property):
    """
    用例执行器
    """

    # 返回一个执行器实例
    return Executor(request, record_property)
