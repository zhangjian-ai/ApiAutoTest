import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from email.mime.base import MIMEBase

from utils.common import log

smtp_server = ''
ssl_port = ''
sender_name = ''
from_addr = ''
password = ''


def send_mail(msg: MIMEBase):
    try:
        smtp = smtplib.SMTP_SSL(host=smtp_server, port=ssl_port)
        smtp.login(user=from_addr, password=password)

        smtp.sendmail(msg["From"], msg["To"].split(","), msg=msg.as_bytes())
        log.info("📧 测试报告已发送")

    except smtplib.SMTPException as e:
        log.error(f"❌ 邮件发送失败: {str(e)}")


def mail_instance(content: str, recipients: str = None,
                  subject: str = None, annex_files: list = None):
    """
    返回一个邮件实例对象
    :param content:
    :param recipients:
    :param subject:
    :param annex_files: 文件路径/(文件名, 文件内容)
    :return:
    """
    # 邮件文本
    content = MIMEText(content, "html", "utf8")

    # 实例化邮件附件
    annexes = []
    if annex_files:
        for file in annex_files:
            if isinstance(file, tuple):
                filename, text = file
            else:
                filename = os.path.basename(file)
                text = open(file, 'rb').read()

            annex_file = MIMEText(text, 'base64', 'utf8')
            annex_file["Content-Type"] = "application/octet-stream"
            annex_file["Content-Disposition"] = f"attachment; filename='{filename}'"
            annexes.append(annex_file)

    # 邮件附件直接配置返回
    if not annexes:
        content["From"] = formataddr((sender_name, from_addr))
        content["To"] = recipients
        content["Subject"] = subject

        return content

    # 需要携带附件
    msg_related = MIMEMultipart('related')

    # 申明一个 可替换媒体类型 的实体来保存文本。以实现对 图片媒体对象的引用
    msg_alternative = MIMEMultipart('alternative')
    msg_alternative.attach(content)

    # 添加文本
    msg_related.attach(msg_alternative)

    # 添加附件
    if annexes:
        for annex in annexes:
            msg_related.attach(annex)

    # 邮件头部信息
    msg_related["From"] = formataddr((sender_name, from_addr))
    msg_related["To"] = recipients
    msg_related["Subject"] = subject

    return msg_related

