"""
@Project: api-auto-test
@File: runner.py
@Author: Seeker
@Date: 2023/7/8 5:58 下午
"""

import json
import time
import pytest

from copy import deepcopy
from types import FunctionType

from _pytest.config import Config

from utils.framework.magic import Magic
from utils.framework.core import Setup, Teardown
from utils.framework.loads import load_cls, data_rpc
from utils.framework.open.helper import http_request, protobuf_to_dict
from utils.framework.open.logger import log


def build_func(name: str, extend_fixtures: list):
    """
    创建一个函数
    """
    # 夹具
    fixtures = ["executor"]

    if extend_fixtures:
        fixtures.extend(extend_fixtures)

    # 将code串编译成code对象
    code = \
    compile(source=f'def func({",".join(fixtures)}):\n\texecutor.schedule()', filename=name, mode="exec").co_consts[0]
    # 创建函数
    # globals 选项为函数提供全局变量。比如函数内部需要调用其他方法，如果不指定会ERROR
    # locals()/globals() 内置函数分别返回局部(所在局部块，这里就是函数内部作用域)/全局(当前模块)的作用域字典
    function = FunctionType(code=code, globals=globals(), name=name)

    return function


def run_setup(cls_path: str, config: Config):
    """
    根据用户配置的 Setup 类 执行前置操作
    """
    if cls_path:
        cls = load_cls(cls_path)

        if not issubclass(cls, Setup):
            raise RuntimeError(f"自定义前置类不是 Setup 子类: {cls}")

        config.setup = cls()

        # 执行准备工作
        config.setup.before()


def run_teardown(cls_path: str):
    """
    根据用户配置的 Teardown 类 执行后置操作
    """
    if cls_path:
        cls = load_cls(cls_path)

        if not issubclass(cls, Teardown):
            raise RuntimeError(f"自定义后置类不是 Teardown 子类: {cls}")

        # 执行后置工作
        cls().after()


def verify(expect: dict, response: dict):
    """
    验证 expect 中的键值是否都能在 response 中找到且一致
    """

    # 验证实际结果是否与预期一致
    for key, value in expect.items():
        # 比较运算处理
        if key in ("<", ">", "==", ">=", "<=", "!="):
            real_value = response
            if not isinstance(response, (int, float, str)):
                real_value = len(response)

            if isinstance(real_value, str):
                real_value = f"'{real_value}'"
            if isinstance(value, str):
                value = f"'{value}'"

            assert eval(f"{real_value} {key} {value}"), f'\n' \
                                                        f'KEY: {key} \n' \
                                                        f'运算符: {key} ' \
                                                        f'(如果实际返回值是一个对象，那么此时检验的是对象的长度) \n' \
                                                        f'预期值: {value}\n' \
                                                        f'实际值: {real_value}\n' \
                                                        f'返回值: {response}\n'

        # 包含关系
        elif key in ("in", "not in"):
            if not isinstance(response, (list, str, dict)):
                assert False, f'\n' \
                              f'KEY: {key} \n' \
                              f'运算符: {key} ' \
                              f'预期值: {value}\n' \
                              f'实际值: {response} 的类型不支持包含关系运算\n'

            elif isinstance(value, dict):
                _verify_list(key, [value], response, operate=key)

            elif isinstance(value, (list, tuple)):
                _verify_list(key, value, response, operate=key)

            else:
                if isinstance(value, str):
                    value = f"'{value}'"
                if isinstance(response, str):
                    response = f"'{response}'"

                assert eval(f"{value} {key} {response}"), f'\n' \
                                                          f'KEY: {key} \n' \
                                                          f'运算符: {key} ' \
                                                          f'预期值: {value}\n' \
                                                          f'实际值: {response}\n' \
                                                          f'包含关系运算结果不为真'

        # any 预期列表中任意一个值在实际响应中就算通过
        elif key in ("any",):
            # 使用 any 时，要求预期值是列表或元组
            assert isinstance(value, (list, tuple)), f'\n' \
                                                     f'KEY: {key} \n' \
                                                     f'预期值: {value} \n' \
                                                     f'使用 any 关键字时，要求预期值是列表或元组'
            success = False
            # 将预期值依次放入列表校验，直到校验成功
            for sub_val in value:
                try:
                    _verify_list(key, [sub_val], response)
                    success = True
                    break
                except AssertionError:
                    pass

            assert success, f'\n' \
                            f'KEY: {key} \n' \
                            f'预期值: {value} \n' \
                            f'预期值: {response} \n' \
                            f'预期结果中没有任何值在实际列表中存在'

        # 如果预期值是str、int、float那么就直接对比
        elif isinstance(value, (str, int, float)):
            assert isinstance(response, dict) \
                   and value == response.get(key), f'\n' \
                                                   f'KEY: {key} \n' \
                                                   f'预期结果: {json.dumps(expect, indent=2, ensure_ascii=False)}\n' \
                                                   f'实际结果: {json.dumps(response, indent=2, ensure_ascii=False)}\n'

        # 如果预期值是list则便利预期列表中的item是否都在实际结果中能找到
        elif isinstance(value, (list, tuple)):
            _verify_list(key, value, response.get(key))

        # 如果预期值是dict则再次调用本方法进行递归验证
        elif isinstance(value, dict):
            assert isinstance(response, dict), f'\n' \
                                               f'预期结果: {json.dumps(expect, indent=2, ensure_ascii=False)}\n' \
                                               f'实际结果: {json.dumps(response, indent=2, ensure_ascii=False)}\n' \
                                               f"响应对象实际类型是: {type(response)}，预期类型是 DICT\n"
            verify(value, response.get(key))


def _verify_list(key: str, expect: list, response: list, operate: str = "in"):
    """
    针对列表验证
    key 为预期列表expect在父级字典对应的键，传递过来主要为了打印日志
    operate 取值为 in、not in 用于表示包含和不包含的关系
    """

    # 检查实际值的类型
    assert isinstance(response, (list, tuple)), f'\n' \
                                                f'KEY: {key} \n' \
                                                f'预期值: {expect}\n' \
                                                f'实际值: {response}\n'

    # # 列表长度校验
    # if len(value) != len(real_value):
    #     assert False, f'\n' \
    #                   f'KEY: {key} \n' \
    #                   f'预期列表长度: {len(value)}\n' \
    #                   f'实际列表长度: {len(real_value)}\n'

    # 列表项依次校验
    for sub_val in expect:
        # 此处不考虑列表项仍然是列表的情况，此种情况也不能出现在脚本中
        if isinstance(sub_val, (list, tuple)):
            assert False, f'\n' \
                          f'KEY: {key}\n' \
                          f'预期值: {expect}\n' \
                          f'结果验证中不允许列表嵌套列表的预期值'

        # 常规类型时，考虑返回值可能无序，直接用 operate 执行运算
        elif isinstance(sub_val, (str, int, float)):
            if isinstance(sub_val, str):
                sub_val = f"'{sub_val}'"
            if isinstance(response, str):
                response = f"'{response}'"

            assert eval(f"{sub_val} {operate} {response}"), f'\n' \
                                                            f'KEY: {key}\n' \
                                                            f'预期列表: {expect}\n' \
                                                            f'实际列表: {response}\n' \
                                                            f'缺失表项: {sub_val}'

        # 如果列表项是字典，那么就便利实际结果列表依次对比直到通过
        elif isinstance(sub_val, dict):
            status = operate == "not in"
            for item in response:
                if not isinstance(item, dict):
                    continue
                try:
                    verify(sub_val, item)
                    status = not status
                    break
                except AssertionError:
                    pass

            assert status, f'\n' \
                           f'KEY: {key} \n' \
                           f'运算符: {operate} \n' \
                           f'预期值: {sub_val}\n' \
                           f'实际值: {response}\n' \
                           f'包含关系运算结果不为真'


def call(im, step):
    """
    执行请求
    """
    # 获取接口信息
    api = step.get("api")

    # 为请求数据 处理关联 和 动态数据替换
    request = deepcopy(step.get("request"))
    expect = deepcopy(step.get("response", {}))

    # 请求类型。不是http全部当作gRPC
    is_http = "(**request)" not in api

    # http
    if is_http:
        api = getattr(im, api)

        # 测试数据替换默认的api数据
        for key, val in request.items():
            if key in api:
                if key == "url":
                    api["url"] += str(val)

                elif isinstance(api[key], dict):
                    api[key].update(val)

                continue

            api[key] = val
    else:
        service = api.split(".", 1)[0]
        stub = service + "Stub"
        api = api.replace(service, stub)

    # 根据调度逻辑处理接口调用和验证
    rule = {"timeout": 0, "interval": 3}
    rule.update(step.get("rule", {}))
    response = None
    start = 0

    while start <= rule["timeout"]:
        try:
            # 请求接口
            response = http_request(**api) if is_http else protobuf_to_dict(exec(api, data_rpc))

            verify(expect, response)

            break
        except Exception as e:
            # 如果是最后一次接口调用就引发异常
            if start > rule["timeout"] - rule["interval"]:
                raise e

            start += rule["interval"]
            time.sleep(rule["interval"])

    return response or {}


class Executor:
    """
    用例执行器
    """

    def __init__(self, request, record_property):
        self.data = request.param
        self.config = request.config
        self.func = request.function.__name__
        self.record_property = record_property

        # 神奇魔法
        self.magic = Magic()

        # 用例 参数化变量，转换之后赋值给magic
        args = deepcopy(self.data.get("param", {}))
        self.magic.trans(args)
        self.magic.cp = args

        # 校验用例是否可执行
        self.inspect()

    def inspect(self):
        """
        用例开始前的审查工作
        """
        # 判断skip
        spec = deepcopy(self.data.get("spec", {}))
        skips = spec.get("skips", [])
        branch = self.config.getoption("branch")

        if branch and branch in skips:
            log.warning(f"分支<{self.config.getoption('branch')}> 已限制用例 <{self.func}> 不执行")
            pytest.skip(f"分支<{self.config.getoption('branch')}> 已限制用例 <{self.func}> 不执行")

        # 绑定用例信息
        meta = deepcopy(self.data.get("meta", {}))
        self.magic.trans(meta)
        meta["params"] = self.magic.cp

        [self.record_property(key, val) for key, val in meta.items()]

        # 用例开始执行
        log.info(f"执行用例: {self.func} <{meta.get('desc')}>")

    def schedule(self):
        """
        用例具体的step在这里调度完成
        """
        # 处理 step 级别的参数化
        origin_steps = deepcopy(self.data["steps"])
        target_steps = []

        for step in origin_steps:
            param = step.get("param", None)

            if param:
                Magic.trans_parameters(param)

                keys = [key for key in param.keys()]

                # 将所有非列表值修正为列表
                for key in keys:
                    if not isinstance(param[key], (list, tuple)):
                        param[key] = [param[key]]

                for i in range(len(param[keys[0]])):
                    args = {}
                    for key in keys:
                        args[key] = param[key][i]
                    item = deepcopy(step)
                    item["step_args"] = args
                    target_steps.append(item)
            else:
                target_steps.append(step)

        # 按步骤依次调度
        for idx, step in enumerate(target_steps):
            # 处理步骤模版参数，转换之后赋值给magic
            args = step.pop("step_args", {})
            self.magic.sp.clear()
            self.magic.trans(args)
            self.magic.sp = args

            # 处理其他模版参数
            self.magic.trans(step)

            # 打印用户自定义日志
            log.info(f"Step {idx + 1}: {step.get('desc', '未填写step描述信息，建议补充')}")

            # 暂存当前接口调用结果到stages
            self.magic.r.append(call(self.config.im, step))
