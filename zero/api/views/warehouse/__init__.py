# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/3 8:39 下午
@Author  : Demon
@File    : __init__.py.py
"""


'''
celery worker --app=zero --loglevel=info
celery -A zero beat -l info  --scheduler django_celery_beat.schedulers:DatabaseScheduler
'''