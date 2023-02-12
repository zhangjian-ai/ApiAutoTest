import time
import pytest

from copy import deepcopy

from utils.common import Magic
from utils.common import log, Singleton
from utils.common import http_request, verify


class Executor(metaclass=Singleton):
    """
    用例执行器
    """

    def __init__(self, request, record_property):
        self.im = request.config.im
        self.data = request.param
        self.config = request.config
        self.func = request.function.__name__
        self.record_property = record_property

        # 工厂数据
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
            # 获取接口信息
            api = getattr(self.im, step.get("api"))

            # 处理步骤模版参数，转换之后赋值给magic
            args = step.pop("step_args", {})
            self.magic.sp.clear()
            self.magic.trans(args)
            self.magic.sp = args

            # 处理其他模版参数
            self.magic.trans(step)

            # 打印用户自定义日志
            log.info(f"Step {idx + 1}: {step.get('desc', '未填写step描述信息，建议补充')}")

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
            self.magic.r.append(response)
