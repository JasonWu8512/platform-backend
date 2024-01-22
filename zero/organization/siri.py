# -*- coding: utf-8 -*-
# @Time    : 2021/2/4 6:38 下午
# @Author  : zoey
# @File    : siri.py
# @Software: PyCharm
from zero.organization.models import *
from rest_framework import serializers
from zero.api.baseSiri import CustomSerializer, OffsetLimitSiri
from zero.jira.models import JiraIssue
from zero.utils.format import datestrToDate, second_2_days


class AccountSiri(serializers.ModelSerializer):
    class Meta:
        model = AceAccount
        fields = ('id', 'name', 'email', 'jira_user',)


class DepartmentSiri(serializers.ModelSerializer):
    class Meta:
        model = AceDepartment
        fields = ('open_department_id', 'name', 'parent_open_department_id',)


class DevDepartmentSiri(serializers.Serializer):
    open_department_id = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    parent_open_department_ids = serializers.CharField(required=False)
    leader_id = serializers.CharField(required=False)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        if obj.get('parent_open_department_ids') != '0':
            names = []
            ids = obj.get('parent_open_department_ids').split(',')
            for i in ids:
                if i != '0' and i != "od-6ac439ac289537cafd7d6e5cdff6a5e9":
                    name = AceDepartment.objects.filter(open_department_id=i).values_list("name", flat=False)[0][0]
                    names.append(name)
            names.reverse()
            names.append(obj.get('name'))
            return "/".join(names)
        return obj.get('name')


class AceChatSiri(serializers.ModelSerializer):
    class Meta:
        model = AceChat
        fields = ('id', 'chat_id', 'name')


class AceGitlabProjectSiri(serializers.ModelSerializer):
    class Meta:
        model = AceGitlabProject
        fields = ('project', 'path')


class AceGitlabProjectChatSiri(serializers.ModelSerializer):
    class Meta:
        model = AceGitlabProjectChat
        fields = ('id', 'project', 'source_branch', 'target_branch', 'chat_id')


class AceGitlabProjectPRSiri(serializers.ModelSerializer):
    class Meta:
        model = AceGitlabProjectChat
        fields = ('id', 'project', 'is_jira_active')


class AceGitlabProjectPRSchema(serializers.Serializer):
    project = serializers.CharField(required=False)
    is_jira_active = serializers.BooleanField(required=False)


class AceGitlabProjectChatSchema(serializers.Serializer):
    project = serializers.CharField(required=False)
    source_branch = serializers.CharField(required=False)
    target_branch = serializers.CharField(required=True)
    chat_id = serializers.CharField(required=True)


class UserTaskGanttSiri(serializers.ModelSerializer):
    duration = serializers.SerializerMethodField()
    estimate = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    story = serializers.SerializerMethodField()

    def get_duration(self, obj):
        return (obj.target_end - obj.target_start).days + 1

    def get_start_date(self, obj):
        return obj.target_start.strftime("%Y-%m-%d")

    def get_story(self, obj):
        if obj.parent_key:
            story = JiraIssue.objects.filter(key=obj.parent_key)
            if len(story):
                return story.first().summary

    def get_estimate(self, obj):
        return second_2_days(obj.original_time_estimate)

    class Meta:
        model = JiraIssue
        fields = ('id', 'summary', 'assignee', 'start_date', 'story', 'duration', 'estimate')


class getUserTaskSchema(serializers.Serializer):
    start_date = serializers.CharField(required=True)
    end_date = serializers.CharField(required=True)
    account_ids = serializers.ListField(required=True)
    # users = AccountSiri(many=True)


class getDepartmentSchema(serializers.Serializer):
    open_department_id = serializers.CharField(required=False, default='od-6ac439ac289537cafd7d6e5cdff6a5e9')


class getChatScheme(serializers.Serializer):
    name = serializers.CharField(required=False)


class getGitlabProjectScheme(serializers.Serializer):
    project = serializers.CharField(required=False)


class getGitlabProjectChatScheme(serializers.Serializer):
    project = serializers.CharField(required=False)


class AceApprovalConfigChatScheme(OffsetLimitSiri):
    project = serializers.CharField(required=False)
    chat_id = serializers.CharField(required=False)
