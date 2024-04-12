import os
import re
import time

import pytest
import threading

from copy import deepcopy
from collections import defaultdict

from _pytest.config import Config

from framework import BASE_DIR
from framework.core.loads import load_interface


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

    def __init__(self, products: list):
        # 接口管理类同时管理多个产品的接口实例
        self.products = {}

        # 校验api配置
        if not products:
            raise RuntimeError(f"API_FILE 配置错误，请检查 settings 文件")

        for p in products:
            self.products[p["name"]] = \
                InterfaceManager.Interface(name=p["name"],
                                           apis=load_interface(os.path.join(BASE_DIR, p["path"])))

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


def flatten(args: dict or list, prefix="", result: dict = None) -> dict:
    """
    按照规则，将 dict 或 list 处理成一级 dict
    本方法会忽略掉列表中的不可变对象
    dict: 层级的key用 . 拼接
    list: 使用索引表示key
    """
    if result is None:
        result = {}

    if isinstance(args, dict):
        for k, v in args.items():
            cur = ".".join((prefix, k)) if prefix else k
            if isinstance(v, (dict, list)):
                flatten(v, cur, result)
            else:
                result[cur] = v

    elif isinstance(args, list):
        for idx, arg in enumerate(args):
            if isinstance(arg, (dict, list)):
                flatten(arg, f"{prefix}[{idx}]" if prefix else f"[{idx}]", result)

    return result


def replace_args(keys: list, config: Config):
    """
    以keys提供的选项名，替换命令行参数中的引用
    """

    for key in keys:
        if not isinstance(key, str):
                raise RuntimeError("命令行参数的键必须是str类型")

        val: str = config.getoption(key, None)

        if val:
            args = re.findall(r"\$\{(.+?)}", val)

            for arg in args:
                if arg == "time":
                    t = time.strftime('%Y-%m-%d %H:%M:%S')
                elif arg == "timestamp":
                    t = str(time.time())
                else:
                    t = config.getoption(arg, None)

                if t:
                    val = val.replace("${" + arg + "}", t)

        config.option.__setattr__(key, val)
