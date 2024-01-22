# -*- coding: utf-8 -*-
# @Time    : 2020/10/23 11:53 上午
# @Author  : zoey
# @File    : decorators.py
# @Software: PyCharm
import functools
from functools import wraps
from typing import Type

import jwt
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response

import zero.utils.superResponse as Response
from zero.organization.models import AceAccount

UserModel = get_user_model()


def login_or_permission_required(perm=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            # 格式化权限
            perms = (perm,) if isinstance(perm, str) else perm

            # if request.user.is_authenticated:
            #     # 正常登录用户判断是否有权限
            #     if not request.user.has_perms(perms):
            #         raise PermissionDenied
            # else:
            # try:
            auth = request.META.get("HTTP_AUTHORIZATION", "")
            if not auth:
                return Response(status=401, data={"msg": "No authenticate header"})
                # raise NotAuthenticated('No authenticate header')
                # return JsonResponse({"code": 401, "message": "No authenticate header"})

            try:
                valid_data = jwt.decode(auth, verify=False)
            except Exception:
                return Response(status=401, data={"msg": "失效或无效的token"})
                # raise AuthenticationFailed("失效或无效的token")

            # user = valid_data.get("user")

            # if not user.is_active:
            #     return Response(status=401, data={'msg': 'User inactive or deleted'})
            # raise NotAuthenticated("User inactive or deleted")
            try:
                user = UserModel.objects.get(id=valid_data["user_id"])
            except UserModel.DoesNotExist:
                return Response(status=401, data={"msg": "User Does not exist"})
                # raise NotAuthenticated("User Does not exist")

            # Token登录的用户判断是否有权限
            if perm:
                if not any(user.has_perm(perm) for perm in perms):
                    return Response(status=403, data={"msg": "PermissionDenied"})
                # raise PermissionDenied("PermissionDenied")
            try:
                self.open_id = AceAccount.objects.get(email=user.email).lark_open_id
            except AceAccount.DoesNotExist:
                self.open_id = ""
            self.username = user.username
            self.email = user.email
            return view_func(self, request, *args, **kwargs)

        return _wrapped_view

    return decorator


# 接口中使用，作为request参数的校验
def schema(siri: Type[serializers.Serializer] = None, partial=False):
    def decorator(func):
        siri_class = {"siri": siri}

        @wraps(func)
        def wrapper(self, request, **kwargs):
            if request.method in ("POST", "PUT", "PATCH"):
                data = request.data
            elif request.method in ("GET",):
                data = request.query_params
            elif request.method in ("DELETE",):
                data = request.data or request.query_params
            else:
                data = {}
            cur_siri = self.get_serializer if siri is None else siri
            siri_class.update(siri=cur_siri)
            validate_siri = cur_siri(data=data, partial=partial)
            validate_siri.is_valid(raise_exception=True)
            self.filtered = validate_siri.validated_data
            return func(self, request, **kwargs)

        wrapper.siri = siri_class["siri"]
        return wrapper

    return decorator


def raise_exception(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=str(e))

    return wrapper
