"""
@Project: api-auto-test
@File: runner.py
@Author: Seeker
@Date: 2023/7/8 5:58 下午
"""
import importlib
import json
import re
import time
import pytest

from copy import deepcopy
from typing import Optional
from types import FunctionType

from _pytest.fixtures import SubRequest

from framework.open.entry import Setup, Entry, Teardown
from framework.open.helper import http_request
from framework.open.logger import log


class Flow(Entry):
    """
    流程控制
    """

    @classmethod
    def run_setup(cls):
        """
        根据用户配置的 Setup 类 执行前置操作
        """
        for setup in cls.controllers.get("__setup__", []):
            if not issubclass(setup, Setup):
                raise RuntimeError(f"自定义前置类不是 Setup 子类: {setup}")

            cls.config.setup = setup()

            # 执行准备工作
            cls.config.setup.before()

    @classmethod
    def inject_fixture(cls):
        """
        注入自定义夹具
        """
        module = importlib.import_module("tests.conftest")

        for fixture in cls.fixtures.values():
            setattr(module, fixture.__name__, fixture)

    @classmethod
    def run_teardown(cls):
        """
        根据用户配置的 Teardown 类 执行后置操作
        """
        for teardown in cls.controllers.get("__teardown__", []):
            if not issubclass(teardown, Teardown):
                raise RuntimeError(f"自定义后置类不是 Teardown 子类: {teardown}")

            # 执行后置工作
            teardown().after()


class Render(Entry):
    """
    渲染模版语法内容
    """

    def __init__(self, params: dict):
        """
        构造器
        @param params: 用例接别的参数化数据
        """
        # r对象，应该是一个列表
        self.r = []

        # 步骤参数化对象
        self.sp = {}

        # 夹具
        self.fp = {}

        # 用例参数化对象
        self.cp = params
        self.trans(params)

    def trans(self, data):
        """
        将对象data中模版语法转换成真是数据
        """
        if isinstance(data, dict):
            for key, val in data.items():
                if not val:
                    continue

                if isinstance(val, str):
                    data[key] = self._render_(val)
                elif isinstance(val, (dict, list)):
                    self.trans(val)

        elif isinstance(data, list):
            for idx, val in enumerate(data):
                if not val:
                    continue

                if isinstance(val, str):
                    data[idx] = self._render_(val)
                elif isinstance(val, (dict, list)):
                    self.trans(val)
        else:
            pytest.fail(f"trans方法入参类型错误: {type(data)}， 默认只接受 list、dict")

    def _render_(self, origin):
        """
        为字符串中的模版语法施加魔法，让其变成真实数据
        """
        # 正则匹配出多个模版
        args = re.findall("@<(.+?)>", origin)

        # 可用的变量参数对象
        params = {"r": self.r}
        params.update(self.cp)
        params.update(self.sp)
        params.update(self.fp)

        for arg in args:
            # 转换模版代码为真是数据值
            target = eval(arg, dict(**self.utils, **params))

            if f"@<{arg}>" == origin:
                return target

            origin = origin.replace(f"@<{arg}>", str(target))

        return origin

    @staticmethod
    def trans_parameters(data: dict):
        """
        用例级别的参数化允许使用模板替换，但此时仅将str模板转换，如果本身已经是列表，其内部的模板则不做处理，等到执行其内部去转换
        这样做的目的是万一用例失败重跑，测试数据不会冲突
        """
        for key, val in data.items():
            if isinstance(val, str):
                args = re.findall("@<(.+?)>", val)

                if args and f"@<{args[0]}>" == val:
                    try:
                        target = eval(args[0], Render.utils)
                    except:
                        pass
                    else:
                        if isinstance(target, list):
                            data[key] = target


class Assist(Entry):
    """
    能力支持
    """

    @classmethod
    def build_func(cls, name: str, extend_fixtures: list):
        """
        创建一个函数
        """
        # 夹具
        fixtures = ["executor"]

        if extend_fixtures:
            fixtures.extend(extend_fixtures)

        source_code = f'def func({",".join(fixtures)}):\n\texecutor.render.fp=locals()\n\texecutor.schedule()'

        # 将code串编译成code对象
        code = compile(source=source_code, filename=name, mode="exec").co_consts[0]

        # 创建函数
        # globals 选项为函数提供全局变量。比如函数内部需要调用其他方法，如果不指定会ERROR
        # locals()/globals() 内置函数分别返回局部(所在局部块，这里就是函数内部作用域)/全局(当前模块)的作用域字典
        function = FunctionType(code=code, globals=globals(), name=name)

        return function

    @classmethod
    def _verify_list(cls, key: str, expect: list, response: list, operate: str = "in"):
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
                        cls._verify_dict(sub_val, item)
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

    @classmethod
    def _verify_dict(cls, expect: dict, response: dict):
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
                    cls._verify_list(key, [value], response, operate=key)

                elif isinstance(value, (list, tuple)):
                    cls._verify_list(key, value, response, operate=key)

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
                        cls._verify_list(key, [sub_val], response)
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
                assert isinstance(response, dict), f"预期的数据类型是 DICT，而不是 {type(response)}"

                if isinstance(value, str) and value.isdigit():
                    value = float(value)
                    response[key] = float(response.get(key, 0))

                assert value == response.get(key), f'\n' \
                                                   f'KEY: {key} \n' \
                                                   f'预期结果: {json.dumps(expect, indent=2, ensure_ascii=False)}\n' \
                                                   f'实际结果: {json.dumps(response, indent=2, ensure_ascii=False)}\n'

            # 如果预期值是list则便利预期列表中的item是否都在实际结果中能找到
            elif isinstance(value, (list, tuple)):
                cls._verify_list(key, value, response.get(key))

            # 如果预期值是dict则再次调用本方法进行递归验证
            elif isinstance(value, dict):
                assert isinstance(response, dict), f'\n' \
                                                   f'预期结果: {json.dumps(expect, indent=2, ensure_ascii=False)}\n' \
                                                   f'实际结果: {json.dumps(response, indent=2, ensure_ascii=False)}\n' \
                                                   f"响应对象实际类型是: {type(response)}，预期类型是 DICT\n"
                cls._verify_dict(value, response.get(key))

    @classmethod
    def verify_result(cls, expect: dict, response: dict):
        """
        处理断言错误信息，过滤掉无用的traceback信息
        """
        try:
            cls._verify_dict(expect, response)
        except AssertionError as e:
            e.__traceback__ = None
            raise e

    @classmethod
    def call(cls, step, order):
        """
        执行请求
        """
        # 获取接口信息
        api = step.get("api")

        # 为请求数据 处理关联 和 动态数据替换
        request = deepcopy(step.get("request"))
        expect = deepcopy(step.get("response", {}))

        # 日志
        log_info = step.get('log', '无当前步骤说明信息，建议补充')

        # 请求类型
        is_http = True

        # http 数据拼接
        if is_http:
            api = cls.im.get(api)

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
            pass

        # 根据调度逻辑处理接口调用和验证
        rule = {"timeout": 0, "interval": 3}
        rule.update(step.get("rule", {}))
        rule["interval"] = max(rule["interval"], 1)
        response = None
        start = 0

        while start <= rule["timeout"]:
            try:

                # 打印用户日志
                retry = start // rule["interval"]
                suffix = f" [retry_times: {retry}] " if retry > 0 else ""
                log.info(f" Step {order}: {log_info}{suffix}")

                # 请求接口
                response = http_request(**api) if is_http else {}

                cls.verify_result(expect, response)

                break
            except Exception as e:
                # 如果是最后一次接口调用就引发异常
                if start > rule["timeout"] - rule["interval"]:
                    raise e

                start += rule["interval"]
                time.sleep(rule["interval"])

        return response or {}


class Executor(Entry):
    """
    用例执行器
    """

    def __init__(self, data: dict, render: Render):
        """
        :param data: 用例数据字典
        :param render: Render
        """
        self.data = data
        self.render = render

    @classmethod
    def request_of(cls, request: SubRequest) -> Optional:
        """
        校验用例的可行性。可行则返回一个Executor实例
        @param request:
        @return:
        """
        data = deepcopy(request.param)
        func_name = request.function.__name__

        # render
        render = Render(data.pop("param", {}))

        # 记录用例描述信息
        meta = data.pop("meta", {})
        meta["params"] = render.cp
        meta["start_time"] = time.strftime('%Y-%m-%d %H:%M:%S')

        [request.node.user_properties.append((key, val)) for key, val in meta.items()]

        # 调用校验勾子
        cls.hooks["pytest_cat_case_validator"](request)

        # 用例开始执行
        log.info(f"执行用例: {func_name} <{meta.get('desc')}>")

        return Executor(data, render)

    def schedule(self):
        """
        用例具体的step在这里调度完成
        """
        # 处理 step 级别的参数化
        origin_steps = self.data["steps"]
        target_steps = []

        for step in origin_steps:
            param = step.pop("param", None)

            if param:
                Render.trans_parameters(param)

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
            # 步骤延迟
            delay = step.get("delay")
            if delay:
                time.sleep(delay)

            # 处理步骤模版参数，转换之后赋值给render
            args = step.pop("step_args", {})
            self.render.trans(args)
            self.render.sp = args

            # 暂存当前接口调用结果到stages
            self.render.r.append(self.invoke(step, idx + 1))

    def invoke(self, step, order):
        """
        执行请求
        """
        # 预期结果在每次请求后再做渲染
        expect = step.pop("response", {})

        # 处理动态数据
        self.render.trans(step)

        # 获取接口信息
        api = self.im.get(step.get("api"))

        # 请求类型
        is_http = True

        # http 数据拼接
        if is_http:
            # 测试数据补充到默认 api 数据中
            for key, val in step.get("request").items():
                if key in api:
                    if key == "url":
                        api["url"] += str(val)
                    elif isinstance(api[key], dict):
                        api[key].update(val)
                    continue
                api[key] = val
        else:
            pass

        # 根据调度逻辑处理接口调用和验证
        rule = {"timeout": 0, "interval": 3}
        rule.update(step.get("rule", {}))
        rule["interval"] = max(rule["interval"], 1)

        # 处理请求参数
        response = None
        start = 0

        # step 日志
        log.info(f"Step {order}: {step.get('desc', '无当前步骤说明信息，建议补充')}")

        while start <= rule["timeout"]:
            try:
                # 请求接口
                response = http_request(**api) if is_http else {}

                # 实时渲染预期结果
                current_expect = {"expect": deepcopy(expect)}
                self.render.trans(current_expect)

                Assist.verify_result(current_expect["expect"], response)

                break
            except Exception as e:
                # 如果是最后一次接口调用就引发异常
                if start > rule["timeout"] - rule["interval"]:
                    raise e

                start += rule["interval"]
                time.sleep(rule["interval"])

                # 重试日志
                log.info(
                    f"Step {order}: {step.get('desc', '无当前步骤说明信息，建议补充')} [ retry_times: {start // rule['interval']} ] ")

        return response or {}
