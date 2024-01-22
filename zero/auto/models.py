from django.db import models
from zero.libs.baseModel import BaseDocument, BaseModel
from zero.coverage.commands import JenkinsTaskStatus
import mongoengine as mongo
import shortuuid


class AutoCaseConfig(BaseDocument):
    id = mongo.StringField(primary_key=True, default=shortuuid.uuid)
    name = mongo.StringField(max_length=32, null=False)
    tags = mongo.StringField(null=True)  # 标签
    notify_chat_ids = mongo.ListField(default=[])  # 通知群
    crontab_schedule = mongo.StringField(max_length=64, null=True)
    crontab_id = mongo.IntField(null=True)
    enable_auto_trigger = mongo.BooleanField(default=False)
    cases = mongo.ListField(null=True)
    pipeline_ids = mongo.ListField(default=[])
    creator = mongo.StringField(max_length=32, null=True)
    status = mongo.StringField(max_length=16, default='pending')
    exec_env = mongo.StringField(max_length=16)

    meta = {'collection': 'auto_case_config',
            "indexes": ["name", "tags", "notify_chat_ids", "pipeline_id", "creator"]}


class AutoCaseTree(BaseDocument):
    id = mongo.StringField(primary_key=True, default=shortuuid.uuid)
    name = mongo.StringField(max_length=32, null=False)
    children = mongo.ListField()

    meta = {'collection': 'auto_case_tree',
            'indexes': ["name"]}


class AutoCaseTags(BaseModel):
    id = models.AutoField(primary_key=True, auto_created=True)
    name = models.CharField(unique=True, max_length=32)

    class Meta:
        db_table = 'auto_case_tags'


class AutoCaseRunHistory(BaseModel):
    auto_config_id = models.CharField(max_length=32, help_text='自动化用例配置集id')
    auto_config_name = models.CharField(max_length=64, help_text='自动化用例配置集名称')
    username = models.CharField(max_length=32, default='system', help_text='触发者')
    build_number = models.IntegerField(null=True, help_text='jenkins构建number')
    recover_times = models.IntegerField(default=0, help_text='重试次数')
    status = models.CharField(max_length=8, default='pending', help_text='执行状态')
    mark = models.CharField(max_length=255, null=True)

    class Meta:
        db_table = 'auto_case_run_history'

    @property
    def status_chinese(self):
        return JenkinsTaskStatus.get_chinese(self.status)


class AutoCaseAllureReport(BaseDocument):
    id = mongo.IntField(primary_key=True)
    summary = mongo.DictField()
    suites = mongo.DictField()

    meta = {'collection': 'auto_case_allure_report'}

class AutoCaseAllureDetail(BaseDocument):
    id = mongo.StringField(primary_key=True)
    detail = mongo.DictField()

    meta = {'collection': 'auto_case_allure_detail'}
