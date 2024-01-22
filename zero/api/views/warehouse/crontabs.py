# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/3 4:07 下午
@Author  : Demon
@File    : crontabs.py
"""

import pytz
from django_celery_beat.models import CrontabSchedule
from zero.api.views.warehouse.serializer import CrontabSerializer
from zero.api import BaseViewSet
import zero.utils.superResponse as Response
from zero.api.views.warehouse.PageNigation import UdfLimitOffsetPagination
from zero.warehouse import models


class CrontabViewSet(BaseViewSet):
    queryset = CrontabSchedule.objects.all()

    serializer_class = CrontabSerializer

    def list(self, request, *args, **kwargs):
        qset = CrontabSchedule.objects.all()
        data = []
        for _ in qset:

            data.append({
                "id": _.id,
                'minute': _.minute,
                'hour': _.hour,
                'day_of_week': _.day_of_week,
                'day_of_month': _.day_of_month,
                'month_of_year': _.month_of_year,
                'timezone': str(_.timezone),
            })
        return Response.success(data=data)

    def create(self, request, *args, **kwargs):
        request.data.update(timezone=pytz.timezone(request.data.get('timezone')))
        schedule, _ = CrontabSchedule.objects.get_or_create(
            **request.data
        )
        return Response.success()
