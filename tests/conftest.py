import os
import shutil

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

from config import CONF_FILE, TEMP_DIR, CASE_DIR
from framework.core.report import *
from framework.core.mail import Mail
from framework.core.render import Render
from framework.core.loads import load_case, load_yaml
from framework.core.runner import Executor, CapabilitySupport, Control

from framework.open.entry import Entry
from framework.open.logger import log

# 项目配置
settings = load_yaml(CONF_FILE)["nightingale"]


def pytest_addoption(parser: Parser):
    """
    命令行注册
    初始化时最先调用的Hook
    """

    def add_option(p: Parser, args: dict):
        for k, v in args.items():
            if isinstance(v, dict):
                add_option(p, v)
            else:
                p.addoption(f"--{k}", action="store", default=str(v))

    # 内置固定命令行
    parser.addoption("--case", action="store", default="")

    # 注册通用命令行
    add_option(parser, settings.get("args", {}))


def pytest_configure(config: Config):
    """
    初始化配置，在这里配置自定义的一些属性
    此时已经可以使用上一Hook注册的命令行参数
    """
    # 测试进程开始
    log.info("测试进程启动")

    # 装载Entry
    Entry.assemble(config, settings)


def pytest_sessionstart(session: Session):
    """
    创建Session对象后调用的Hook
    config对象配置为session的属性
    """
    # 创建测试临时目录
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    # 处理settings配置的引用
    Render.render_settings(settings)

    # 执行前置
    Control.run_setup()

    # 注入自定义夹具
    Control.inject_fixture()

    # 测试报告增加元数据
    metadata = session.config._metadata
    metadata.clear()

    for key, val in settings.get("report", {}).items():
        if key == "测试时间":
            metadata[key] = time.strftime('%Y-%m-%d %H:%M:%S')
            continue

        metadata[key] = val

    # 同步邮件时间信息
    settings.get("args", {}).get("mail", {})["start_time"] = metadata["测试时间"]


def pytest_pycollect_makemodule(path: LocalPath, parent: Collector):
    """
    pytest收集到测试模块后调用的hook函数
    """
    # 从入口文件开始配置测试
    if path.purebasename == "test_entrypoint":

        # 获取用例名称及其文件路径的映射关系
        cases = load_case(target_dir=os.path.join(CASE_DIR),
                          target=parent.config.getoption("case"))

        # 导入入口模块，加载用例
        from importlib import import_module
        module = import_module("tests.test_entrypoint")

        # 构建用例
        for key, val in cases.items():
            setattr(module, key,
                    CapabilitySupport.build_func(key, extend_fixtures=val.get("spec", {}).get("fixtures", [])))

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
        Render.trans_parameters(parameters)

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
                Mail.send_mail(config=settings.get("args", {}).get("mail", {}), content=f.read(),
                               annex_files=[session.config._html.logfile])

        # 分布式测试时，在主节点执行数据清理逻辑
        log.info("执行测试后处理")
        Control.run_teardown()

        # 删除测试临时目录
        if os.path.exists(TEMP_DIR):
            # os.rmdir(TEMP_DIR)
            shutil.rmtree(TEMP_DIR, ignore_errors=True)

    Entry.close()

    log.info(f"测试进程结束，Exit Code:{exitstatus}")


@pytest.fixture()
def executor(request: SubRequest):
    """
    用例执行器
    """

    # 返回一个执行器实例
    return Executor.request_of(request)
