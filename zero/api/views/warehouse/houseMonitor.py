# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/3 4:07 下午
@Author  : Demon
@File    : houseMonitor.py
"""

import json
from zero.warehouse.models import MonitorTableConfig, MonitorRules
from zero.api.views.warehouse.serializer import MonitorTableConfigSerializer, MonitorRulesSerializer
from zero.api import BaseViewSet
from rest_framework.decorators import api_view
from zero.api.decorators import login_or_permission_required
from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule
import zero.utils.superResponse as Response
from zero.api.views.warehouse.PageNigation import UdfLimitOffsetPagination
from zero.warehouse.tasks import dispatch



class MonitorRulesViewSet(BaseViewSet):

    def list(self, request, *args, **kwargs):
        page = UdfLimitOffsetPagination()
        page_rules = page.paginate_queryset(
            queryset=MonitorRules.objects.all().order_by('-create_at'),
            request=request,
            view=self
        )
        page_data = MonitorRulesSerializer(instance=page_rules, many=True)
        return page.get_paginated_response(page_data.data)


class MonitorConfigViewSet(BaseViewSet):
    queryset = MonitorTableConfig.objects.all()
    serializer_class = MonitorTableConfigSerializer
    # serializer_class = OffsetLimitSiri

    def list(self, request, *args):
        # 获取所有监控配置规则信息
        queryset = MonitorTableConfig.objects.all()
        qs = MonitorTableConfigSerializer(queryset, many=True).data

        return Response.success(qs)

    @login_or_permission_required(['qa.edit'])
    def create(self, request, *args, **kwargs):
        # 创建实例
        data = request.data
        print("create()", data)
        try:
            moni_ruler = MonitorRules.objects.get(pk=data['term_id'])
            # data.update(**dict(term=moni_ruler, cron_rule=cron_ruler))
            obj = MonitorTableConfig.objects.create(**data)
            # # 创建PeriodicTask任务，传递id

            PeriodicTask.objects.create(
                name=data.get("name"),
                task=dispatch(monitor_type=moni_ruler.term).name,
                crontab_id=request.data.get("cron_rule_id"),
                one_off=False,
                kwargs=json.dumps({"params": data}),
            )
            # monitor_func.apply(args=(request.data, ))
            return Response.success()
        except Exception as e:
            return Response.bad_request(str(e))

    @login_or_permission_required(['qa.edit'])
    def update(self, request, *args, **kwargs):
        """更新"""
        try:
            moni_ruler = MonitorRules.objects.get(pk=request.data['term_id'])

            obj = MonitorTableConfig.objects.get(pk=request.data.get("id"))
            pt = PeriodicTask.objects.get(name=obj.name)
            obj.__dict__.update(**request.data)
            # obj.update(**request.data)
            print(obj.name)
            pt.__dict__.update(**dict(
                name=request.data.get("name"),
                task=dispatch(monitor_type=moni_ruler.term).name,
                crontab_id=request.data.get("cron_rule_id"),
                one_off=False,
                kwargs=json.dumps(request.data)
            ))
            obj.save()
            pt.save()
            return Response.success()
        except MonitorTableConfig.DoesNotExist as e:
            return Response.bad_request(data="没有该条记录")
        except Exception as e:
            return Response.bad_request(data=str(e))

    @login_or_permission_required(['qa.edit'])
    def destroy(self, request, *args, **kwargs):
        try:
            MonitorTableConfig.objects.get(pk=request.data.get("id")).delete()
            return Response.success()
        except MonitorTableConfig.DoesNotExist as e:
            return Response.bad_request(data="没有该条记录")



