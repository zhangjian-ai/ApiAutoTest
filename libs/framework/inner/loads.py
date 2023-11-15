import os
import yaml
import importlib

from types import ModuleType
from inspect import isfunction, isclass
from importlib.machinery import SourceFileLoader

from google.protobuf.internal.python_message import GeneratedProtocolMessageType

from config.settings import BASE_DIR
from libs.framework.open.logger import log


def load_yaml(path) -> dict:
    """
    加载yaml文件
    :param path:
    :return:
    """
    if not path.endswith(".yaml") and not path.endswith(".yml"):
        raise TypeError("file type is not 'yaml'.")

    if not os.path.exists(path):
        log.error(f"试图加载一个不存在的文件: {path}")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data or {}


def load_case(target_dir, target: str) -> dict:
    """
    根据目标列表加载数据目录中的文件数据
    如果目标为空，则加载全部
    """
    # 临时字段对象
    all_data = dict()
    all_case = dict()
    all_case_name = list()

    # 先按文件将所有数据加载到临时对象
    for cur_dir, dirs, files in os.walk(target_dir):
        for file in files:
            # 不满足测试文件命名规则的文件直接忽略
            if not file.startswith("test_") or not file.endswith(".yaml"):
                continue

            # 重复文件校验
            if file in all_data:
                raise RuntimeError(f"重复的测试文件名称: {file}")

            file_path = os.path.join(cur_dir, file)
            details = load_yaml(file_path)

            for key, val in details.items():
                # 重复用例名称校验
                if key in all_case_name:
                    raise RuntimeError(f"重复的测试用例名称: {key}")
                all_case_name.append(key)

                # 在用例信息中添加文件名称
                val.get("info", {})["origin"] = file_path.replace(BASE_DIR, "")[1:]

            all_data[file] = details

    del all_case_name

    # 整理所有用例
    [all_case.update(item) for item in all_data.values()]

    # target 为空时，返回所有用例
    if not target:
        del all_data
        return all_case

    # target 不为空时，则从临时数据中挑出需要的数据
    needs = dict()
    for name in target.split(","):
        # 文件
        if name in all_data:
            needs.update(all_data[name])
        elif name in all_case:
            needs.update({name: all_case[name]})
        else:
            raise RuntimeError(f"不存在的测试文件或用例名称: {name}")

    del all_data
    del all_case

    return needs


def load_interface(path: str) -> dict:
    """
    加载路径下所有接口文件中的接口信息
    """

    # 要求路径必须是目录
    if not os.path.isdir(path):
        raise RuntimeError(f"接口文件路径应是一个目录: {path}")

    apis = dict()

    for cur_dir, _, files in os.walk(path):
        for file in files:
            apis.update(load_yaml(os.path.join(cur_dir, file)))

    return apis


def load_yours(modules: str or list) -> dict:
    """
    返回路径下所有类、函数，并注入夹具
    """
    if not modules:
        return {}

    # 先倒入模块
    all_module = []

    if isinstance(modules, str):
        modules = [modules]

    # 找出所有模块
    for m in modules:
        m_path = os.path.join(BASE_DIR, m)

        # 过滤掉无效文件
        if m.startswith("_") and m.endswith(".py"):
            continue

        # 如果是有效py文件则直接创建模块对象
        if not m.startswith("_") and m.endswith(".py"):
            basename = os.path.basename(m_path)
            # 手动构建module对象
            module = SourceFileLoader(basename, path=m_path).load_module(basename)
            all_module.append(module)
            continue

        # 如果不是py则说明是目录，则查找出所有py
        for cur_dir, _, files in os.walk(m_path):
            for file in files:
                if not file.startswith("_") and file.endswith(".py"):
                    module = SourceFileLoader(file, path=os.path.join(cur_dir, file)).load_module(file)
                    all_module.append(module)

    # 将所有模块中的 类、函数 导出
    attrs = dict()
    conftest = importlib.import_module("tests.conftest")
    for module in all_module:
        for attr in dir(module):
            if not attr.startswith("_"):
                unknown = getattr(module, attr)

                # 收集工具类和函数，包含grpc消息类型
                if isclass(unknown) or isfunction(unknown) or isinstance(unknown, GeneratedProtocolMessageType):

                    # 如果是 fixture，则直接注入到 conftest
                    if hasattr(unknown, "_pytestfixturefunction"):
                        setattr(conftest, attr, unknown)
                        continue

                    attrs[attr] = getattr(module, attr)

    return attrs


def load_cls(path: str):
    """
    根据导包路径，返回 类
    """
    module_path, cls_name = path.rsplit(".", 1)

    module = importlib.import_module(module_path)

    if not isinstance(module, ModuleType):
        raise RuntimeError(f"导包路径错误: {path}")

    if not hasattr(module, cls_name):
        raise RuntimeError(f"模块 {module} 中没有要找的类属性: {cls_name}")

    return getattr(module, cls_name)
