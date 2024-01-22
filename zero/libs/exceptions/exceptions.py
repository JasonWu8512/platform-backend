# -*- coding: utf-8 -*-
# @Time    : 2020/10/21 1:18 下午
# @Author  : zoey
# @File    : exceptions.py
# @Software: PyCharm
from rest_framework import status
from rest_framework.exceptions import APIException


class ValidateException(Exception):
    def __init__(self, error_details):
        super(ValidateException, self).__init__(error_details)
        self.err_details = error_details

    @property
    def err_data(self):
        msg = {
            'err_details': self.err_details,
        }
        return msg


class RedisException(Exception):
    """ Redis 错误 """


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable, try again later.'
    default_code = 'service_unavailable'


class RetryException(Exception):
    """ 用于重试的报错，发起后，需要catch住进行重试 """
