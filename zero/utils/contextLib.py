# -*- coding: utf-8 -*-
# @Time    : 2020/12/9 12:03 下午
# @Author  : zoey
# @File    : contextLib.py
# @Software: PyCharm
import contextlib
from contextlib import suppress
from rest_framework.response import Response
import logging

log = logging.getLogger('api')

@contextlib.contextmanager
def catch_error():
    # __enter__方法
    # print('open file:', file_name, 'in __enter__')
    # file_handler = open(file_name, 'r')

    try:
        yield

    except Exception as exc:
        # deal with exception
        log.error(exc.args[0])
        raise

    # finally:
    #     print('close file:', 'in __exit__')
