import time
import pytest

from py.xml import html

from utils.common import log

"""
设置html报告样式
依赖插件 pytest-html
整个导入到 conftest.py
"""


@pytest.mark.optionalhook
def pytest_html_report_title(report):
    report.title = "测试报告"


@pytest.mark.optionalhook
def pytest_metadata(metadata):
    pass


@pytest.mark.optionalhook
def pytest_html_results_summary(prefix):
    # 统计报告前缀
    pass


@pytest.mark.optionalhook
def pytest_html_results_table_header(cells):
    # 删除link列
    cells.pop(-1)

    # 表头
    cells.insert(3, html.th('Time', class_='sortable time', col='time'))
    cells.insert(4, html.th('用例描述'))
    cells.insert(5, html.th("作者"))
    cells.insert(6, html.th("用例等级"))
    cells.insert(7, html.th("编辑时间"))


@pytest.mark.optionalhook
def pytest_html_results_table_row(report, cells):
    # 删除link列
    cells.pop(-1)

    if report:
        try:
            properties = dict(report.user_properties)
            cells.insert(3, html.td(time.strftime('%Y-%m-%d %H:%M:%S'), class_='col-time'))
            cells.insert(4, html.td(properties.get('desc', "")))
            cells.insert(5, html.td(properties.get('author', "")))
            cells.insert(6, html.td(properties.get('level', "")))
            cells.insert(7, html.td(properties.get('time', "")))
        except Exception as e:
            log.error(str(e))


@pytest.mark.optionalhook
def pytest_html_results_table_html(report, data):
    # 通过的用例不记录日志
    if report.passed:
        pass
        data.clear()
        data.append(html.div("we will not record log for passed case.", class_="empty log"))
