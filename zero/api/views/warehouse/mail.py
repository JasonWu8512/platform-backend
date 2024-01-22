# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/7 4:35 下午
@Author  : Demon
@File    : mail.py
"""

# -*-coding:utf-8 -*-
import os
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
#kcc项目jmeter接口回归报告发送
class SendMailProject(object):
    def __init__(self):
        self.msg_from = '3414474690@qq.com'
        # 客户端授权码
        self.passwd = 'goybmvpsglmucjfa'
    def f(self, fi):
        self.__createFile(fi)
    def __createContent(self, mail_body):
        '''处理正文'''

        return mail_body
    def __createFile(self, extra_file):
        '''处理附件'''
        sendFile = MIMEApplication(open(dat, 'rb').read())
        sendFile["Content-Type"] = 'application/octet-stream'
        # 以下代码可以重命名附件为hello_world.txt
        sendFile.add_header('Content-Disposition', 'attachment')
        return sendFile
    def __createPng(self, png_file):
        img_file = open(png_file, 'rb').read()
        image = MIMEImage(img_file)
        image.add_header('Content-ID', '<image1>')
        # 如果不加下边这行代码的话，会在收件方方面显示乱码的bin文件，下载之后也不能正常打开
        image["Content-Disposition"] = 'attachment; filename="red_people.png"'
        return image
    def sendMail(self, subject, content, receive_mail, cc_mail=None, extra_file=None, png_file=None):
        # msg_to = ';'.join(receive_mail)
        #Jenkins构建jmeter脚本测试报告
        msg = MIMEMultipart(_charset='utf-8', _subtype='mixed')
        msg['From'] = self.msg_from
        msg['To'] = ';'.join(receive_mail)
        if cc_mail:
            msg['Cc'] = ';'.join(cc_mail)
        msg['Subject'] = subject   # 主题

        text_sub = MIMEText(content, 'plain', 'utf-8')   # 文本
        msg.attach(text_sub)
        # 超文本
        # 附件、图片
        if png_file:
            msg.attach(self.__createPng(png_file))
        if extra_file:
            msg.attach(self.__createFile(extra_file))
        try:
            sftp_obj = smtplib.SMTP_SSL("smtp.qq.com", 465)
            # QQ邮件服务
            # s = smtplib.SMTP_SSL("smtp.163.com",465)
            # 网易163邮件服务
            sftp_obj.login(self.msg_from, self.passwd)
            # 登陆
            sftp_obj.sendmail(self.msg_from, receive_mail, msg.as_string(), )
            # 发送邮件
            sftp_obj.quit()
        except Exception as e:
            print('sendemail failed next is the reason\n>>>', e)

def main(title="", content=""):
    title = '邮件发送'
    content = content if content else '临时使用邮件转发'
    extra_file = [r'f:/pyFile/育儿网口碑品牌SaaS关键词-10.xls', r'f:/pyFile/育儿网口碑品牌SaaS关键词-11.xls']
    receive_mail = ['Demon_jiao@jiliguala.com']
    cc_mail = []
    # 目前只支持发送一个邮箱，可循环
    smp = SendMailProject()

    smp.sendMail(subject=title, content=content, cc_mail=cc_mail, receive_mail=receive_mail, )

if __name__ == "__main__":
    main()