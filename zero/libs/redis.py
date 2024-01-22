# -*- coding: utf-8 -*-
# @Time    : 2020/10/21 1:17 下午
# @Author  : zoey
# @File    : redis.py
# @Software: PyCharm
import redis
from django.conf import settings
from zero.libs.exceptions.exceptions import RedisException


class RedisClient(object):
    """ 管理全部的 Redis 连接 """
    _clients = {}

    @classmethod
    def clear_cache(cls):
        cls._clients = {}

    @classmethod
    def get_client(cls, usage: str = None) -> redis.StrictRedis:
        if usage in cls._clients:
            return cls._clients[usage]
        config = settings.NEW_REDIS_ACCESS.get(usage, None)
        if not config:
            raise RedisException('{} not allowed.'.format(usage))
        client = redis.StrictRedis(
            host=config['host'],
            port=config.get('port', 6379),
            db=config.get('db', 0),
            password=config.get('password', None),
            socket_timeout=10,
            socket_connect_timeout=10,
        )
        cls._clients[usage] = client
        return cls._clients[usage]
