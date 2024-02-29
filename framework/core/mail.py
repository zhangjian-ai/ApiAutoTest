import os
import smtplib

from email.utils import formataddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from framework.open.logger import log


class Mail:
    """
    邮件
    需要使用 pytest config 对象
    """

    @classmethod
    def send_mail(cls, config, content, annex_files: list = None):
        # 参数处理，部分默认值需要填写
        smtp_server = config.get("smtp_server")
        ssl_port = config.get("ssl_port")
        sender_name = config.get("from_name")
        from_addr = config.get("email_sender")
        password = config.get("email_password")

        subject = f"{config.get('subject')} [{config.get('start_time')}]"
        recipients = config.get("email_receiver")

        if not all([smtp_server, ssl_port, sender_name, from_addr, password, recipients, subject]):
            log.warning("邮件参数配置缺失，测试报告已保存到 report 目录。")
            return

        try:
            # 链接邮件服务器
            smtp = smtplib.SMTP_SSL(host=smtp_server, port=ssl_port)
            smtp.login(user=from_addr, password=password)

            # 创建邮件实例
            msg = cls.mail_instance(sender_name, from_addr, content, recipients, subject, annex_files)

            # 发送邮件
            smtp.sendmail(msg["From"], msg["To"].split(","), msg=msg.as_bytes())
            log.info("📧 测试报告已发送")

        except smtplib.SMTPException as e:
            log.error(f"❌ 邮件发送失败: {str(e)}")

    @classmethod
    def mail_instance(cls, sender_name: str, from_addr: str, content: str,
                      recipients: str = None, subject: str = None, annex_files: list = None):
        """
        返回一个邮件实例对象
        :param sender_name:
        :param from_addr:
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
