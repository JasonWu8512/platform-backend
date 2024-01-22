# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/3 10:09 下午
@Author  : Demon
@File    : serializer.py
"""

from rest_framework import serializers
from zero.warehouse import models
from django_celery_beat.models import CrontabSchedule

class MonitorTableConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MonitorTableConfig
        # fields = "__all__"
        # read_only_fields = ('id', 'dbname', 'tbname', 'field_name', 'rule_logic_monitor')
        fields = ('name', 'dbname', 'tbname', 'term', 'field_name', 'rule_logic_monitor',
                  'part_field', 'part_fmt', 'warn_grad', 'cron_rule', 'one_off')


class MonitorRulesSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MonitorRules
        fields = "__all__"


class CrontabSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrontabSchedule
        fields = "__all__"

