# -*- coding: utf-8 -*-
# @Time    : 2021/7/28 11:35 上午
# @Author  : zoey
# @File    : apiRequest.py
# @Software: PyCharm
from random import randint

import funcy as fc
from retry import retry

import zero.utils.super_requests as requests
from zero.libs.mongo import mongoClient
from zero.libs.mysql import MySQL

jlgl_url = "https://fat.jiliguala.com"


@retry(tries=3, delay=1)
def register_user(mobile=None):
    """注册新用户"""
    if not mobile:
        for i in fc.count():
            mobile = "16" + str(randint(400000000, 499999999))
            user = mongoClient.get_client().get_collection("users").find_one({"mobile": mobile})
            if not user:
                break
            elif i >= 20:
                raise ValueError("请求超时，请重试")
    body = {"mobile": mobile, "source": "NA", "crm_source": "NA"}
    response = requests.post(url=f"{jlgl_url}/api/web/sms", json=body, verify=False)
    response.raise_for_status()
    return mobile


def logout_user(mobile, basic_auth):
    headers = {"Authorization": basic_auth}
    body = {"type": "text HTTP/1.1"}
    sms = requests.get(url=f"{jlgl_url}/api/user/sms_logout", params=body, headers=headers, verify=False)
    sms.raise_for_status()
    code = mongoClient.get_client().get_collection("users").find_one({"mobile": mobile})["sms"]["code"]
    body = {"mobile": mobile, "smsCode": code}
    resp = requests.delete(url=f"{jlgl_url}/api/users/security/info", json=body, headers=headers, verify=False)
    resp.raise_for_status()


def register_guest():
    """创建游客"""
    response = requests.put(url=f"{jlgl_url}/api/users/guest/v2", verify=False)
    response.raise_for_status()
    return response.json().get("data")


def onboarding_create_baby(bd, auth):
    """
    创建指定年龄baby
    :param bd: baby 生日时间戳
    :param auth: 加密base64 token
    :return:
    """
    body = {"bd": bd, "auth": auth, "nick": "宝宝"}
    response = requests.post(url=f"{jlgl_url}/api/user/onboarding", json=body, verify=False)
    response.raise_for_status()
    return response.json().get("data")


def create_promoter(mobile, guaid):
    """一键生成推广人"""
    body = {"promoterInfos": [{"guaid": guaid, "mobile": mobile, "identity": "normal"}]}
    res = requests.request(method="POST", url=f"{jlgl_url}/api/promoter/batchImport", json=body, verify=False)
    res.raise_for_status()


def purchase_item(bid, item_id, basic_auth, channel="alipay"):
    """
    站内购买课程
    :param bid:
    :param channel:
    :param item_id:
    :param physical:
    :return:
    """
    eshop_db = MySQL("eshop")
    commodity = eshop_db.query(sql=f"select id from commodity where commodity_no='S1GE'")
    skus = eshop_db.query_raw(sql=f"select sku_id from commodity_sgu_map where sgu_id={commodity[0]['id']}")
    ids = [item[0] for item in skus]
    categories = eshop_db.query(
        sql=f"select category_code from commodity where id in {tuple(ids)}"
        if len(ids) > 1
        else f"select category_code from commodity where id={ids[0]}"
    )
    physical = any([item["category_code"].startswith("physical/") for item in categories])
    headers = {"Authorization": basic_auth}
    body = {"bid": bid, "channel": channel, "itemid": item_id, "physical": physical}
    res = requests.post(url=f"{jlgl_url}/api/pingpp/purchase", json=body, headers=headers, verify=False)
    res.raise_for_status()
