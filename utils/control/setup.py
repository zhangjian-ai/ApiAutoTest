"""
@Project: api-auto-test
@File: control.py
@Author: Seeker
@Date: 2023/7/9 12:34 下午
"""
from utils.framework.core import Setup


class MySetup(Setup):
    """
    自定义前置类
    """

    def before(self):
        for product in self.config.im.products.keys():
            if product == "httpbin":
                p = getattr(self.config.im, product)
                for api in p.apis.values():
                    api["url"] = f"{self.config.getoption('host')}:{self.config.getoption('port')}{api['url']}"







