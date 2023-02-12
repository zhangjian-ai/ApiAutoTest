import os
import sys
import pytest

from utils.common import BASE_DIR, load_yaml


def debug(yaml_path, case_name, debug_flag):
    """
    调试工具
    """
    # 检查yaml是否存在
    if not os.path.exists(os.path.join(BASE_DIR, yaml_path)):
        sys.stdout.write(f"\n⚠️ 数据文件不存在: {yaml_path}\n")
        return

    # py文件检查
    target = "tests" + yaml_path.split("data")[1]
    dirname = os.path.join(BASE_DIR, os.path.dirname(target))
    basename = os.path.basename(target).replace(".yaml", ".py")

    py_path = os.path.join(dirname, basename)

    # 是否调试
    if debug_flag:
        cmd = py_path
        if case_name:
            cmd += f"::{case_name}"
        pytest.main(["-s", cmd])
        return

    # 检查目录是否存在，不存在就创建
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    # 检查py文件是否存在，不存在就创建
    if not os.path.exists(py_path):
        with open(py_path, "w", encoding="utf-8") as f:
            # 添加默认导包
            f.write("import pytest\n\n"
                    "from utils.common import rewrite\n\n\n")

    # 不调试用例则默认是要创建case
    cases = load_yaml(os.path.join(BASE_DIR, yaml_path))
    str_list = []

    # 当前py文件的内容
    with open(py_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 指明了case就往文件中追加
    if case_name:
        if case_name not in cases:
            sys.stdout.write(f"\n{yaml_path} 中未找到: {case_name}\n")
            return

        if case_name not in content:
            temp = cases[case_name]["spec"]
            temp["name"] = case_name
            temp["desc"] = cases[case_name]["meta"]["desc"]

            str_list.append(build_case(temp))

        if str_list:
            sys.stdout.write(f"\n{target.replace('.yaml', '.py')} 新增用例: {case_name}\n")
    else:
        keys = []
        for key, case in cases.items():
            temp = case["spec"]
            temp["name"] = key
            temp["desc"] = case["meta"]["desc"]

            keys.append(key)
            str_list.append(build_case(temp))

        # 有可写入的用例才添加导包信息
        if str_list:
            str_list.insert(0, "import pytest\n\n"
                               "from utils.common import rewrite\n\n\n")
            keys = ["\n" + key for key in keys]
            sys.stdout.write(f"\n{target.replace('.yaml', '.py')} 重写用例: \n{''.join(keys)}\n")

    if str_list:
        mode = "a" if case_name else "w"
        with open(py_path, mode, encoding="utf-8") as f:
            for string in str_list:
                f.write(string)

        sys.stdout.write("\n✅ 用例信息更新完成\n")
        return

    sys.stdout.write("\n⚠️ 无用例更新\n")


def build_case(case) -> str:
    """
    构建py中的case
    返回str
    """
    string = ""

    # mark
    marks = case.get("marks")
    if marks:
        for mark in marks:
            string += f"@pytest.mark.{mark}\n"

    # 函数
    string += f'@rewrite()\ndef {case.get("name")}():\n    """{case.get("desc")}"""\n    pass\n\n\n'

    return string
