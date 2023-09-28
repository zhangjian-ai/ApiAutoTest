import re
import pytest

from config.settings import DATA_FACTORY
from utils.framework.loads import load_module_attrs

# 工厂数据
data_factory = load_module_attrs(DATA_FACTORY)


class Magic:
    """
    处理原始测试数据中的模版语法
    """

    def __init__(self):
        # r对象，应该是一个列表
        self.r = []

        # 用例参数化对象
        self.cp = {}

        # 步骤参数化对象
        self.sp = {}

        # 夹具对象
        self.fp = {}

    def trans(self, data):
        """
        将对象data中模版语法转换成真是数据
        """
        if isinstance(data, dict):
            for key, val in data.items():
                if not val or isinstance(val, (int, float)):
                    continue
                elif isinstance(val, str):
                    data[key] = self._magic_(val)
                else:
                    self.trans(val)

        elif isinstance(data, list):
            for idx, val in enumerate(data):
                if isinstance(val, (int, float)):
                    continue
                elif isinstance(val, str):
                    data[idx] = self._magic_(val)
                else:
                    self.trans(val)
        else:
            pytest.fail(f"trans方法入参类型错误: {type(data)}， 默认只接受 list、dict")

    def _magic_(self, origin):
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
            target = eval(arg, dict(**data_factory, **params))

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
                        target = eval(args[0], data_factory)
                    except:
                        pass
                    else:
                        if isinstance(target, list):
                            data[key] = target
