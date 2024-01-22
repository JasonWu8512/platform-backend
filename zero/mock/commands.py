# -*- coding: utf-8 -*-
# @Time    : 2020/11/26 1:18 下午
# @Author  : zoey
# @File    : commands.py
# @Software: PyCharm
from zero.utils.enums.jlgl_enum import ChineseEnum, ChineseTuple
import requests


class MockDomains(ChineseEnum):
    PINGXX = ChineseTuple(('api.pingxx.com', '支付'))


class PxxEvent(ChineseEnum):
    CHARGE_SUCCESS = ChineseTuple(('charge.succeeded', '支付成功'))
    REFUND_SUCCESS = ChineseTuple(('refund.succeeded', '退款成功'))

class PxxClient():

    BaseUrl = 'https://api.pingxx.com'

    @classmethod
    def refund(self, cid, body, headers):
        res = requests.post(f'{self.BaseUrl}/v1/charges/{cid}/refunds', json=body, headers=headers, verify=False)
        return res

    @classmethod
    def query_refund(self, cid, refund_id, headers):
        res = requests.get(f'{self.BaseUrl}/v1/charges/{cid}/refunds/{refund_id}', headers=headers, verify=False)
