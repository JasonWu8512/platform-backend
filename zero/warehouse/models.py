# -*- coding: utf-8 -*-
"""
@Time    : 2020/12/27 8:39 下午
@Author  : Demon
@File    : models.py
"""

from django.db import models
from django_celery_beat.models import CrontabSchedule

task_status = (
    (-1, "运行失败"),
    (0, "运行成功"),
    (2, "运行中"),
    (3, "运行中"),
)



# class TaskLog(models.Model):
#
#     task = models.CharField(help_text="任务id", max_length=64,)
#     status = models.IntegerField(help_text="任务运行状态", choices=task_status, default=0)
#     user = models.ForeignKey("user.User", help_text="任务运行成员", on_delete=models.DO_NOTHING)
#     data = models.CharField(help_text="运行结果数据", null=True, max_length=128)
#     created = models.DateTimeField(auto_now_add=True, null=True, help_text="创建时间")
#     updated = models.DateTimeField(auto_now=True, help_text="更新时间")
#
#     class Meta:
#         db_table = "task_log"


class DayPartitionAsset(models.Model):
    """每天的表的数据中资产"""

    task = models.CharField(help_text="任务id", max_length=64, null=False)
    name = models.CharField(help_text="任务名称", max_length=64, null=False)
    status = models.IntegerField(help_text="任务运行状态", choices=task_status, default=0)
    tbname = models.CharField(help_text="查询表的名称", max_length=64, null=False)
    dbname = models.CharField(help_text="查询表的库名称", max_length=32, null=False)
    part_field = models.CharField(help_text="分区字段；按照分区查询数据，对应分区记录", null=True, max_length=32)
    # user = models.ForeignKey("user.User", help_text="调度人", on_delete=models.DO_NOTHING)
    data = models.TextField(help_text="运行结果数据", null=True, )
    day_month = models.CharField(help_text="监控统计周期，DAY/MONTH/YEAR", null=False, default="DAY", max_length=32)
    out_of_limits = models.IntegerField(help_text="超过预警的次数", default=0, null=False)
    create_at = models.DateTimeField(auto_now_add=True, null=True, help_text="创建时间")
    update_at = models.DateTimeField(auto_now=True, help_text="更新时间")

    class Meta:
        db_table = "day_partition_assert"
        ordering = ['-create_at']


class MonitorRules(models.Model):
    """监控规则库基础信息"""
    rule_name = models.CharField(help_text="监控规则大分类，有效性，唯一性，准确性", max_length=32)
    rule_desc = models.CharField(help_text="规则大类的说明", max_length=128)
    term = models.CharField(help_text="具体的监控指标名称", max_length=32)
    term_desc = models.CharField(help_text="指标说明", max_length=128, null=True)
    logic_remark = models.CharField(help_text="监控规则详细说明", max_length=128, null=True)
    term_level = models.CharField(help_text="监控规则级别，字段名/表，table代表表级,field字段级", default="table", max_length=32)
    is_usedefine = models.IntegerField(help_text="是否是自定义,0:非自定义", default=0, )
    datatype_scope = models.CharField(help_text="规则适用字段类型", null=True, max_length=128)
    stats = models.IntegerField(default=1, help_text="规则是否可用")
    create_at = models.DateTimeField(help_text="创建时间", auto_now_add=True)
    update_at = models.DateTimeField(help_text="创建时间", auto_now=True)

    class Meta:
        db_table = "monitor_rules"
        ordering = ['-create_at']

    def __str__(self):
        return self.term


class MonitorTableConfig(models.Model):
    name = models.CharField(help_text="任务名称", unique=True, null=True, max_length=64)
    dbname = models.CharField(help_text="数据库", null=False, max_length=16)
    tbname = models.CharField(help_text="表名", null=False, max_length=64)
    term = models.ForeignKey(MonitorRules, on_delete=models.CASCADE, help_text="监控指标")
    field_name = models.CharField(help_text="监控的字段名，为空则是表级", null=True, max_length=32,)
    rule_logic_monitor = models.CharField(max_length=128, help_text="监控自定义json", null=True)
    pre_table = models.CharField(help_text="数据表的上游表名", null=True, max_length=32)
    # part_flag = models.IntegerField(help_text="是否分区, 1:分区", default=0, null=False)
    part_field = models.CharField(help_text="分区字段,只提供一个,为空则不存在分区查询", null=True, max_length=32)
    part_fmt = models.CharField(help_text="分区字段格式 yyyyMMdd", null=True, max_length=32)
    warn_grad = models.IntegerField(help_text="告警方式0:邮件,", default=0, null=False)
    # day_month = models.CharField(help_text="监控周期", default="DAY", null=False, max_length=32)
    is_active = models.IntegerField(default=1, help_text="是否生效", null=False)
    one_off = models.BooleanField(default=False, help_text="是否是一次性任务", null=False)
    cron_rule = models.ForeignKey(CrontabSchedule, help_text="监控执行规则", null=True, on_delete=models.DO_NOTHING)
    task_desc = models.CharField(help_text="规则的描述", null=True, max_length=64)
    create_at = models.DateTimeField(help_text="创建时间", auto_now_add=True)
    update_at = models.DateTimeField(help_text="创建时间", auto_now=True)

    class Meta:
        db_table = 'monitor_table_config'
        ordering = ['-create_at']


class MonitorResultCode(models.Model):

    code = models.CharField(help_text="监控指标码", max_length=32, null=False)
    code_desc = models.CharField(help_text="指标码描述", max_length=64, null=True)
    create_at = models.DateTimeField(help_text="创建时间", auto_now_add=True)
    update_at = models.DateTimeField(help_text="创建时间", auto_now=True)

    class Meta:
        db_table = "monitor_result_code"
        ordering = ['-create_at']

    def __str__(self):
        return self.code


class MonitorResult(models.Model):

    task = models.ForeignKey(MonitorTableConfig, help_text="任务id", null=True, on_delete=models.CASCADE)
    # name = models.CharField(help_text="任务名称", max_length=64, null=False)
    # monitor_rule = models.ForeignKey(MonitorTableConfig, on_delete=models.DO_NOTHING)
    term_value = models.CharField(help_text="最新监控结果码result_code；", null=True, max_length=64)
    # status = models.IntegerField(help_text="任务运行状态", choices=task_status, default=0)
    # tbname = models.CharField(help_text="查询表的名称", max_length=64, null=False)
    # dbname = models.CharField(help_text="查询表的库名称", max_length=32, null=False)
    data = models.TextField(help_text="监控查询数据结果", null=True)
    # day_month = models.CharField(help_text="监控统计周期，DAY/MONTH/YEAR", null=False, default="DAY", max_length=32)
    # out_of_limits = models.IntegerField(help_text="超过预警的次数", default=0, null=False)
    is_normal = models.BooleanField(help_text="结果是否正常", default=True, null=False)
    create_at = models.DateTimeField(help_text="创建时间", auto_now_add=True)
    update_at = models.DateTimeField(help_text="创建时间", auto_now=True)

    class Meta:
        db_table = 'monitor_result'
        ordering = ['-create_at']

