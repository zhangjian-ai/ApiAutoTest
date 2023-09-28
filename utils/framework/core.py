"""
@Project: api-auto-test
@File: core.py
@Author: Seeker
@Date: 2023/7/8 3:04 下午
"""
import os
from copy import deepcopy

from abc import abstractmethod

from utils.framework.open.entry import Entry
from config.settings import API_IMP, API_FILE, BASE_DIR
from utils.framework.loads import load_interface_from_dir, load_module_attrs


class InterfaceManager:
    """
    接口管理类
    """
    __slots__ = ["products", "attrs"]

    class Interface:
        """
        内部类
        """
        __slots__ = ["name", "apis"]

        def __init__(self, name: str, apis: dict):
            self.name = name
            self.apis = apis

        def __getattribute__(self, item):
            if item in ["name", "apis"]:
                return object.__getattribute__(self, item)

            if item not in self.apis:
                raise RuntimeError(f"当前产品 {self.name} 中没有配置接口 {item}")

            return deepcopy(self.apis[item])

    def __init__(self):
        # 接口管理类同时管理多个产品的接口实例
        self.products = {}

        # 校验api配置
        if (API_FILE and API_IMP) or (not API_FILE and not API_IMP):
            raise RuntimeError(f"api配置冲突，请检查 settings 配置文件")

        if API_FILE:
            for conf in API_FILE:
                self.products[conf["product"]] = \
                    InterfaceManager.Interface(name=conf["product"],
                                               apis=load_interface_from_dir(os.path.join(BASE_DIR, conf["path"])))

        if API_IMP:
            self.attrs = load_module_attrs(API_IMP)

    def __getattribute__(self, item):
        if item in ["products", "attrs"]:
            return object.__getattribute__(self, item)

        # 分解item
        try:
            product, interface = item.split(".")
        except ValueError:
            product = item
            interface = None

        if product not in self.products:
            raise RuntimeError(f"无效产品名称: {product}，请检查 settings 配置文件")

        return getattr(self.products[product], interface) if interface else self.products[product]
