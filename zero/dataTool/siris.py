# -*- coding: utf-8 -*-
# @Time    : 2021/7/26 11:19 上午
# @Author  : zoey
# @File    : siris.py
# @Software: PyCharm

from rest_framework import serializers
#  from zero.dataTool.models import ApolloAppChat, ApolloIntlAppChat
from zero.dataTool.models import ApolloAppChat
from zero.organization.models import AceChat
from zero.api.baseSiri import OffsetLimitSiri, CustomSerializer
import json


class ApolloAppChatSiri(CustomSerializer):
    chat_name = serializers.SerializerMethodField()

    def get_chat_name(self, obj):
        try:
            chat = AceChat.objects.get(chat_id=obj.chat_id)
        except AceChat.DoesNotExist:
            return ''
        return chat.name

    class Meta:
        model = ApolloAppChat
        fields = '__all__'


# class ApolloIntlAppChatSiri(CustomSerializer):
#     chat_name = serializers.SerializerMethodField()
#
#     def get_chat_name(self, obj):
#         try:
#             chat = AceChat.objects.get(chat_id=obj.chat_id)
#         except AceChat.DoesNotExist:
#             return ''
#         return chat.name
#
#     class Meta:
#         model = ApolloIntlAppChat
#         fields = '__all__'


class GetAppChatSchema(OffsetLimitSiri):
    search = serializers.CharField(required=False, default='', allow_null=False)
