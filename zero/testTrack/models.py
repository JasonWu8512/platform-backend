# -*- coding: utf-8 -*-
# @Time    : 2020/10/29 4:29 下午
# @Author  : zoey
# @File    : models.py
# @Software: PyCharm
from django.db import models
from uuid import uuid4
from zero.jira.models import JiraProject, JiraIssue, JiraFixVersions
import mongoengine as mongo
import shortuuid
from zero.libs.baseModel import BaseDocument, BaseModel
from zero.testTrack.commands import PlanStatus, ReviewStatus, ProgressStatus, PlanStage
from zero.jira.siris import JiraVersionTasksSerializer


class BaseCase(BaseDocument):
    tree_id = mongo.StringField(required=True)
    importance = mongo.IntField()
    status = mongo.StringField(default='init')
    proj_id = mongo.StringField()
    description = mongo.StringField(required=False, default='')

    meta = {'abstract': True}


class ManualCase(BaseCase):
    """
    xmind 转case包含以下字段
    TestCase
    :param name: test case name
    :param version: test case version infomation
    :param summary: test case summary infomation
    :param preconditions: test case pre condition
    :param execution_type: manual:1 or automate:2
    :param importance: high:1, middle:2, low:3
    :param estimated_exec_duration: estimated execution duration
    :param status: draft:1, ready ro review:2, review in progress:3, rework:4, obsolete:5, future:6, final:7
    :param steps: test case step list
    """
    id = mongo.StringField(primary_key=True, default=shortuuid.uuid)
    name = mongo.StringField(required=True)
    version = mongo.IntField(required=False, default=1)
    summary = mongo.StringField(required=False)
    preconditions = mongo.StringField(default="无")
    execution_type = mongo.IntField(default=1)
    steps = mongo.ListField(mongo.DictField(), default=[])
    product = mongo.StringField(required=False)
    suite = mongo.StringField(required=False)
    estimated_exec_duration = mongo.IntField(required=False, default=3)
    # 拓展自定义字段
    creator = mongo.StringField(required=False)  # 文件上传者
    qa = mongo.StringField(required=False)  # qa执行者
    reviewer = mongo.StringField(required=False, default='')  # 用例评审人
    case_type = mongo.StringField(default='functional')

    meta = {'collection': 'manual_case',
            "indexes": ["tree_id", "name", "status", "reviewer", "creator", "importance", "proj_id", "case_type"]}

    @property
    def status_chinese(self):
        return ReviewStatus.get_chinese(self.status)


class TestPlanCase(BaseCase):
    id = mongo.StringField(primary_key=True, default=shortuuid.uuid)
    name = mongo.StringField()
    plan_id = mongo.StringField()
    case_id = mongo.StringField()
    executor = mongo.StringField(required=False, default='')
    step_actual_results = mongo.ListField(mongo.StringField(), default=[])
    step_actual_status = mongo.ListField(mongo.StringField(), default=[])
    issue_ids = mongo.ListField(mongo.StringField(), default=[])
    smoke_check = mongo.StringField(default='init')

    meta = {'collection': 'test_plan_case',
            'indexes': ['plan_id', 'tree_id', 'executor', 'status', 'importance', 'proj_id', 'case_id', 'smoke_check']}

    @property
    def status_chinese(self):
        return PlanStatus.get_chinese(self.status)

    @property
    def issues(self):
        return JiraVersionTasksSerializer(JiraIssue.objects.filter(key__in=self.issue_ids,
                                                                   resolution__in=['完成', 'Unresolved']), many=True).data


class TestPlanTree(BaseDocument):
    id = mongo.IntField(primary_key=True, required=True)
    tree = mongo.ListField(mongo.DictField(), default=[])

    meta = {"collection": 'test_plan_tree',}


class ModuleTree(BaseModel):
    id = models.AutoField(primary_key=True, auto_created=True, serialize=False)
    name = models.CharField(max_length=255, blank=False, null=False)
    parent = models.CharField(max_length=15, blank=True, null=True)
    proj_id = models.CharField(max_length=15, blank=False, null=False)
    deleted = models.BooleanField(default=False, serialize=False)

    class Meta:
        db_table = 'module_tree'

    @property
    def review_id(self):
        query = TestReviewModel.objects.filter(tree_id=self.id)
        if len(query) > 0:
            return query.first().id

    @property
    def proj_name(self):
        return JiraProject.objects.get(id=self.proj_id).name


class TestPlanModel(BaseModel):
    id = models.AutoField(primary_key=True, auto_created=True)
    name = models.CharField(max_length=255, blank=True, null=False)
    epic_ids = models.CharField(max_length=255, blank=True, null=False, serialize=False)
    stories = models.CharField(max_length=255, blank=True, null=True, serialize=False)
    sprint_id = models.CharField(max_length=32, blank=False, null=False)
    proj_id_list = models.CharField(max_length=255, blank=False, null=False, default="[]", serialize=False)
    proj_name_list = models.TextField(max_length=65535, blank=False, null=False, default="[]", serialize=False)
    stage = models.CharField(max_length=255, blank=True, null=False)
    target_start = models.DateTimeField(null=True, verbose_name='目标开始时间', help_text='目标开始时间')
    target_end = models.DateTimeField(null=True, verbose_name='目标结束时间', help_text='目标结束时间')
    actual_start = models.DateTimeField(null=True, verbose_name='实际开始时间', help_text='实际开始时间')
    actual_end = models.DateTimeField(null=True, verbose_name='实际结束时间', help_text='实际结束时间')
    description = models.TextField(blank=True, null=True)
    owner = models.CharField(max_length=255, blank=False, null=False)
    approval_instance = models.TextField(max_length=65535, blank=True, null=True)
    status = models.CharField(max_length=255, blank=False, null=False, default="init")
    parent = models.IntegerField(blank=False, null=True, default=None)
    has_rejected = models.BooleanField(default=False, serialize=False)
    report_components = models.CharField(max_length=255, default="1,2,3,4,5,6,7")
    issue_jql = models.TextField(blank=True, null=True)
    history_id = models.CharField(max_length=16, blank=True, null=True, help_text='自动化构建id')
    deleted = models.BooleanField(default=False, serialize=False)
    reject_count = models.IntegerField(blank=True, null=True)
    pipelines = models.CharField(max_length=64, blank=True, null=True, help_text='关联流水线', serialize=False)

    class Meta:
        db_table = 'test_plan'

    @property
    def proj_ids(self):
        return self.proj_id_list.split(',')

    @property
    def proj_names(self):
        return self.proj_name_list.split(',')

    @property
    def status_chinese(self):
        return ProgressStatus.get_chinese(self.status)

    @property
    def stage_chinese(self):
        return PlanStage.get_chinese(self.stage)

    # @property
    # def epics(self):
    #     return self.epic_ids.split(',') if self.epic_ids else None

    @property
    def story_ids(self):
        return self.stories.split(',') if self.stories else None

    @property
    def pipeline_ids(self):
        return [int(item) for item in self.pipelines.split(',')] if self.pipelines else []


class TestReviewModel(BaseModel):
    id = models.AutoField(primary_key=True, auto_created=True)
    name = models.CharField(max_length=255, blank=True, null=False)
    proj_id = models.IntegerField(blank=True, null=False)
    proj_key = models.CharField(max_length=255, blank=True, null=False)
    tree_id = models.CharField(max_length=255, blank=True, null=False, unique=True)
    target_end = models.DateTimeField(null=True, verbose_name='目标结束时间', help_text='目标结束时间')
    description = models.TextField(blank=True, null=True)
    reviewer = models.CharField(max_length=255, blank=True, null=True, serialize=False)
    creator = models.CharField(max_length=255, blank=False, null=True)
    status = models.CharField(max_length=15, blank=False, null=False, default='init')
    deleted = models.BooleanField(default=False, serialize=False)
    class Meta:
        db_table = 'test_review'

    @property
    def status_chinese(self):
        return ProgressStatus.get_chinese(self.status)

    @property
    def reviewer_list(self):
        return self.reviewer.split(',') if self.reviewer else []
