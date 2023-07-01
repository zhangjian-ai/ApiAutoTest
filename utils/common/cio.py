import os
import yaml

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.__str__()


def load_yaml(path) -> dict:
    """
    加载yaml文件
    :param path:
    :return:
    """
    if not path.endswith(".yaml") and not path.endswith(".yml"):
        raise TypeError("file type is not 'yaml'.")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data


def load_data(target_dir, target_case) -> dict:
    """
    根据目标用例加载数据目录中的文件数据
    如果目标用例为空，则加载全部
    """

    data_source = dict()

    for cur_dir, dirs, files in os.walk(target_dir):
        for file in files:
            abs_path = os.path.join(cur_dir, file)
            details = load_yaml(abs_path)

            # 为用例添加数据源字段
            for val in details.values():
                val.get("meta", {})["origin"] = abs_path.replace(BASE_DIR, "")[1:]

            # 如果目标是整个yaml，则直接返回整个文件的数据
            if target_case == file:
                del data_source
                return details

            for key in details.keys():
                if key in data_source:
                    raise RuntimeError(f"用例名称冲突，项目中不允许存在同名的用例，冲突用例名称: {key}")

                # 如果目标是单个case，则仅返回该case的数据
                if target_case == key:
                    data_source[key] = details[key]
                    return data_source

            data_source.update(details)

    return data_source
