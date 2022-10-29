import yaml


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
