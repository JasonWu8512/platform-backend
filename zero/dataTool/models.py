# -*- coding: utf-8 -*-
# @Time    : 2021/7/19 11:19 上午
# @Author  : zoey
# @File    : models.py
# @Software: PyCharm

from zero.libs.baseModel import BaseModel
from django.db import models


class ApolloAppItems(BaseModel):
    appId = models.CharField(max_length=64, blank=False, null=False)
    key = models.CharField(max_length=64, null=False, blank=False)
    dataChangeLastModifiedBy = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = 'apollo_app_items'
        unique_together = (('appId', 'key'),)


class ApolloOperateLog(BaseModel):
    appId = models.CharField(max_length=64)
    operation = models.CharField(max_length=32)
    key = models.CharField(max_length=64, null=True)
    value = models.TextField(null=True)
    comment = models.CharField(max_length=255, null=True)
    operator = models.CharField(max_length=32)

    class Meta:
        db_table = 'apollo_operate_log'


class ApolloAppChat(BaseModel):
    app_id = models.CharField(max_length=64, null=False, blank=False)
    chat_id = models.CharField(max_length=128, null=False, blank=False)

    class Meta:
        db_table = 'apollo_app_chat'
        unique_together = (('app_id', 'chat_id'),)


# class ApolloIntlAppItems(BaseModel):
#     appId = models.CharField(max_length=64, blank=False, null=False)
#     key = models.CharField(max_length=64, null=False, blank=False)
#     dataChangeLastModifiedBy = models.CharField(max_length=64, null=True, blank=True)
#
#     class Meta:
#         db_table = 'apollo_intl_app_items'
#         unique_together = (('appId', 'key'),)
#
#
# class ApolloIntlOperateLog(BaseModel):
#     appId = models.CharField(max_length=64)
#     operation = models.CharField(max_length=32)
#     key = models.CharField(max_length=64, null=True)
#     value = models.TextField(null=True)
#     comment = models.CharField(max_length=255, null=True)
#     operator = models.CharField(max_length=32)
#
#     class Meta:
#         db_table = 'apollo_intl_operate_log'
#
#
# class ApolloIntlAppChat(BaseModel):
#     app_id = models.CharField(max_length=64, null=False, blank=False)
#     chat_id = models.CharField(max_length=128, null=False, blank=False)
#
#     class Meta:
#         db_table = 'apollo_intl_app_chat'
#         unique_together = (('app_id', 'chat_id'),)
