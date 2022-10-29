import random

from faker import Faker
from string import ascii_letters, digits


class Fabricate:
    """
    虚构数据类
    """

    faker = Faker(locale='zh_CN')

    @staticmethod
    def random_str(n: int = 10):
        """
        返回一个随机字符串，默认10位
        :param n:
        :return:
        """
        string = ascii_letters + digits

        return "".join(random.sample(string, n))

    @classmethod
    def random_text(cls, suffix=""):
        """
        随机文本
        :return:
        """
        return cls.faker.sentence().strip(".") + suffix
