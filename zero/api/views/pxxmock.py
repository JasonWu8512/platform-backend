# -*- coding: utf-8 -*-
# @Time    : 2020/11/25 3:17 下午
# @Author  : zoey
# @File    : pxxmock.py
# @Software: PyCharm

from django.contrib.auth.models import Group
from zero.api import BaseViewSet
from zero.api.baseSiri import OffsetLimitSiri
from rest_framework.decorators import list_route, detail_route
from rest_framework.response import Response
from zero.utils import superResponse
from zero.mock.tasks import pxx_webhooks, ace_larkhooks
from zero.mock.commands import PxxEvent, MockDomains, PxxClient
from zero.mock.fabfile_mock import *
from zero.organization.models import AceAccount
from zero.libs.redis import RedisClient
import json
import time
import logging
import shortuuid
from celery.result import AsyncResult

logger = logging.getLogger('api')


class MockSwitchViewSet(BaseViewSet):
    """开关mock,只能发版后执行本地无法执行"""
    queryset = Group.objects.filter(name__isnull=False)
    serializer_class = OffsetLimitSiri

    @list_route(methods=['get'], url_path='status')
    def get_mock_status(self, request):
        data = request.data or request.query_params
        host_lines_list = get_mock_status(data.get('env'))
        domain_status = []
        for domain in MockDomains:
            status_list = []
            sub_domain_status = []
            for host_lines in host_lines_list:
                for key, value in host_lines.items():
                    if domain.value in value:
                        status_list.append(True)
                        sub_domain_status.append({'server': f'{key}', 'status': True})
                    else:
                        status_list.append(False)
                        sub_domain_status.append({'server': f'{key}', 'status': False})
            domain_status.append({'domain': domain.value, 'status': all(status_list), 'details': sub_domain_status})
        return superResponse.success(data=domain_status)

    @list_route(methods=['post'], url_path='status/update')
    def update_mock_status(self, request):
        """更新mock状态"""
        data = request.data or request.json
        domains = data.get('domains')
        env = data.get('env')
        server = data.get('server_list')
        user_email = data.get('user_email')
        open_id = AceAccount.objects.get(email=user_email).lark_open_id
        for domain, status in domains.items():
            if not server:
                return superResponse.bad_request(message='请至少选择一个服务')
            # 先删除域名在hosts中的行，如果是
            try:
                switch_mock_host(env=env, status=status, server=server)
            except Exception as e:
                superResponse.server_error(message=e.args[0])
        ace_larkhooks.apply_async(kwargs={'env': env, 'open_id': open_id}, countdown=1)
        return superResponse.success()


class MockViewSet(BaseViewSet):
    authentication_classes = ()
    queryset = Group.objects.filter(name__isnull=False)
    serializer_class = OffsetLimitSiri

    @list_route(methods=['post'], url_path='charges')
    def createCharge(self, request):
        """创建支付"""
        data = request.data
        charge_id = "mockch_" + shortuuid.uuid()
        created = int(time.time())
        tn = int(time.time() * 1000000)
        resData = {
            "id": charge_id,
            "object": "charge",
            "created": created,
            "livemode": True,
            "paid": not bool(data.get('amount')),
            "refunded": False,
            "reversed": False,
            "app": "app_1Gqj58ynP0mHeX1q",
            "channel": data.get('channel'),
            "order_no": data.get('order_no'),
            "client_ip": data.get('client_id'),
            "amount": data.get('amount'),
            "amount_settle": data.get('amount'),
            "currency": data.get('currency'),
            "subject": data.get('subject'),
            "body": data.get('body'),
            "extra": data.get('extra', {}),
            "time_paid": created + 1,
            "time_expire": data.get('time_expire', created + 3600),
            "time_settle": None,
            "transaction_no": None,
            "refunds": {
                "object": "list",
                "url": f"/v1/charges/{charge_id}/refunds",
                "has_more": False,
                "data": []
            },
            "amount_refunded": 0,
            "failure_code": None,
            "failure_msg": None,
            "metadata": {},
            "credential": {
                "object": "credential",
                data.get('channel'): {
                    "tn": tn,
                    "mode": "01"
                } if 'qr' not in data.get('channel') else "https://cli.im/url"
            },
            "description": None,
            "res": "success",
        }
        pxx_webhooks.apply_async(kwargs={'chargeobject': resData, 'event': PxxEvent.CHARGE_SUCCESS.value}, countdown=1,
                                 priority=10, routing_key='high_celery')
        return Response(resData)

    @list_route(methods=['get'], url_path='charges/(?P<cid>[^/]+)')
    def query_charge(self, request, cid=None):
        chargeObject = json.loads(RedisClient.get_client('cache').get(cid) or '{}')
        return Response(chargeObject)

    @list_route(methods=['get'], url_path='charges/(?P<cid>[^/]+)/refunds/(?P<rid>[^/]+)')
    def query_refund(self, request, cid=None, rid=None):
        refundObject = json.loads(RedisClient.get_client('cache').get(rid) or '{}')
        return Response(refundObject)

    @list_route(methods=['post'], url_path='charges/(?P<cid>[^/]+)/refunds')
    def create_refund(self, request, cid=None):
        """创建退款"""
        if not cid.startswith('mock'):
            res = PxxClient.refund(cid, request.data, dict(request.headers))
            return Response(status=res.status_code, data=res.json())
        chargeObject = json.loads(RedisClient.get_client('cache').get(cid) or '{}')
        chargeObject.update({'refunded': True, 'amount_refunded': chargeObject['amount']})
        RedisClient.get_client('cache').set(cid, json.dumps(chargeObject))
        order_no = shortuuid.uuid()
        refundId = 'mockre_' + order_no
        created = int(time.time())
        resData = {
            "id": refundId,
            "object": "refund",
            "order_no": order_no,
            "amount": request.data.get('amount') or chargeObject.get('amount'),
            "created": created,
            "succeed": True,
            "status": "succeeded",
            "time_succeed": created,
            "description": "Refund Description",
            "failure_code": None,
            "failure_msg": None,
            "metadata": request.data.get('metadata', {}),
            "charge": cid,
            "charge_order_no": chargeObject.get('order_no'),
            "transaction_no": int(time.time() * 1000000),
            "funding_source": None,
            "extra": {}
        }
        pxx_webhooks.apply_async(
            kwargs={'chargeobject': resData, 'event': PxxEvent.REFUND_SUCCESS.value}, countdown=1, priority=10, routing_key='high_celery')
        return Response(resData)
        # result = AsyncResult(task.id).state
        # retry = 1
        # while result not in ['SUCCESS', 'FAILURE', 'REVOKED'] and retry < 10:
        #     time.sleep(1)
        #     result = AsyncResult(task.id).state
        #     retry += 1
        # else:
        #     if result == 'SUCCESS':
        #         return Response(resData)
        #     else:
        #         return superResponse.bad_request(message='回调pay服务/api/mock/pingpp/refund/callback接口错误')
