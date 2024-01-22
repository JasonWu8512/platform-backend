# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/8 4:30 下午
@Author  : Demon
@File    : CheckTypeEnums.py
"""

from enum import Enum

class CheckTypeEnums(Enum):

    RANGE_THRESHOLD = "RANGE_THRESHOLD"
    LOGIC_CHECK = "LOGIC_CHECK"
    CONTAIN_CONTENT_ENUM = "CONTAIN_CONTENT_ENUM"
    EQUAL_CONTENT_ENUM = "EQUAL_CONTENT_ENUM"
    ROWCOUNT_CHAINRATE = "ROWCOUNT_CHAINRATE"
    ROWCOUNT_VARIANCE = "ROWCOUNT_VARIANCE"
    ROWCOUNT = "ROWCOUNT"
    COUNT_ENUM = "COUNT_ENUM"

if __name__ == '__main__':
    print(CheckTypeEnums.LOGIC_CHECK.value, CheckTypeEnums.COUNT_ENUM == 'COUNT_ENUM')
