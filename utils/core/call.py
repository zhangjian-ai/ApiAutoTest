import re
import time
import pytest

from copy import deepcopy
from jsonpath import jsonpath

from utils import factory
from utils.common import log, Singleton
from utils.common import http_request, verify


class Executor(metaclass=Singleton):
    """
    用例执行器
    """
    # 工厂数据对象
    ds = vars(factory)

    def __init__(self, request, record_property):
        self.im = request.config.im
        self.data = request.param
        self.config = request.config
        self.func = request.function.__name__
        self.record_property = record_property

        # 工厂数据
        self.factory = Executor.ds

        # 用例 参数化变量
        self.args = deepcopy(self.data.get("param", {}))
        Executor.factory_replace(self.args)

        # 校验用例是否可执行
        self.inspect()

        # step 参数化变量
        self.step_args = None

        # 记录每一个step的响应结果，供关联模版使用
        self.stages = []

    def inspect(self):
        """
        用例开始前的审查工作
        """
        # 绑定用例信息
        info = deepcopy(self.data.get("info", {}))
        self._replace_(info)
        [self.record_property(key, val) for key, val in info.items()]

        # 用例开始执行
        log.info(f"执行用例: {self.func} <{info.get('description')}>")

        # 判断skip
        spec = deepcopy(self.data.get("spec", {}))
        self._replace_(spec)
        skips = spec.get("skips", [])
        if self.config.getoption("branch") in skips:
            log.warning(f"分支<{self.config.getoption('branch')}> 已限制用例 <{self.func}> 不执行")
            pytest.skip(f"分支<{self.config.getoption('branch')}> 已限制用例 <{self.func}> 不执行")

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
                Executor.factory_replace(param)

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
            # 获取接口信息
            api = getattr(self.im, step.get("api"))

            # 处理步骤模版参数
            self.step_args = step.pop("step_args", {})
            self._replace_(self.step_args)
            self._step_replace_(step)

            # 处理其他模版参数
            self._replace_(step)

            # 打印用户自定义日志
            log.info(f"Step {idx + 1}: {step.get('log', '未填写step描述信息，建议补充')}")

            # 为请求数据 处理关联 和 动态数据替换
            request = deepcopy(step.get("request"))
            expect = deepcopy(step.get("response", {}))

            # 测试数据替换默认的api数据
            for key, val in request.items():
                if key in api:
                    if key == "url":
                        api["url"] += str(val)

                    elif isinstance(api[key], dict):
                        api[key].update(val)

                    continue

                api[key] = val

            # 根据调度逻辑处理接口调用和验证
            rule = {"timeout": 0, "interval": 3}
            rule.update(step.get("rule", {}))
            response = None
            start = 0

            while start <= rule["timeout"]:
                try:
                    # 请求接口
                    response = http_request(**api)

                    verify(expect, response)
                    break
                except Exception as e:
                    # 如果是最后一次接口调用就引发异常
                    if start > rule["timeout"] - rule["interval"]:
                        raise e

                    start += rule["interval"]
                    time.sleep(rule["interval"])

            # 暂存当前接口调用结果到stages
            self.stages.append(response)

    def _replace_(self, data):
        """
        处理前后接口关联、资源库函数替换
        """
        if isinstance(data, dict):
            # 增加处理 sign 签名的逻辑
            sign = data.pop("sign", None)

            for key, val in data.items():
                if isinstance(val, (int, float)):
                    continue
                elif isinstance(val, str):
                    # 替换规则前提是val是一个字符串
                    data[key] = self._magic_(val)
                else:
                    # 不是 int、str 则默认只能是 list、dict
                    self._replace_(val)

            # 处理签名
            if sign is not None:
                if isinstance(sign, str):
                    self.factory['data'] = data
                    data["sign"] = self._magic_(sign)
                else:
                    data["sign"] = sign

        elif isinstance(data, list):
            for idx, val in enumerate(data):
                if isinstance(val, (int, float)):
                    continue
                elif isinstance(val, str):
                    data[idx] = self._magic_(val)
                else:
                    self._replace_(val)
        else:
            pytest.fail(f"动态替换方法入参类型错误: {type(data)}， 默认只接受 LIST、DICT")

    def _magic_(self, origin: str) -> str:
        """
        字符串替换
        """
        relates = re.findall("@<(.+?)>", origin)
        funcs = re.findall("!<(.+?)>", origin)
        args = re.findall("%<(.+?)>", origin)

        # 关联数据替换
        for relate in relates:
            idx, pat = relate.split(",", 1)
            idx = int(idx.strip())

            if idx >= len(self.stages):
                pytest.fail(f"关联取值的索引超范围: {idx}")

            matches = jsonpath(self.stages[idx], pat.strip())

            if not matches:
                pytest.fail(f"关联失败: {relate}，请检查 未知参数/jsonpath 是否都正确")

            val = matches[0]

            # 如果原始字符串仅仅是一个模版表达式，则直接返回目标值
            if f"@<{relate}>" == origin:
                return val

            # 否则就用target替换原字符串中的模版表达式
            origin = origin.replace(f"@<{relate}>", str(val))

        # 工厂方法数据替换
        for func in funcs:
            val = eval(func, self.factory)

            if f"!<{func}>" == origin:
                return val

            origin = origin.replace(f"!<{func}>", str(val))

        # 参数数据
        for arg in args:

            if not self.args:
                pytest.fail(f"当前用例未配置参数化，请检查模版是否使用正确")

            if arg not in self.args:
                pytest.fail(f"{arg}: 当前 用例 未找到该变量的参数配置")

            val = self.args[arg]

            if f"%<{arg}>" == origin:
                return val

            origin = origin.replace(f"%<{arg}>", str(val))

        return origin

    def _step_replace_(self, data):
        """
        处理 step 内部参数化逻辑
        """

        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, (int, float)):
                    continue
                elif isinstance(val, str):
                    data[key] = self._step_magic_(val)
                else:
                    self._step_replace_(val)
        elif isinstance(data, list):
            for idx, val in enumerate(data):
                if isinstance(val, (int, float)):
                    continue
                elif isinstance(val, str):
                    data[idx] = self._step_magic_(val)
                else:
                    self._step_replace_(val)
        else:

            pytest.fail(f"动态替换方法入参类型错误: {type(data)}， 默认只接受 LIST、DICT")

    def _step_magic_(self, origin: str) -> str:
        """
        单独处理 step 的替换逻辑
        """
        args = re.findall("~<(.+?)>", origin)

        # 关联数据
        for var in args:
            if var not in self.step_args:
                pytest.fail(f"{var}: 当前 step 未找到该变量的参数配置")

            val = self.step_args[var]

            if f"~<{var}>" == origin:
                return val

            origin = origin.replace(f"~<{var}>", str(val))

        return origin

    @staticmethod
    def factory_replace(data):
        """
        参数化 对象 前置工厂数据替换
        """
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, (int, float)):
                    continue
                elif isinstance(val, str):
                    data[key] = Executor.factory_magic(val)
                else:
                    Executor.factory_replace(val)

        elif isinstance(data, list):
            for idx, val in enumerate(data):
                if isinstance(val, (int, float)):
                    continue
                elif isinstance(val, str):
                    data[idx] = Executor.factory_magic(val)
                else:
                    Executor.factory_replace(val)
        else:
            pytest.fail(f"动态替换方法入参类型错误: {type(data)}， 默认只接受 LIST、DICT")

    @staticmethod
    def factory_magic(origin: str):
        funcs = re.findall("!<(.+?)>", origin)

        # 工厂方法数据替换
        for func in funcs:
            val = eval(func, Executor.ds)

            if f"!<{func}>" == origin:
                return val

            origin = origin.replace(f"!<{func}>", str(val))

        return origin

    @staticmethod
    def parameter_replace(data: dict):
        """
        针对用例参数化做特殊处理
        参数的key可以是一个str，满足模版的工厂方法
        """
        for key, val in data.items():
            if isinstance(val, str) and val.startswith("!<") and val.endswith(">"):
                data[key] = Executor.factory_magic(val)
