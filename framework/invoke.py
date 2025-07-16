import json
import requests
import traceback

from framework.logger import log
from framework.assists import build_data, parse_data


def http_request(url, method="POST", data: dict = None, params: dict = None, headers: dict = None, cookies: dict = None,
                 verify=False, stream=False) -> dict:
    """
    二次封装 http request 方法
    """

    # 为POST请求处理Content-Type
    if method.upper() == "POST":
        if headers is None:
            headers = {}

        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

    # 日志打印
    log.info(f'请求地址: {url}')
    log.info(f'请求方式: {method}')
    log.info(f'请求头: {headers}')
    log.info(f'查询参数: {params}')
    log.info(f'表单参数: {data}')

    # 处理data数据
    if data and method.upper() == "POST" and 'json' in headers.get("Content-Type"):
        data = json.dumps(data)

    try:
        response = requests.request(method, url, data=data, params=params,
                                    headers=headers, cookies=cookies, verify=verify, stream=stream)
        res = None
        try:
            log.info(f'状态码: {response.status_code}')
            res = response.json()
        except Exception as e:
            if "Content-Disposition" not in response.headers:
                log.error(f"响应结果解析异常: {str(e)}")
                log.error(f"响应文本: {response.text}")

        if res:
            res["status_code"] = response.status_code

        else:
            # response.json() 解析异常时，单独构建响应结果
            res = {"status_code": response.status_code}

        log.info(f'响应结果: {res}')

        return res

    except Exception as e:
        log.error(f'http 请求异常: {traceback.format_exc()}')
        raise e


def htpb_request(url, req, resp, gzip=True, encrypt_type="xor", encrypt_key="", method="POST",
                 data: dict = None, params: dict = None, headers: dict = None, cookies: dict = None,
                 verify=False, stream=False) -> dict:

    log.info(f'请求地址: {url}')
    log.info(f'请求方式: {method}')
    log.info(f'请求头: {headers}')
    log.info(f'查询参数: {params}')
    log.info(f'表单参数: {data}')

    # 构建数据
    data = build_data(req, data, gzip=gzip, encrypt_type=encrypt_type, encrypt_key=encrypt_key)

    # 发起请求
    try:
        response = requests.request(method, url, data=data, params=params,
                                    headers=headers, cookies=cookies, verify=verify, stream=stream)

        # 处理流式及非流式请求
        if stream:
            res = {"chunks": []}
            resp_bytes = b""
            for chunk in response.iter_content(8192):
                resp_bytes += chunk

            pre = 0
            chunks = []

            for i in range(len(resp_bytes)):
                if resp_bytes[i] == 0x00 or resp_bytes[i] == 0x01 or resp_bytes[i] == 0x02:
                    if len(resp_bytes) > i + 2 and resp_bytes[i + 1] == 0x00 and resp_bytes[i + 2] == 0x00:
                        chunks.append(resp_bytes[pre:i + 3])
                        pre = i + 3

                if i + 3 == len(resp_bytes):
                    if pre != i + 3:
                        chunks.append(resp_bytes[pre:i + 3])
                    break

            for chunk in chunks:
                res["chunks"].append(parse_data(resp, chunk, gzip=gzip, encrypt_type=encrypt_type, encrypt_key=encrypt_key))

        else:
            res = parse_data(resp, response.content, gzip=gzip, encrypt_type=encrypt_type, encrypt_key=encrypt_key)

        if res:
            res["status_code"] = response.status_code

        else:
            # response.json() 解析异常时，单独构建响应结果
            res = {"status_code": response.status_code}

        log.info(f'响应结果: {res}')

        return res

    except Exception as e:
        log.error(f'htpb 请求异常: {traceback.format_exc()}')
        raise e

