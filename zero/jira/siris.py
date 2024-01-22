# -*- coding: utf-8 -*-
# @Time    : 2020/10/23 4:27 下午
# @Author  : zoey
# @File    : siris.py
# @Software: PyCharm
from rest_framework import serializers
from zero.jira import models
from zero.organization.models import AceAccount, AceDepartmentAccount, AceDepartment
from zero.utils.format import get_data, second_2_days, get_point_by_buglevel, mode_number
from zero.api.baseSiri import CustomSerializer
from rest_framework_mongoengine.serializers import DocumentSerializer

'''------------------请求参数schema----------------------'''


class BaseParaSerializer(serializers.Serializer):
    proj_id = serializers.CharField(required=True, help_text='项目id')
    closed = serializers.IntegerField(required=False)


class GetVersionsSerializer(serializers.Serializer):
    sprint_id = serializers.CharField(required=True, help_text='sprint id')
    type = serializers.CharField(required=False, help_text='任务类型')


class GetBugStatus(serializers.Serializer):
    proj_id = serializers.CharField(required=False, help_text='项目id')
    start_date = serializers.CharField(required=True, help_text='选择开始时间')
    end_date = serializers.CharField(required=True, help_text='选择截止时间')


class GetMonthReport(serializers.Serializer):
    month = serializers.CharField(required=True, help_text='选择月份')


'''----------------response schema----------------------'''


class CwdUserSerializers(serializers.ModelSerializer):
    class Meta:
        model = models.CwdUser
        fields = '__all__'


class JiraProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JiraProject
        fields = ('id', 'key', 'name', 'sprints')


class JiraBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JiraBoards
        fields = '__all__'


class JiraSprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JiraSprint
        fields = '__all__'


class JiraEpicSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.JiraIssue
        fields = ('key', 'summary')


class JiraEpicSiri(serializers.ModelSerializer):
    class Meta:
        model = models.JiraIssue
        fields = '__all__'


class JiraBusinessCycleSiri(serializers.ModelSerializer):
    class Meta:
        model = models.JiraBusinessCycle
        fields = '__all__'


class JiraVersionTasksSerializer(serializers.ModelSerializer):
    # day = serializers.ReadOnlyField(source='day')
    # point = serializers.ReadOnlyField(source='point')

    class Meta:
        model = models.JiraIssue
        fields = (
        'id','bugOwner','assignee', 'creator', 'key', 'summary', 'description', 'type', 'status', 'parent_key', 'bug_level', 'sub_bug_level',
        'original_time_estimate', 'day', 'point', 'status_chinese')


class DepartmentEstimateSiri(DocumentSerializer):
    class Meta:
        model = models.DepartmentEstimate
        fields = '__all__'


class JiraProjectTaskEstimate(serializers.Serializer):
    proj_id = serializers.CharField(required=False, allow_blank=True)
    total_estimate = serializers.IntegerField(required=False)
    day = serializers.SerializerMethodField()
    proj_name = serializers.SerializerMethodField()

    def get_proj_name(self, obj):
        if obj.get('proj_id'):
            return models.JiraProject.objects.get(id=obj['proj_id']).name
        return

    def get_day(self, obj):
        return second_2_days(obj['total_estimate'])


class JiraDepartTaskEstimate(serializers.Serializer):
    bugOwner = serializers.CharField(required=False, allow_blank=True)
    total_estimate = serializers.IntegerField(required=False)
    day = serializers.SerializerMethodField()
    depart_name = serializers.SerializerMethodField()

    def get_depart_name(self, obj):
        if obj.get('bugOwner'):
            account_id = models.CwdUser.objects.get(user_name=obj['bugOwner']).ace_account_id
            if account_id:
                open_department_id = AceDepartmentAccount.objects.filter(account_id=account_id).order_by(
                    '-id').values_list('open_department_id', flat=True)
                depart = AceDepartment.objects.filter(open_department_id=
                                                      open_department_id[0]).values(
                    'name', 'parent_open_department_id', 'parent_open_department_ids')
                # 若父级部门是技术部，则直接返回部门名称
                if depart[0].get('parent_open_department_id') == 'od-6ac439ac289537cafd7d6e5cdff6a5e9':
                    return depart[0].get('name')
                else:
                    names = []
                    ids = depart[0].get('parent_open_department_ids').split(',')
                    for i in ids:
                        if i != '0' and i != "od-6ac439ac289537cafd7d6e5cdff6a5e9":
                            name = AceDepartment.objects.filter(open_department_id=i).values_list("name", flat=False)[0][0]
                            names.append(name)
                    names.reverse()
                    names.append(depart[0].get('name'))
                    return "/".join(names)
        return

    def get_day(self, obj):
        return second_2_days(obj['total_estimate'])


class JiraDelayTaskGroup(serializers.Serializer):
    assignee = serializers.CharField(required=False)
    key = serializers.CharField(required=False)
    summary = serializers.CharField(required=False)
    open_id = serializers.SerializerMethodField()

    def get_open_id(self, obj):
        open_id = models.CwdUser.objects.get(user_name=obj['assignee']).ace_open_id
        if open_id:
            return open_id
        return


class JiraBugCountGroup(serializers.Serializer):
    proj_id = serializers.CharField(required=False)
    bug_level = serializers.CharField(required=False)
    sub_bug_level = serializers.CharField(required=False)
    count = serializers.IntegerField(required=False)

    point = serializers.SerializerMethodField()
    proj_name = serializers.SerializerMethodField()

    def get_point(self, obj):
        return get_point_by_buglevel(obj['sub_bug_level']) * obj['count']

    def get_proj_name(self, obj):
        if obj.get('proj_id'):
            return models.JiraProject.objects.get(id=obj['proj_id']).name
        return


class SprintBugPoint(serializers.Serializer):
    platform = serializers.CharField(required=False)
    sub_bug_level = serializers.CharField(required=False)
    count = serializers.IntegerField(required=False)
    point = serializers.SerializerMethodField()

    def get_point(self, obj):
        return get_point_by_buglevel(obj['sub_bug_level']) * obj['count']


class SprintBugFixTime(serializers.Serializer):
    sub_bug_level = serializers.CharField(required=False)
    platform = serializers.CharField(required=False)
    count = serializers.IntegerField(required=False)
    duration = serializers.IntegerField(required=False)
    hours = serializers.SerializerMethodField()

    def get_hours(self, obj):
        return mode_number(mode_number(obj['duration'], obj['count']), 3600, 2)


class SprintBugCloseTime(serializers.Serializer):
    sub_bug_level = serializers.CharField(required=False)
    platform = serializers.CharField(required=False)
    count = serializers.IntegerField(required=False)
    fix_duration = serializers.IntegerField(required=False)
    close_duration = serializers.IntegerField(required=False)
    duration = serializers.SerializerMethodField()
    hours = serializers.SerializerMethodField()

    def get_duration(self, obj):
        if obj['fix_duration']:
            return obj['fix_duration'] + obj['close_duration']
        else:
            return obj['close_duration']

    def get_hours(self, obj):
        if obj['fix_duration']:
            return mode_number(mode_number((obj['fix_duration'] + obj['close_duration']), obj['count']), 3600, 2)
        else:
            return mode_number(mode_number(obj['close_duration'], obj['count']), 3600, 2)


class BugDetails(serializers.Serializer):
    bugOwner = serializers.CharField(required=False)
    sub_bug_level = serializers.CharField(required=False)
    key = serializers.CharField(required=False)
    platform = serializers.CharField(required=False)
    fix_time = serializers.IntegerField(required=False)
    close_time = serializers.IntegerField(required=False)
    summary = serializers.CharField(required=False)
    created = serializers.CharField(required=False)
    creator = serializers.CharField(required=False)
    env = serializers.CharField(required=False)
    fix_hour = serializers.SerializerMethodField()
    close_hour = serializers.SerializerMethodField()

    def get_fix_hour(self, obj):
        if obj['fix_time']:
            return mode_number(obj['fix_time'], 3600)
        else:
            return 0

    def get_close_hour(self, obj):
        if obj['close_time']:
            return mode_number(obj['close_time'], 3600)
        else:
            return 0


class JiraPeopleCountGroup(serializers.Serializer):
    proj_id = serializers.CharField(required=False)
    people_count = serializers.IntegerField(required=False)
    proj_name = serializers.SerializerMethodField()

    def get_proj_name(self, obj):
        if obj.get('proj_id'):
            return models.JiraProject.objects.get(id=obj['proj_id']).name
        return


class JiraBugCountDepart(serializers.Serializer):
    bugOwner = serializers.CharField(required=False)
    bug_level = serializers.CharField(required=False)
    sub_bug_level = serializers.CharField(required=False)
    count = serializers.IntegerField(required=False)

    point = serializers.SerializerMethodField()
    depart_name = serializers.SerializerMethodField()

    def get_point(self, obj):
        return get_point_by_buglevel(obj['sub_bug_level']) * obj['count']

    def get_depart_name(self, obj):
        if obj.get('bugOwner'):
            account_id = models.CwdUser.objects.get(user_name=obj['bugOwner']).ace_account_id
            if account_id:
                open_department_id = AceDepartmentAccount.objects.filter(account_id=account_id).order_by(
                    '-id').values_list('open_department_id', flat=True)
                depart = AceDepartment.objects.filter(open_department_id=
                                                      open_department_id[0]).values(
                    'name', 'parent_open_department_id', 'parent_open_department_ids')
                # 若父级部门是技术部，则直接返回部门名称
                if depart[0].get('parent_open_department_id') == 'od-6ac439ac289537cafd7d6e5cdff6a5e9':
                    return depart[0].get('name')
                else:
                    names = []
                    ids = depart[0].get('parent_open_department_ids').split(',')
                    for i in ids:
                        if i != '0' and i != "od-6ac439ac289537cafd7d6e5cdff6a5e9":
                            name = AceDepartment.objects.filter(open_department_id=i).values_list("name", flat=False)[0][0]
                            names.append(name)
                    names.reverse()
                    names.append(depart[0].get('name'))
                    return "/".join(names)
        return


class SprintEstimateSiri(DocumentSerializer):
    business_story_days = serializers.SerializerMethodField()
    tech_story_days = serializers.SerializerMethodField()
    resource_depletion_days= serializers.SerializerMethodField()
    change_story_days = serializers.SerializerMethodField()
    regression_story_days = serializers.SerializerMethodField()

    def get_business_story_days(self, obj):
        return second_2_days(obj.business_story_estimate)

    def get_tech_story_days(self, obj):
        return second_2_days((obj.tech_story_estimate))

    def get_resource_depletion_days(self, obj):
        return second_2_days((obj.resource_depletion_estimate))

    def get_change_story_days(self, obj):
        return second_2_days((obj.change_story_estimate))

    def get_regression_story_days(self, obj):
        return second_2_days((obj.regression_estimate))

    class Meta:
        model = models.SprintEstimate
        exclude = ('created_at', 'updated_at')


class DepartmentEsSiri(DocumentSerializer):
    class Meta:
        model = models.DepartmentEstimate
        exclude = ('created_at', 'updated_at')


class PlatformBug(serializers.Serializer):
    """平台对应bugs"""
    platform = serializers.CharField(required=False)
    count = serializers.IntegerField(required=False)
