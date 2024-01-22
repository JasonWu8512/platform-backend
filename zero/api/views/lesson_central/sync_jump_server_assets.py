# -*- coding: utf-8 -*-
"""
@Time    : 2021/5/14 6:08 下午
@Author  : Demon
@File    : sync_jump_server_assets.py
"""

# 同步jumpserver账户的服务器资产
import requests

class JumpServer():
    BASEURL = 'http://jumpserver.jiliguala.com'
    def __init__(self):
        self.session = requests.session()
        self.api_login()

    def api_login(self):
        url = f'{self.BASEURL}/auth/login/'
        data = {
            'csrfmiddlewaretoken': 'XxefSMgC2JFGFRXCuyL1ZwczIYiG2KUGBzaookJy45q9itaaknZ3QFalQIeYOozT',
            'username': 'demon_jiao',
            'password': 'demon_jiao'
        }
        response = self.session.post(url=url, json=data)
        # print(response.text)
        print(response.cookies)
        return

    def api_first_login(self):
        url = f'{self.BASEURL}/users/first-login/'
        response = self.session.get(url=url, )
        print(response.text)

if __name__ == '__main__':
    js = JumpServer()
    js.api_first_login()
