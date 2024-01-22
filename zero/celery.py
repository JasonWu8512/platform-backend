# -*- coding: utf-8 -*-
# @Time    : 2020/10/22 9:37 上午
# @Author  : zoey
# @File    : celery.py
# @Software: PyCharm
import os
import sys
from django.apps import apps
from django.conf import settings
from celery import Celery, platforms
from kombu import Queue

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zero.settings')

app = Celery('zero')

app.config_from_object('django.conf:settings', namespace='CELERY')
platforms.C_FORCE_ROOT = True

# _app_names = [config.name for config in apps.get_app_configs()]

app.conf.update(task_track_started=True)
app.conf.update(failover_strategies='shuffle')

# 设置时区
app.conf.update(enable_utc=False)
app.conf.timezone = 'Asia/Shanghai'

# 从模块中加载所有task任务
app.autodiscover_tasks()
# app.autodiscover_tasks(_app_names, related_name='tasks')
# app.autodiscover_tasks(packages=['zero.auto.tasks'], related_name='tasks')
# app.autodiscover_tasks(packages=['zero.auto.tasks'], related_name='commands')
# app.autodiscover_tasks(packages=['celeryapp.tasks'], related_name='high_celery')


# 定义不同的task队列，及对应的routing_key,为了方便，这里routing_key和queue name一致
_task_queues = (
    Queue('celery', routing_key='celery'),
    Queue('high_celery', routing_key='high_celery'),
    # Queue('low_priority', routing_key='low_priority'),
)
app.conf.update(task_queues=_task_queues)

# 定义哪些task任务属于哪个任务队列
_task_routes = \
    [('zero.jira.tasks.*', {"queue": 'celery'}),
     ('zero.auto.tasks.*', {"queue": 'celery'}),
     ('zero.mock.tasks.*', {"queue": 'high_celery'}),
     ('zero.warehouse.tasks.*', {"queue": 'celery'}),
     ('zero.coverage.tasks.*', {"queue": 'celery'})
     # ('celeryapp.tasks.low_celery.*', {'queue': 'low_priority'}),
     ]
app.conf.update(task_routes=(_task_routes,))
