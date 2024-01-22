# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/18 11:21 上午
@Author  : Demon
@File    : models.py
"""

from django.db import models
from django_celery_beat.models import CrontabSchedule

class RPCUri(models.Model):
    name = models.CharField(max_length=64, help_text='名称', null=True)
    uri = models.CharField(max_length=128, help_text='url地址', null=False)
    operation = models.CharField(max_length=128, help_text='用户操作，lesson开头', null=True)
    class Meta:
        db_table = 'rpc_uri'
    def __str__(self):
        return self.name


class RPCEnv(models.Model):
    name = models.CharField(max_length=32, help_text='名称', null=True)
    env = models.CharField(max_length=32, help_text='url地址', null=True)
    class Meta:
        db_table = 'rpc_env'
    def __str__(self):
        return self.env


class RPCServer(models.Model):
    name = models.CharField(max_length=64, help_text='名称')
    server = models.CharField(max_length=128, help_text='url地址')
    class Meta:
        db_table = 'rpc_server'
    def __str__(self):
        return self.server


class LessonScore(models.Model):
    # server = models.ForeignKey(RPCServer, on_delete=models.DO_NOTHING, help_text="服务器", null=True)
    # env = models.ForeignKey(RPCEnv, help_text='环境配置', max_length=16, on_delete=models.DO_NOTHING)
    server = models.CharField(help_text="服务器", null=False, max_length=32, default='course.course.atom')
    env = models.CharField(help_text="环境配置", null=False, max_length=32, default='env')
    params = models.TextField(help_text='接口参数', null=True)
    uri = models.ForeignKey(RPCUri, on_delete=models.DO_NOTHING, help_text='url', null=True)
    data = models.TextField(help_text='查询结果', null=True)
    class Meta:
        db_table = 'lesson_score'


class BuriedTestProject(models.Model):
    # 维护象数平台埋点测试项目api_key映射
    name = models.CharField(help_text='项目名称,^_^dev结尾', max_length=64)
    api_key = models.CharField(help_text='api_key', max_length=64, unique=True)
    api_key_desc = models.CharField(help_text='api_key desc', max_length=255)
    platform = models.CharField(help_text='平台', max_length=48)
    version = models.CharField(help_text='项目当前版本', max_length=48)
    deleted = models.IntegerField(help_text='是否删除', default=0, null=False)
    is_cross_project = models.BooleanField(help_text='是否组合项目', default=False, null=False)
    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lesson_central_buriedtestproject'

