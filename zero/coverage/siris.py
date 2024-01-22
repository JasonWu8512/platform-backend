# -*- coding: utf-8 -*-
# @Time    : 2021/2/23 2:34 下午
# @Author  : zoey
# @File    : siris.py
# @Software: PyCharm
from rest_framework import serializers
from zero.coverage.models import *
from zero.api.baseSiri import OffsetLimitSiri, CustomSerializer
import json


class CreateJenkinsCommit(serializers.Serializer):
    git_url = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    short_commit = serializers.CharField(required=True, allow_null=False, allow_blank=False)


class CreateJenkinsTask(serializers.Serializer):
    project_git = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    compare_branch = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    pipeline_id = serializers.IntegerField(required=False)


class GetJenkinsTaskList(OffsetLimitSiri):
    pipeline_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class GetCoverageReport(OffsetLimitSiri):
    project_name = serializers.CharField(required=False)

class CreateCoveragePipline(serializers.Serializer):
    coverage_params = CreateJenkinsTask(required=True)
    name = serializers.CharField(required=True, max_length=64, allow_null=False, allow_blank=False)
    project_id = serializers.IntegerField(required=True, allow_null=False)
    owner = serializers.CharField(required=True, max_length=16)
    notify_chat_ids = serializers.ListField(required=False)
    step1 = serializers.CharField(required=True, allow_blank=True, allow_null=True)
    step2 = serializers.CharField(required=True, allow_blank=True, allow_null=True)

class GitWebHookSchema(serializers.Serializer):
    ssh_url = serializers.CharField(required=True, allow_null=False, allow_blank=False)
    commit_id = serializers.CharField(required=True, allow_blank=False, allow_null=False)



class FullCoverageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FullCoverage
        fields = '__all__'


class DiffCoverageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiffCoverage
        fields = '__all__'


class GitProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitProject
        fields = '__all__'


class JenkinsTaskSerializer(CustomSerializer):
    class Meta:
        model = JenkinsBuildTask
        fields = '__all__'
        extra_fields = ['status_chinese']


class JenkinsProjectCommitSerializer(serializers.ModelSerializer):
    class Meta:
        model = JenkinsProjectCommit
        fields = '__all__'


class CoveragePiplineSerializer(serializers.ModelSerializer):
    coverage_params = serializers.SerializerMethodField()
    notify_chat_ids = serializers.SerializerMethodField()
    reason = serializers.SerializerMethodField()

    def get_coverage_params(self, obj):
        return json.loads(obj.coverage_params)

    def get_notify_chat_ids(self, obj):
        return obj.notify_chat_ids.split(',') if obj.notify_chat_ids else []

    def get_reason(self, obj):
        return json.loads(obj.mark)

    class Meta:
        model = CoveragePipeline
        fields = ('id', 'name', 'step1', 'step2', 'project_name', 'project_id', 'deploy_status', 'coverage_status',
                  'end_commit', 'reason', 'coverage_params', 'notify_chat_ids', 'sonar_status', 'business', 'terminal')

class DeployServerHistorySerializer(CustomSerializer):
    class Meta:
        model = CoverageServerDeployHistory
        fields = '__all__'
        extra_fields = ['status_chinese']

