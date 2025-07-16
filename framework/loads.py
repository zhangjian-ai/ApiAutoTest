import os
import yaml

from framework.logger import log


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


def load_case(target_dir) -> dict:
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
                val.get("meta", {})["origin"] = file_path.split("testcases", 1)[1]

            all_data[file] = details

    del all_case_name

    # 整理所有用例
    [all_case.update(item) for item in all_data.values()]

    del all_data
    return all_case
