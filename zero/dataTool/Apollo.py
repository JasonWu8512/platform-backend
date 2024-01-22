# -*- coding: utf-8 -*-
# @Time    : 2021/7/16 2:47 下午
# @Author  : zoey
# @File    : Apollo.py
# @Software: PyCharm
import requests
import functools
from retry import retry
import shortuuid

username = 'qa'
password = 'qa'


@retry(tries=3)
def ace_larkhooks_release_apollo(open_id, appid, namespace, chat_ids=['oc_ff4ac49096858315eb54cf935f36b2c0']):
    for chat_id in chat_ids:
        body = {
            "event": {
                "type": "interactive",
                "card": {
                    "config": {
                        "wide_screen_mode": True,
                        "enable_forward": True,
                    },
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"【阿波罗配置: 发布】"
                        },
                        "template": "orange"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**应用**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n{appid}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**namespace**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n{namespace}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**触发人**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n<at id={open_id}></at> <at id=all></at>" if open_id else "system"
                                    }
                            }]
                        },
                    ]
                },
                "open_id": open_id,
                "open_chat_id": chat_id,
            },
            "uuid": shortuuid.uuid(),
            "token": "zero_jiliguala"
        }
        try:
            res = requests.post('https://ace.jiliguala.com/endpoints/lark/', json=body,
                                headers={'Content-Type': 'application/json'}, verify=False)
            res.raise_for_status()
        except Exception as e:
            raise e


@retry(tries=3)
def ace_larkhooks_edit_apollo(open_id, appid, key, value, namespace, chat_ids=['oc_ff4ac49096858315eb54cf935f36b2c0']):
    for chat_id in chat_ids:
        body = {
            "event": {
                "type": "interactive",
                "card": {
                    "config": {
                        "wide_screen_mode": True,
                        "enable_forward": True,
                    },
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"【阿波罗配置: 更新】"
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**应用**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n{appid}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**namespace**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n{namespace}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**key**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n{key}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**修改后的值**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n{value}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**触发人**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n<at id={open_id}></at> <at id=all></at>" if open_id else "system"
                                    }
                            }]
                        },
                    ]
                },
                "open_id": open_id,
                "open_chat_id": chat_id,
            },
            "uuid": shortuuid.uuid(),
            "token": "zero_jiliguala"
        }
        try:
            res = requests.post('https://ace.jiliguala.com/endpoints/lark/', json=body,
                                headers={'Content-Type': 'application/json'}, verify=False)
            res.raise_for_status()
        except Exception as e:
            raise e


def valid_login(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kw):
        try:
            res = func(self, *args, **kw)
        except ValueError as e:
            if e.args[0] == '请求被重定向':
                ApolloClient.sessionId = fetch_sessionId()
                res = func(self, *args, **kw)
            else:
                raise Exception(e.args[0])
        return res

    return wrapper


@retry(tries=3, delay=1)
def fetch_sessionId():
    """登录获取sessionId,此处放在类变量中"""
    url = "http://apollo.jlgltech.com/signin"
    response = requests.post(url, data={"username": username, "password": password},
                             headers={'Content-Type': 'application/x-www-form-urlencoded'})
    cookie = response.history[0].headers.get('Set-Cookie').split(';')[0]
    return cookie


class ApolloClient:
    host = 'http://apollo.jlgltech.com'
    session = requests.session()
    sessionId = fetch_sessionId()

    @retry(tries=3, delay=1)
    @valid_login
    def get_apps(self):
        response = self.session.get(self.host + '/apps/search/by-appid-or-name', headers={"Cookie": self.sessionId},
                                    params={'query': '', 'page': 0, 'size': 200})
        response.raise_for_status()
        if len(response.history) > 0:
            raise ValueError('请求被重定向')
        data = response.json()
        return data

    @valid_login
    def get_app_items(self, app_id):
        """
        获取应用的配置
        :param app_name:
        :return:
        """
        response = self.session.get(self.host + f'/apps/{app_id}/envs/FAT/clusters/default/namespaces',
                                    headers={"Cookie": self.sessionId})
        response.raise_for_status()
        if len(response.history) > 0:
            raise ValueError('请求被重定向')
        data = response.json()
        return data

    @valid_login
    def get_associated_items(self, app_id, name_space):
        response = self.session.get(
            url=self.host + f"/envs/FAT/apps/{app_id}/clusters/default/namespaces/{name_space}/associated-public-namespace",
            headers={"Cookie": self.sessionId})
        response.raise_for_status()
        if len(response.history) > 0:
            raise ValueError('请求被重定向')
        data = response.json()
        return data

    @valid_login
    def edit_app_item(self, app_id, item, namespace):
        response = requests.put(url=self.host + f"/apps/{app_id}/envs/FAT/clusters/default/namespaces/{namespace}/item",
                                json=item, headers={"Cookie": self.sessionId})
        response.raise_for_status()
        if len(response.history) > 0:
            raise ValueError('请求被重定向')
        return

    @valid_login
    def release_app_configs(self, app_id, release_comment, release_title, namespace):
        """
        :param app_id:
        :param release_comment: 发布说明
        :param release_title: 发布标题
        :return:
        """
        body = {
            "isEmergencyPublish": False,
            "releaseComment": release_comment,
            "releaseTitle": release_title,
        }
        response = self.session.post(
            url=self.host + f"/apps/{app_id}/envs/FAT/clusters/default/namespaces/{namespace}/releases",
            json=body, headers={"Cookie": self.sessionId})
        response.raise_for_status()
        if len(response.history) > 0:
            raise ValueError('请求被重定向')
        data = response.json()
        return data


apollo = ApolloClient()
# apollo.get_apps()
# apollo.get_app_items('backend.phoenix.device-server')
# item = {"id":228,"namespaceId":56,"key":"service.wechat.ggshare.ticket.map",
#         "value":"{\"ggshare-ticket\":\"gQGo8TwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyWTlvSjk0S3lic2UxMDAwMDAwM2cAAgQlx5ZeAwQAAAAA\",\"ggshare-ticket2\":\"gQHB8DwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyQlhkeDlKS3lic2UxMDAwMHcwM2IAAgTwQLZeAwQAAAAA\",\"ggshare-ticket3\":\"gQHJ8TwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyZkI5TDl4S3lic2UxMDAwMDAwM04AAgTemd1eAwQAAAAA\",\"ggshare-ticket4\":\"gQGa8DwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAydGFMUzhjS3lic2UxMDAwMHcwM0EAAgTYWOheAwQAAAAA\",\"ggshare-ticket5\":\"gQFG8DwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyV1M3dzlaS3lic2UxMDAwME0wMzgAAgRaUxVfAwQAAAAA\",\"ggshare-ticket6\":\"gQHY8DwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyYzFFQThYS3lic2UxMDAwME0wM24AAgRSvSxfAwQAAAAA\",\"ggshare-ticket7\":\"gQF_8DwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyZnpEQTlvS3lic2UxMDAwMGcwM2YAAgTXHSxfAwQAAAAA\",\"ggshare-ticket8\":\"gQHf7zwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyVzlZdDh1S3lic2UxMDAwMHcwM1QAAgR7-E1fAwQAAAAA\",\"ggshare-ticket9\":\"gQGI8DwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyOXdDejgyS3lic2UxMDAwME0wM1YAAgQs-U1fAwQAAAAA\",\"ggshare-ticket10\":\"gQGi8DwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyY3JUcTlwS3lic2UxMDAwME0wM0wAAgSw-U1fAwQAAAAA\",\"ggshare-ticket12\":\"gQH08DwAAAAAAAAAAS5odHRwOi8vd2VpeGluLnFxLmNvbS9xLzAyU0NHMjhCS3lic2UxMDAwME0wMzgAAgQ271FfAwQAAAAA\"}","comment":"呱呱爱分享永久二维码Ticket（ticket11对应分支为随机二维码）",
#         "lineNum":1,
#         }
# apollo.edit_app_item('backend.phoenix.xshare-server', item)
