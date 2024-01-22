# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/4 5:14 下午
@Author  : Demon
@File    : PageNigation.py
"""


from rest_framework.pagination import LimitOffsetPagination

class UdfLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 20