# -*- coding: utf-8 -*-
# @Time    : 2020/10/23 5:33 下午
# @Author  : zoey
# @File    : middleware.py
# @Software: PyCharm
from __future__ import unicode_literals

import logging
import json
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework_jwt.serializers import VerifyJSONWebTokenSerializer
from rest_framework.response import Response

"""
自定义jwt认证成功返回数据
:token  返回的jwt
:user   当前登录的用户信息[对象]
:request 当前本次客户端提交过来的数据
:role 角色
"""


def jwt_response_payload_handler(token, user=None, request=None, role=None):
    if user.first_name:
        name = user.first_name
    else:
        name = user.username
    return {
        "authenticated": 'true',
        'id': user.id,
        "role": role,
        'name': name,
        'username': user.username,
        'email': user.email,
        'permissions': list(user.get_all_permissions()),
        'token': token,
    }


class ApiLoggingMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        self.apiLogger = logging.getLogger('api')

    def __call__(self, request):
        try:
            body = json.loads(request.body)
        except Exception:
            body = dict()
        body.update(dict(request.POST))
        response = self.get_response(request)
        response['Accept'] = "*/*"
        response["Access-Control-Allow-Headers"] = "*"
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS, DELETE, PATCH, PUT'
        response['Access-Control-Allow-Credentials'] = 'true'
        if hasattr(response, 'data'):
            self.apiLogger.info("请求ip:{} {} {}  请求body:{} 返回体:{} {}".format(
                request.META.get("REMOTE_ADDR"), request.method, request.path, body,
                response.status_code, response.data))
        else:
            self.apiLogger.info("请求ip:{} {} {} {} {}".format(
                request.META.get("REMOTE_ADDR"), request.method, request.path, body,
                response.status_code))
        return response


class JwtAuthorizationAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # 获取头信息token
        authorization = request.META.get('HTTP_AUTHORIZATION', '')
        if not authorization:
            raise NotAuthenticated('No authenticate header')
        # 校验
        try:
            valid_data = VerifyJSONWebTokenSerializer().validate({"token": authorization})
        except Exception:
            raise AuthenticationFailed("token 失效了")

        """
        验证valid_data中的用户信息
        """
        user = valid_data.get("user")
        if user:
            return
        else:
            raise AuthenticationFailed("认证失败了。。。")


class Md1:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("Md1处理请求")

        response = self.get_response(request)

        print("Md1返回响应")

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        print("Md1在执行%s视图前" % view_func.__name__)

    def process_exception(self, request, exception):
        print("Md1处理视图异常...")
        if exception:
            return Response({'msg': exception}, status=500)
