import os
import threading

from copy import deepcopy
from collections import defaultdict

from config.settings import API_FILE, BASE_DIR
from utils.framework.inner.loads import load_interface_from_dir


class InterfaceManager:
    """
    接口管理类
    """
    __slots__ = ["products"]

    class Interface:
        """
        内部类
        """
        __slots__ = ["name", "apis"]

        def __init__(self, name: str, apis: dict):
            self.name = name
            self.apis = apis

        def get(self, item) -> dict:
            if item in ["name", "apis"]:
                return object.__getattribute__(self, item)

            if item not in self.apis:
                raise RuntimeError(f"当前产品 {self.name} 中没有配置接口 {item}")

            return deepcopy(self.apis[item])

    def __init__(self):
        # 接口管理类同时管理多个产品的接口实例
        self.products = {}

        # 校验api配置
        if not API_FILE:
            raise RuntimeError(f"API_FILE 配置错误，请检查 settings 文件")

        if API_FILE:
            for conf in API_FILE:
                self.products[conf["product"]] = \
                    InterfaceManager.Interface(name=conf["product"],
                                               apis=load_interface_from_dir(os.path.join(BASE_DIR, conf["path"])))

    def get(self, item) -> dict or Interface:
        if item in ["products"]:
            return object.__getattribute__(self, item)

        # 分解item
        try:
            product, interface = item.split(".")
        except ValueError:
            product = item
            interface = None

        if product not in self.products:
            raise RuntimeError(f"无效产品名称: {product}，请检查 settings 配置文件")

        return self.products[product].get(interface) if interface else self.products[product]


class Singleton(type):
    """
    单例元类
    """
    __lock = threading.Lock()
    __instances = defaultdict()

    def __call__(cls, *args, **kwargs):
        # 根据调用方、调用参数生成一个唯一的key
        key = cls.__name__ + str(args) + str(kwargs)

        # 加锁，判断当前key是否已有实例
        with Singleton.__lock:
            if key not in Singleton.__instances:
                Singleton.__instances[key] = super(Singleton, cls).__call__(*args, **kwargs)

        return Singleton.__instances[key]
