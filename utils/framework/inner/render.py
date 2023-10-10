import re
import pytest

from utils.framework.open.entry import Entry


class Render(Entry):
    """
    处理原始测试数据中的模版语法
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
            # 增加处理 sign 签名的逻辑
            sign = data.pop("sign", None)

            for key, val in data.items():
                if not val or isinstance(val, (int, float)):
                    continue
                elif isinstance(val, str):
                    data[key] = self._magic_(val)
                else:
                    self.trans(val)

            # 处理签名
            if sign is not None:
                if isinstance(sign, str):
                    self.sp['data'] = data
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
            target = eval(arg, dict(**self.source, **params))

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
                        target = eval(args[0], Render.source)
                    except:
                        pass
                    else:
                        if isinstance(target, list):
                            data[key] = target

    @staticmethod
    def render_string(string: str):
        """
        按照框架规则替换命令行参数到字符串
        规则：字符串中 {xxx} 部分将被替换，如果 xxx 是命令行参数的话
        """
        args = re.findall(r"\{(.+?)\}", string)
        for arg in args:
            new = Render.config.getoption(arg)
            if new:
                string = string.replace("{" + arg + "}", new)

        return string
