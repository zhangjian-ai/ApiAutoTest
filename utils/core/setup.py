import os

from copy import deepcopy

from utils.common import load_yaml, API_DIR


class InterfaceManager:
    """
    接口管理类
    """
    __slots__ = ["config", "apis"]

    class Interface:
        """
        内部类
        """
        __slots__ = ["name", "api", "config", "cookies"]

        def __init__(self, name: str, api: dict, config):
            self.name = name
            self.api = api
            self.config = config
            self.cookies = {}

        def __getattribute__(self, item):
            if item in ["name", "api", "config", "cookies"]:
                return object.__getattribute__(self, item)

            data = deepcopy(self.api[item])

            # 这里处理api。比如：绑定 host、port；添加 cookie、header 等

            return data

    def __init__(self, config):
        """
        :param config: pytest 内置 config 对象
        """
        self.config = config
        self.apis = {}

        # 加载接口配置
        root, _, files = os.walk(API_DIR).__next__()

        for file in files:
            if not file.endswith(".yaml") and not file.endswith(".yml"):
                continue

            # 主站名字
            name = file.split(".", 1)[0]

            # 每个主站对应一个interface实例
            self.apis[name] = InterfaceManager.Interface(name, load_yaml(os.path.join(API_DIR, file)), config)

    def __getattribute__(self, item):
        if item in ["config", "apis"]:
            return object.__getattribute__(self, item)

        # 分解item
        variables = item.split(".")

        if len(variables) == 2:
            name, api_name = variables
        else:
            raise RuntimeError(f"非法的api，请检查本用例的 api 字段")

        if name not in self.apis:
            raise RuntimeError(f"{name}.yaml: 没有这样的接口文档")

        return getattr(self.apis[name], api_name)

