# -*- coding: utf-8 -*-
# @Time    : 2021/3/1 10:11 上午
# @Author  : zoey
# @File    : qiwei.py
# @Software: PyCharm
import requests
import json
import functools
from retry import retry
import logging

corpid = 'wwe4bdd14a319a8407'
corpsecret = 'UCcqURjN9csjnQn0bOi5Kf8XCLcuYS5TfaZRt3VGvUw'


def valid_login(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kw):
        res = func(self, *args, **kw)
        if res['errcode'] == 40014:
            self.access_token = fetch_access_token()
            res = func(*args, **kw)
        return res

    return wrapper

@retry(tries=10, delay=1)
def fetch_access_token():
    data = {
        'corpid': corpid,
        'corpsecret': corpsecret
    }
    res = requests.get(url='https://qyapi.weixin.qq.com/cgi-bin/gettoken', params=data).json()
    return res['access_token']


"""企业微信组织架构API， https://open.work.weixin.qq.com/api/doc/90000/90135/90201"""
class QiWei():

    url = 'https://qyapi.weixin.qq.com/cgi-bin'
    session = requests.Session()

    def __init__(self):
        self.access_token = fetch_access_token()



    @retry(tries=10, delay=1)
    @valid_login
    def _get(self, path, **data):
        data = {k: v for k, v in data.items() if v}
        data = {
            "access_token": self.access_token,
            **data
        }
        response = self.session.get(self.url + path, params=data)
        response.raise_for_status()
        data = response.json()
        if data['errcode'] == 0:
            logging.error(data['errmsg'])
        return data

    @retry(tries=10, delay=1)
    @valid_login
    def _post(self, path, **data):
        data = {k: v for k, v in data.items() if v}
        res = self.session.post(self.url + path + f'?access_token={self.access_token}', data=data)
        res.raise_for_status()
        data = res.json()
        if data['errcode'] == 0:
            logging.error(data['errmsg'])
        return data

    def create_user(self, userid: str, username:str, department: list, gender: int, email: str, mobile: str, main_department: int, **kwargs):
        """
        创建成员
        :param userid: 成员UserID。对应管理端的帐号，企业内必须唯一。不区分大小写，长度为1~64个字节。只能由数字、字母和“_-@.”四种字符组成，且第一个字符必须是数字或字母。
        :param username: 成员名称。长度为1~64个utf8字符
        :param department:成员所属部门id列表,不超过100个
        :param gender:性别。1表示男性，2表示女性
        :param email:邮箱。长度6~64个字节，且为有效的email格式。企业内必须唯一，mobile/email二者不能同时为空
        :param mobile:手机号码。企业内必须唯一，mobile/email二者不能同时为空
        :param main_department:
        :return:主部门
        """
        body = {
            "userid": userid,
            "username": username,
            "department": department,
            "gender": gender,
            "email": email,
            "mobile": mobile,
            "main_department": main_department,
            **kwargs
        }
        res = self._post(path='/user/create', **body)
        return res

    def get_user(self, userid):
        """
        获取成员
        :param userid:
        :return:
        """
        body = {'userid': userid}
        res = self._get(path='/user/get', **body)
        return res

    def delete_user(self, userid):
        """
        删除成员
        :param userid:
        :return:
        """
        body = {'userid': userid}
        res = self._get(path='/user/delete', **body)
        return res

    def get_user_list_by_department(self, department: int, fetch_child: int = 1):
        """
        获取部门成员详情
        :param department:
        :param fetch_child: 1/0：是否递归获取子部门下面的成员
        :return:
        """
        body = {
            'department': department,
            'fetch_child': fetch_child
        }
        res = self._get('/user/list', **body)
        return res

    def create_department(self, name: str, parentid: int, name_en: str = None, order: int = None):
        """
        创建部门
        :param name: 部门名称同一个层级的部门名称不能重复。长度限制为1~32个字符，字符不能包括\:?”<>｜
        :param name_en: 英文名称。同一个层级的部门名称不能重复。需要在管理后台开启多语言支持才能生效。长度限制为1~32个字符，字符不能包括\:?”<>｜
        :param parentid: 父部门id
        :param order: 在父部门中的次序值。order值大的排序靠前。有效的值范围是[0, 2^32)
        :return:
        """
        body = {
            'name': name,
            'name_en': name_en,
            'parentid': parentid,
            'order': order
        }
        res = self._post(path='/department/create', **body)
        return res

    def update_department(self, id: int, name: str = None, parentid: int = None, name_en: str = None, order: int=None):
        """
        更新部门
        :param id:
        :param name: 部门名称同一个层级的部门名称不能重复。长度限制为1~32个字符，字符不能包括\:?”<>｜
        :param name_en: 英文名称。同一个层级的部门名称不能重复。需要在管理后台开启多语言支持才能生效。长度限制为1~32个字符，字符不能包括\:?”<>｜
        :param parentid: 父部门id
        :param order: 在父部门中的次序值。order值大的排序靠前。有效的值范围是[0, 2^32)
        :return:
        """

    def delete_department(self, id):
        """
        删除部门
        :param id: 部门id
        :return:
        """
        body = {
            'id': id,
        }
        res = self._get(path='/department/delete', **body)
        return res

    def get_department_list(self, id: int = None):
        """
        获取部门列表
        :param id: 部门id。获取指定部门及其下的子部门（以及及子部门的子部门等等，递归）。 如果不填，默认获取全量组织架构
        :return:
        """
        body = {
            "id": id,
        }
        res = self._get(path='/department/list', **body)
        return res




qiwei = QiWei()
qiwei.get_department_list()

