# -*- coding: utf-8 -*-
# @Time    : 2020/10/21 1:58 下午
# @Author  : zoey
# @File    : baseSiri.py
# @Software: PyCharm
from rest_framework import serializers
from rest_framework_mongoengine.serializers import DocumentSerializer


class OffsetLimitSiri(serializers.Serializer):
    offset = serializers.IntegerField(default=0, required=False, help_text='偏移量')
    limit = serializers.IntegerField(default=20, required=False, help_text='每页数目')


class ChangePasswordSiri(serializers.Serializer):
    oldpassword = serializers.CharField(required=True, allow_null=False, help_text='旧密码')
    newpassword = serializers.CharField(required=True, allow_null=False, help_text='新密码')


class CustomSerializer(serializers.ModelSerializer):

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(CustomSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields


class DocumentCustomSerializer(DocumentSerializer):
    def get_field_names(self, declared_fields, info):
        expanded_fields = super(DocumentCustomSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields
