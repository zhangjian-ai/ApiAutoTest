import os
import time
import xdist
import platform

from typing import List

from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.fixtures import SubRequest
from _pytest.main import Session
from _pytest.nodes import Item, Collector
from _pytest.python import Metafunc
from _pytest.runner import CallInfo
from py._path.local import LocalPath

from framework.report import *
from framework.logger import log
from framework.loads import load_case
from framework.consts import Gather
from framework.values import case_dir, settings
from framework.runner import Executor, Process, Flow, Render
from framework.assists import flat_dict, check_path, stat_result


def pytest_addoption(parser: Parser):
    """
    命令行注册
    初始化时最先调用的Hook
    """

    # 命令行注入
    commands = flat_dict(settings)

    for k, v in commands.items():
        parser.addoption("--" + k, action="store", default=v or "")


def pytest_configure(config: Config):
    """
    初始化配置，在这里配置自定义的一些属性
    此时已经可以使用上一Hook注册的命令行参数
    """
    # 测试进程开始
    log.info("测试进程启动")

    # 加载数据到基类
    Gather.assemble(config)

    # 记录测试开始时间
    config.option.__dict__["session_start"] = time.time()


def pytest_sessionstart(session: Session):
    """
    创建Session对象后调用的Hook
    config对象配置为session的属性
    """
    # 执行前置
    Flow.run_setup()

    # 注入自定义夹具
    Flow.inject_fixture()

    # 测试报告增加元数据
    metadata = session.config._metadata
    metadata.clear()

    # TODO 可以加一些自己需要的信息


def pytest_pycollect_makemodule(path: LocalPath, parent: Collector):
    """
    pytest收集到测试模块后调用的hook函数
    """
    # 从入口文件开始配置测试
    if path.purebasename == "test_entrance":

        # 获取用例名称及其文件路径的映射关系
        cases = load_case(target_dir=os.path.join(case_dir))

        # 导入入口模块，加载用例
        from importlib import import_module
        module = import_module("tests.test_entrance")

        # 构建用例
        for key, val in cases.items():
            setattr(module, key,
                    Process.build_func(key, extend_fixtures=val.get("meta", {}).get("fixtures", [])))

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

    # 用例使用到的夹具
    fixtures = metafunc.fixturenames
    ids, items = Render.render_case(data)

    # 夹具参数化
    for fixture in fixtures:
        # 维护需要参数化的夹具
        if fixture in ('executor',):
            metafunc.parametrize(argnames=fixture, argvalues=items, ids=ids, indirect=True)


def pytest_collection_modifyitems(session: Session, config: Config, items: List[Item]):
    """
    用例参数化完成后调用的hook
    """

    # 用例过滤
    target = config.getoption("test.case")

    if target:
        point = 0
        target_items = [item.strip() for item in target.split(",")]
        func_ids = [item for item in target_items if item.startswith("test_")]
        cls_ids = [item for item in target_items if item.startswith("Test")]
        path_kws = [item for item in target_items if ((item not in func_ids) and (item not in cls_ids))]

        while point < len(items):
            if (items[point].name not in func_ids) and (items[point].parent.name not in cls_ids) and not check_path(
                    path_kws, config.cases.get(items[point].name)["meta"]["origin"]):
                items.pop(point)
                continue

            point += 1

    # item表示每个测试用例
    for item in items:
        # 处理console中文显示问题
        item.name = item.name.encode("utf-8").decode("unicode-escape")
        item._nodeid = item._nodeid.encode("utf-8").decode("unicode-escape")

        # 为item添加mark
        meta = config.cases.get(item.originalname).get("meta")
        item.add_marker(meta["level"])
        for mark in meta.get("markers", []):
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
    # TODO 发送测试报告邮件
    if xdist.is_xdist_master(session): ...

    log.info("执行测试后处理")
    Flow.run_teardown()

    log.info(f"测试进程结束，Exit Code:{exitstatus}")


@pytest.fixture()
def executor(request: SubRequest):
    """
    用例执行器
    """

    # 返回一个执行器实例
    return Executor.request_of(request)
