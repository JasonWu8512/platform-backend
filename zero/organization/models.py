# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
import uuid
from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from zero.libs.baseModel import BaseModel


class AceAccount(models.Model):
    uid = models.CharField(unique=True, max_length=32)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deactivated_at = models.DateTimeField()
    name = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(unique=True, max_length=11, blank=True, null=True)
    email = models.CharField(unique=True, max_length=50, blank=True, null=True)
    default_jira_project = models.CharField(max_length=50)
    sync_calendar = models.IntegerField()
    default_gitlab_project = models.CharField(max_length=50, blank=True, null=True)
    unionid = models.CharField(unique=True, max_length=30, blank=True, null=True)
    alarm_openid = models.CharField(unique=True, max_length=30, blank=True, null=True)
    is_subscribe = models.IntegerField()
    user_info = models.TextField()
    wxwork_user_id = models.CharField(max_length=30)
    lark_open_id = models.CharField(unique=True, max_length=50, blank=True, null=True)
    enable_vesta = models.IntegerField()
    password_jira = models.CharField(max_length=256, blank=True, null=True)
    lark_user_id = models.CharField(unique=True, max_length=50, blank=True, null=True)
    objects = models.Manager()
    user_role = models.CharField()

    class Meta:
        app_label = "zero.organization"
        db_table = 'ace_account'

    @property
    def jira_user(self):
        user = User.objects.filter(email=self.email)
        if len(user):
            return user.first().username


class AceDepartment(models.Model):
    uid = models.CharField(unique=True, max_length=32)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deactivated_at = models.DateTimeField()
    name = models.CharField(max_length=50, blank=True, null=True)
    department_id = models.CharField(unique=True, max_length=50, blank=True, null=True)
    open_department_id = models.CharField(unique=True, max_length=50, blank=True, null=True)
    parent_department_id = models.CharField(max_length=50, blank=True, null=True)
    parent_open_department_id = models.CharField(max_length=50, blank=True, null=True)
    leader_id = models.CharField(max_length=50, blank=True, null=True)
    count = models.CharField(max_length=50, blank=True, null=True)
    leader_email = models.CharField(max_length=50, blank=True, null=True)
    parent_open_department_ids = models.CharField(max_length=10000, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        app_label = "zero.organization"
        db_table = 'ace_department'



class AceDepartmentAccount(models.Model):
    uid = models.CharField(unique=True, max_length=32)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deactivated_at = models.DateTimeField()
    open_department_id = models.CharField(max_length=50)
    account_id = models.CharField(max_length=50)
    objects = models.Manager()

    class Meta:
        app_label = "zero.organization"
        db_table = 'ace_department_account'


class AceChat(models.Model):
    uid = models.CharField(unique=True, max_length=32)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deactivated_at = models.DateTimeField()
    chat_id = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    name = models.CharField(max_length=50)
    owner_user_id = models.CharField(max_length=50)

    class Meta:
        app_label = "zero.organization"
        db_table = 'ace_chat'


class AceGitlabProject(models.Model):
    uid = models.CharField(unique=True, max_length=32)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deactivated_at = models.DateTimeField()
    project = models.CharField(max_length=50)
    path = models.CharField(max_length=50)
    project_id = models.CharField(max_length=50)
    project_namespace = models.CharField(max_length=50)

    class Meta:
        app_label = "zero.organization"
        db_table = 'ace_gitlab_project'


class AceGitlabProjectChat(BaseModel):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    deactivated_at = models.DateTimeField(default=datetime.utcfromtimestamp(0))
    project = models.CharField(max_length=50)
    chat_id = models.CharField(max_length=50)
    source_branch = models.CharField(max_length=50, blank=True, null=True)
    target_branch = models.CharField(max_length=50)
    is_active = models.IntegerField()
    is_jira_active = models.IntegerField(blank=True, null=True)

    class Meta:
        app_label = "zero.organization"
        db_table = 'ace_gitlab_project_chat'


class AceLarkCallback(models.Model):
    uid = models.CharField(unique=True, max_length=32)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deactivated_at = models.DateTimeField()
    instance_code = models.CharField(max_length=50, blank=True, null=True)
    callback_type = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    approval_code = models.CharField(max_length=50, blank=True, null=True)
    approval_name = models.CharField(max_length=50, blank=True, null=True)
    form = models.CharField(max_length=10000, blank=True, null=True)
    user_id = models.CharField(max_length=50, blank=True, null=True)
    result = models.CharField(max_length=1023, blank=True, null=True)
    user_name = models.CharField(max_length=50, blank=True, null=True)
    ggr_result = models.CharField(max_length=1023, blank=True, null=True)
    picture_book_result = models.CharField(max_length=1023, blank=True, null=True)
    niuwa_be_result = models.CharField(max_length=1023, blank=True, null=True)

    class Meta:
        app_label = "zero.organization"
        db_table = 'ace_lark_callback'


class AceJiraProjectChat(BaseModel):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    deactivated_at = models.DateTimeField(default=datetime.utcfromtimestamp(0))
    project = models.CharField(max_length=50)
    chat_id = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.IntegerField(blank=True, null=True)

    class Meta:
        app_label = "zero.organization"
        db_table = 'ace_jira_project_chat'
