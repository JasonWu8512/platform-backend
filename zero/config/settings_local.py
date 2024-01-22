# -*- coding: utf-8 -*-
# @Time    : 2020/10/22 10:11 上午
# @Author  : zoey
# @File    : settings_local.py
# @Software: PyCharm


DATABASES = {
    'default': {
            'ENGINE': 'django.db.backends.mysql',
            'HOST': 'jira.mysql.jlgltech.com',
            'USER': 'zero',
            'PASSWORD': '123456',
            'PORT': '3306',
            'NAME': 'zero',
        }
    # 'default': {
    #     'ENGINE': 'django.db.backends.mysql',
    #     'HOST': '10.100.128.86',
    #     'USER': 'zero',
    #     'PASSWORD': 'ZG$#RkbGdyZ3I0Nu',
    #     'PORT': '3306',
    #     'NAME': 'zero',
    # }
}

# 本地调试mongo configuration
# MONGO_DB = 'ZERO_DEBUG'
# MONGO_CONN = (
#     f'mongodb://JLAdmin:niuniuniu168@10.100.128.122:27017/{MONGO_DB}?authSource=admin&authMechanism=SCRAM-SHA-1')
MONGO_DB = 'QAZERO-FAT'
MONGO_CONN = (
    f'mongodb://JLAdmin:niuniuniu168@10.100.128.122:27017/{MONGO_DB}?authSource=admin&authMechanism=SCRAM-SHA-1')

# 本地调试Redis configuration
DEFAULT_REDIS_HOST = '127.0.0.1'
DEFAULT_REDIS_PORT = '6379'
# 密码在deployment/redis.conf 中的requirepass修改
DEFAULT_REDIS_PASS = ''

# celery condifuration
# CELERY_ENABLE_UTC = False
CELERY_BROKER_URL = ['redis://:{}@{}:{}/10'.format(DEFAULT_REDIS_PASS, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)]
CELERY_RESULT_BACKEND = 'redis://:{}@{}:{}/11'.format(DEFAULT_REDIS_PASS, DEFAULT_REDIS_HOST,
                                                      DEFAULT_REDIS_PORT)  # 结果存储地址
CELERY_ACCEPT_CONTENT = ['application/json']  # 指定任务接收的内容序列化类型
CELERY_TASK_SERIALIZER = 'json'  # 任务序列化方式
CELERY_RESULT_SERIALIZER = 'json'  # 任务结果序列化方式
CELERYD_MAX_TASKS_PER_CHILD = 2  # 每个worker最多执行2个任务就摧毁，避免内存泄漏
CELERYD_PREFETCH_MULTIPLIER = 1  # celery worker 每次去redis取任务的数量
CELERYD_FORCE_EXECV = True  # 非常重要,有些情况下可以防止死锁

CELERYD_CONCURRENCY = 4  # worker并发数

CELERYBEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'  # 定时任务调度器
