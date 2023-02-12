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
            data["url"] = f"{self.config.getoption('host')}:{self.config.getoption('port')}{data['url']}"

            return data

    def __init__(self, config):
        """
        :param config: pytest 内置 config 对象
        """
        self.config = config
        self.apis = {}

        # 加载接口配置，api 文件夹中每个目录表示一个服务
        root, dirs, _ = os.walk(API_DIR).__next__()

        # 遍历每个项目
        for d in dirs:
            api = {}
            ds = [os.path.join(root, d)]

            while len(ds) > 0:
                cur = ds.pop(0)

                abs_path, sub_dirs, files = os.walk(cur).__next__()

                # 处理当前文件夹的文件
                for file in files:
                    if not file.endswith(".yaml") and not file.endswith(".yml"):
                        continue

                    api.update(load_yaml(os.path.join(abs_path, file)))

                # 处理子目录
                for sub in sub_dirs:
                    ds.append(os.path.join(abs_path, sub))

            # 每个服务对应一个interface实例
            self.apis[d] = InterfaceManager.Interface(d, api, config)

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
