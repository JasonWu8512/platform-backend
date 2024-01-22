# -*- coding: utf-8 -*-
# @Time    : 2021/3/8 4:04 下午
# @Author  : zoey
# @File    : siris.py
# @Software: PyCharm
from rest_framework import serializers
from zero.auto.models import AutoCaseTags, AutoCaseTree, AutoCaseConfig, AutoCaseAllureDetail, AutoCaseAllureReport, AutoCaseRunHistory
from zero.api.baseSiri import OffsetLimitSiri, CustomSerializer, DocumentCustomSerializer, DocumentSerializer


class CaseTagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoCaseTags
        fields = ('id', 'name',)


class CaseTreeSerializer(DocumentSerializer):
    class Meta:
        model = AutoCaseTree
        fields = '__all__'


class CaseConfigSerializer(DocumentSerializer):
    class Meta:
        model = AutoCaseConfig
        fields = '__all__'


class AllureReportSerializer(DocumentSerializer):
    class Meta:
        model = AutoCaseAllureReport
        fields = '__all__'


class AllureCaseDetailSerializer(DocumentSerializer):
    class Meta:
        model = AutoCaseAllureDetail
        fields = '__all__'


class AutoRunHistorySerializer(CustomSerializer):
    class Meta:
        model = AutoCaseRunHistory
        fields = '__all__'
        extra_fields = ['status_chinese']


class CaseConfigListSchema(OffsetLimitSiri):
    name = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class CreateCaseConfigSchema(DocumentSerializer):
    class Meta:
        model = AutoCaseConfig
        exclude = ('created_at', 'updated_at')


class GetBuildHistorySchema(OffsetLimitSiri):
    config_name = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    config_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)


