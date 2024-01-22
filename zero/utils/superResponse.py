# -*- coding: utf-8 -*-
# @Time    : 2020/11/30 11:35 上午
# @Author  : zoey
# @File    : superResonse.py
# @Software: PyCharm
from rest_framework.response import Response


def success(data=None, message='ok'):
    return Response(data={'msg': message, 'data': data}, status=200)


def bad_request(data=None, message='参数错误'):
    return Response(data={'msg': message, 'data': data}, status=400)


def server_error(data=None, message='服务器错误'):
    return Response(data={'msg': message, 'data': data}, status=500)
