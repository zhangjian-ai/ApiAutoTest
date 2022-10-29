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

    def __init__(self, config, steps: list):
        self.im = config.im
        self.steps = steps

        # 工厂对象字典
        self.factory = vars(factory)

        # 记录每一个step的响应结果，以备后续接口关联调用
        self.stages = []

    def schedule(self):
        """
        用例具体的step在这里调度完成
        """
        # 按步骤依次调度
        for idx, step in enumerate(self.steps):
            # 获取接口信息
            api = getattr(self.im, step.get("api"))

            # 打印用户自定义日志
            log.info(f"Step {idx + 1}: {step.get('log', '未填写step描述信息，建议补充')}")

            # 为请求数据 处理关联 和 动态数据替换
            request = deepcopy(step.get("request"))
            expect = deepcopy(step.get("response", {}))

            # 将 request 的 data 放到 factory，以生成签名
            self.factory['data'] = request.get("data")

            self._replace_(request)
            self._replace_(expect)

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
                except AssertionError as e:
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
            for key, val in data.items():
                if isinstance(val, int):
                    continue
                elif isinstance(val, str):
                    # 替换规则前提是val是一个字符串
                    data[key] = self._magic_(val)
                else:
                    # 不是 int、str 则默认只能是 list、dict
                    self._replace_(val)

        elif isinstance(data, list):
            for idx, val in enumerate(data):
                if isinstance(val, int):
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
        target = None
        relations = re.findall("^.*@<(.+?)>.*$", origin)
        expressions = re.findall("^.*!<(.+?)>.*$", origin)

        # 关联数据
        if relations:
            idx, pat = relations[0].split(",", 1)
            idx = int(idx.strip())

            if idx >= len(self.stages):
                pytest.fail(f"关联取值的索引超范围: {idx}")

            matches = jsonpath(self.stages[idx], pat.strip())

            if not matches:
                pytest.fail(f"关联失败: {relations[0]}，请检查 jsonpath 表达式是否正确")

            target = matches[0]

        # 工厂数据
        elif expressions:
            target = eval(expressions[0], self.factory)

        # 如果原始字符串仅仅是一个模版表达式，则直接返回目标值
        if (origin.startswith("@<") or origin.startswith("!<")) and origin.endswith(">"):
            return target

        # 否则就用target替换原字符串中的模版表达式
        if relations:
            origin = origin.replace(f"@<{relations[0]}>", str(target))
        elif expressions:
            origin = origin.replace(f"!<{expressions[0]}>", str(target))

        return origin
