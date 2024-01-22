# -*- coding: utf-8 -*-
# @Time    : 2020/10/29 5:21 下午
# @Author  : zoey
# @File    : user.py
# @Software: PyCharm
import time

from django.contrib.auth.models import User
from zero.api import BaseViewSet
from zero.api.baseSiri import OffsetLimitSiri, ChangePasswordSiri
from zero.utils import get_object_or_not_found
from zero.api.decorators import schema
from rest_framework.decorators import list_route, detail_route
from rest_framework.response import Response
from zero.api.decorators import login_or_permission_required
from zero.utils.nacos_demo import sso_auth_token, sso_account, sso_logout
from zero.user.models import UserSsoAccessToken
from zero.testTrack.siris import UserSiri
import logging
from zero.utils import superResponse
import jwt
from zero import settings
# from rest_framework_jwt.settings import api_settings

logger = logging.getLogger('api')


class UserViewSet(BaseViewSet):
    queryset = User.objects.all()
    serializer_class = OffsetLimitSiri

    # @login_or_permission_required('normal.all')
    @schema(siri=ChangePasswordSiri)
    @detail_route(methods=['post'], url_path='change-password')
    def edit_user(self, request, pk=None):
        user = get_object_or_not_found(User, id=pk)
        if user.check_password(self.filtered['oldpassword']):
            user.set_password(self.filtered['newpassword'])
            user.save()
            return Response(data={'msg': 'OK'})
        else:
            return Response(data={'msg': '密码错误'}, status=400)

    def list(self, request, *args, **kwargs):
        search = request.query_params.get('search', '')
        query_set = User.objects.filter(is_active=True, username__contains=search)
        data = UserSiri(query_set, many=True).data
        return Response(data={'data': data})

    @list_route(methods=['get'], url_path='permissions')
    def get_user_permissions(self, request):
        user_id = request.query_params.get('user_id')
        user = get_object_or_not_found(User, id=user_id)
        return Response(data={'permissions': list(user.get_all_permissions())})

    @list_route(methods=['post'], url_path='auth_token')
    def auth_token(self, request):
        # instance = get_instance()
        if settings.IS_PROD:
            res = sso_auth_token(request.data.get("sso_auth_code"))
            if res.get("code") == 0:
                user_info = jwt.decode(res['data']['id_token'], verify=False)
                try:
                    user = User.objects.get(email=user_info['email'], is_active=True)
                except User.DoesNotExist:
                    return superResponse.bad_request(message='用户在jira系统不存在')
                except Exception as e:
                    return superResponse.server_error(message=str(e))
                user_info['username'] = user.username
                user_info['user_id'] = user.id
                user_info['exp'] = 12 * 3600 * 1000
                token = jwt.encode(payload=user_info, key='slg')
                UserSsoAccessToken.objects.update_or_create(uid=user_info['uid'],
                                                            defaults={'access_token': res['data']['access_token'],
                                                                      'expire_time': user_info['exp']})
                return Response(data={'token': token, 'permissions': user.get_all_permissions()}, status=200)
            else:
                return Response(data=res, status=400)
        else:
            user_info = {'email': 'devops@jiliguala.com'}
            user = User.objects.get(email=user_info['email'], is_active=True)
            user_info['username'] = user.username
            user_info['user_id'] = user.id
            user_info['exp'] = 12 * 3600 * 1000
            token = jwt.encode(payload=user_info, key='slg')
            return Response(data={'token': token, 'permissions': user.get_all_permissions()}, status=200)

    @list_route(methods=['post'], url_path='logout')
    def sso_logout(self, request):
        uid = request.data.get('uid')
        if not uid:
            return Response(data={"code": 0})
        access_token = UserSsoAccessToken.objects.get(uid=uid).access_token
        res = sso_logout(access_token=access_token)
        if res.get("code") == 0:
            return Response(data=res, status=200)
        elif str(res.status_code).startswith('4') :
            return Response(data={'message': res.get('msg')}, status=200)
        else:
            return Response(data={'message': res.get('msg')}, status=500)

