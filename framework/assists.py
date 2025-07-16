import os
import sys
import gzip
import json
import time

from google.protobuf.json_format import ParseDict, MessageToJson

from framework.values import settings


def gzip_compress(source: bytes):
    compressed_bytes = gzip.compress(source)

    return compressed_bytes


def gzip_decompress(source: bytes):
    decompressed_bytes = gzip.decompress(source)

    return decompressed_bytes


def xor_encrypt(source: bytes, secret_key: str):
    """
    异或加密
    """

    secret_key = secret_key + str(len(source))
    secret_key_bytes = secret_key.encode("utf8")

    if len(source) < len(secret_key_bytes):
        return b""
    else:
        encrypt_seg = [s ^ t for s, t in zip(source, secret_key_bytes)]

    return bytes(encrypt_seg) + source[len(secret_key_bytes):]


def build_data(request_cls, body: dict, gzip=True, encrypt_type="xor", encrypt_key=""):
    """
    构建请求数据
    """
    request = request_cls()

    # 解析字典数据到pb请求对象中
    ParseDict(js_dict=body, message=request)

    # pb对象序列化为字节流（byte），并压缩
    request_bytes = request.SerializeToString()

    # 压缩
    if gzip:
        request_bytes = gzip_compress(request_bytes)

    # 请求数据异或加密
    if encrypt_type == "xor" and encrypt_key:
        request_bytes = xor_encrypt(request_bytes, encrypt_key)

    return request_bytes


def parse_data(response_cls, cipher_bytes, gzip=True, encrypt_type="xor", encrypt_key=""):
    """
    解析PB数据
    """
    response = response_cls()

    # 解密数据
    if encrypt_type == "xor" and encrypt_key:
        cipher_bytes = xor_encrypt(cipher_bytes, encrypt_key)

    # 解压数据
    if gzip:
        cipher_bytes = gzip_decompress(cipher_bytes)

    # 解析流式数据
    response.ParseFromString(cipher_bytes)

    # 转成字典返回
    data = json.loads(MessageToJson(response))

    return data


def flat_dict(d: dict, result=None, prefix: str = ""):
    """
    扁平化处理字典
    此处仅简单处理
    """

    if result is None:
        result = {}

    for k, v in d.items():
        if not isinstance(v, dict):
            result[k if not prefix else ".".join([prefix, k])] = v
        else:
            flat_dict(v, result, k if not prefix else ".".join([prefix, k]))

    return result


def parse_args(line: list = None) -> dict:
    """
    解析命令行参数
    :param line: default sys.argv[1:]
    :return:
    """

    if not line:
        line = sys.argv[1:]

    if not line:
        return {}

    target = dict()
    point = 0

    # 删除无效参数
    tmp = []
    for val in line:
        if isinstance(val, str) and not val.strip():
            continue

        tmp.append(val)
    line = tmp

    if not line[point].startswith("-"):
        raise RuntimeError("命令行参数错误")

    while point < len(line):
        # 找 key
        if line[point].startswith("-"):
            target[line[point].lstrip("-")] = None

            if point + 1 >= len(line):
                break

        # 找 value
        curser = point + 1

        if line[curser].startswith("-"):
            point = curser
            continue

        while True:
            if curser + 1 >= len(line) or line[curser + 1].startswith("-"):
                break

            curser += 1

        if curser - point == 1:
            target[line[point].lstrip("-")] = line[curser]
        elif curser - point > 1:
            target[line[point].lstrip("-")] = line[point + 1: curser + 1]

        point = curser + 1

    return target


def check_path(kws: list, path):
    """
    检查路径关键字是否在node路径中
    """
    tag = False

    for kw in kws:
        if kw in path:
            tag = True
            break

    return tag


class Prepare:
    """
    测试准备
    """

    def __init__(self):
        self.args = flat_dict(settings)
        self.args.update(flat_dict(parse_args()))

        # 设备信息
        self.brands = dict()

    def build_args(self) -> list:
        """
        构建命令行参数
        """

        if not self.args["test.host"]:
            raise RuntimeError("测试环境地址缺失")

        # 默认子进程数
        n = self.args.pop("test.dist", 0)

        # 过滤标签
        mark = self.args.get("test.mark") is not None

        # ================== 命令行汇总 ==================
        # 命令行参数
        cmd = "tests"  # 测试路径
        cmd += f" --capture=sys -v"  # 日志捕获

        cmd += f" --reruns 1 --reruns-delay 5"  # 失败重试
        cmd += f" -n {min(n, os.cpu_count())}" if n > 0 else ""  # 是否分布式执行
        cmd += f" --dist {self.args.pop('test.mode', 'load')}" if n > 0 else ""  # 分布式执行时用例分发方式
        cmd += f" --html report/report.html --self-contained-html"  # 测试报告

        # 其他参数
        cmd_list: list = cmd.split(" ")
        for k, v in self.args.items():
            p = "-" if len(k) == 1 else "--"
            if v is not None:
                cmd_list.append(p + k)
                cmd_list.append(str(v))

        # 单独处理mark
        if mark:
            cmd_list.append("-m")
            cmd_list.append(self.args.pop('test.mark'))

        return cmd_list


def stat_result(session, exitstatus):
    """
    统计测试结果
    """
    # 获取统计报告
    reporter = session.config.pluginmanager.get_plugin('terminalreporter')

    # 用例总数
    total = session.testscollected if session.testscollected else 1

    passed = len(reporter.stats.get('passed', []))
    failed = len(reporter.stats.get('failed', []))
    error = len(reporter.stats.get('error', []))
    skipped = len(reporter.stats.get('skipped', []))
    pass_rate = '%.2f' % (round(((passed + skipped) / total) * 100)) + '%'

    # 执行状态映射
    result_map = {
        0: "通过",
        1: "失败",
        3: "失败",
        2: "中断",
        4: "错误",
        5: "无可用的用例"
    }

    # 结果
    stats = {
        "用例总数": total,
        "通过用例数": passed,
        "失败用例数": failed,
        "错误用例数": error,
        "跳过用例数": skipped,
        "通过率": pass_rate,
        "测试结果": result_map.get(exitstatus, "未知")
    }

    # 测试开始时间和执行时间
    start_time = session.config.getoption("session_start")
    m, s = divmod(int(time.time() - start_time), 60)
    h, m = divmod(m, 60)

    # 装配统计报告
    content = f"<p><span style='font-size:200%; padding-bottom: 0;'>测试结果统计</span> "
    content += f"<p style='padding-top: 0; color: gray;'>" \
               f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))} | " \
               f"执行时长: {h}时 {m}分 {s}秒 | " \
               f"执行人: {session.config.getoption('report.runner')}</p>"

    for key, val in stats.items():
        if key in ("失败用例数", "错误用例数") and val != 0:
            content += f"<p>{key}: <span style='color:red;'>{val}</span></p>"
        elif key == "通过率":
            content += f"<p>{key}: <span style='color:green;'>{val}</span></p>"
        elif key == "测试结果":
            if val == "通过":
                content += f"<p>{key}: <span style='color: green;'>{val}</span></p>"
            else:
                content += f"<p>{key}: <span style='color: red;'>{val}</span></p>"
        else:
            content += f"<p>{key}: {val}</p>"

    return content, stats
