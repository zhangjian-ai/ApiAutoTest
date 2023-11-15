import sys


def set_logger(configure=None):
    if configure is None:
        # 每一行日志打印完，默认换行
        default_format = "\n" \
                         "<cyan><bold>{time:YYYY-MM-DD HH:mm:ss}</bold></cyan> | " \
                         "<level>{level: <7}</level> | " \
                         "<yellow><bold>{function}</bold></yellow>:<blue><bold>{line}</bold></blue> - " \
                         "{message}"

        configure = {
            "handlers": [
                # 控制台打印样式
                # html 报告通过捕获 console 获取日志
                {"sink": sys.stdout, "format": default_format, "level": "INFO", "colorize": True}
            ],
            "extra": {"user": "tester"}
        }

    from loguru import logger
    logger.configure(**configure)

    return logger


# 单例
log = set_logger()
