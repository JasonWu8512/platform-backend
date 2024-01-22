# -*- coding: utf-8 -*-
# @Time    : 2020/11/25 3:21 下午
# @Author  : zoey
# @File    : tasks.py
# @Software: PyCharm
from zero.celery import app
import requests
import logging
import time
import shortuuid
import json
import re
from zero.libs.redis import RedisClient
from zero.mock.commands import PxxEvent
from requests.exceptions import HTTPError


@app.task(bind=True, max_retries=10, default_retry_delay=2)
def ace_larkhooks(self, env, open_id):
    body = {
        "event": {
            "type": "message", "text": f"/mock -e {env}", "open_chat_id": "oc_85edcdfd0a6ac9381d8824eacc9fbcda",
            "open_id": open_id
        },
        "uuid": shortuuid.uuid(),
        "token": "zero_jiliguala"
    }
    try:
        requests.post('https://ace.jiliguala.com/endpoints/lark/', json=body, headers={'Content-Type': 'application/json'}, verify=False)
    except Exception as e:
        logging.error(e.args[0])
        self.retry(exc=e)


@app.task(bind=True, max_retries=10, default_retry_delay=2)
def pxx_webhooks(self, chargeobject, event):
    domains = ['https://dev.jiliguala.com', 'https://fat.jiliguala.com']
    RedisClient.get_client('cache').set(chargeobject['id'], json.dumps(chargeobject), ex=3600 * 24 * 30)
    if event == PxxEvent.CHARGE_SUCCESS.value:
        api = '/api/trade-order/pingxx/mock/chargeCallBack'
    else:
        api = '/api/trade-order/pingxx/mock/refundCallBack'
    event_id = "mockevt_" + shortuuid.uuid()
    notify_body = {
        "id": event_id,
        "created": int(time.time()),
        "livemode": True,
        "type": event,
        "data": {
            "ipAddress": 'http://172.31.112.10:8000',
            "object": chargeobject
        },
        "object": event_id,
        "pending_webhooks": 0,
        "request": "iar_qH4y1KbTy5eLGm1uHSTS00s"
    }
    try:
        status_list = ''
        res_list = []
        for domain in domains:
            res = requests.request(method='POST', url=f'{domain}{api}', json=notify_body,
                                   headers={'Content-Type': 'application/json', 'x-pingplusplus-signature': 'mock'}, verify=False)
            status_list += f'{res.status_code},'
            res_list.append(res)
        logging.info(
            f'{res_list[0].status_code}: {res_list[0].text}，{res_list[1].status_code}: {res_list[1].text} 请求body:{notify_body};')
        if not re.search(r'2[\d]{2}', status_list):
            raise Exception(f'回调失败: {status_list}')
    except Exception as e:
        logging.error(e)
        raise self.retry(exc=e)
