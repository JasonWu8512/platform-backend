# -*- coding: utf-8 -*-
# @Time    : 2020/10/9 5:32 下午
# @Author  : zoey
# @File    : jlgl_enum.py
# @Software: PyCharm

from enum import Enum


class TupleEnum(Enum):
    def __new__(cls, value):
        obj = object.__new__(cls)
        if isinstance(value, TupleBase):
            # 将TupleBase的instance绑定到obj
            obj.original_value = value
            obj._value_ = value.value
        else:
            obj._value_ = value
        return obj


class TupleBase(object):
    def __init__(self, instance_value):
        self._value = instance_value

    @property
    def value(self):
        return self._value[0]


class ChineseEnum(TupleEnum):
    @classmethod
    def index_values(cls, index, value=None, value_list=None):
        # 返回 index 位置上的值是 value 的 enum
        if value_list:
            v_list = []
            for v in cls:
                if v.get_value_by_index(index) in value_list:
                    v_list.append(v.value)
            return v_list
        else:
            for v in cls:
                if v.get_value_by_index(index) == value:
                    return v.value
            return None

    @property
    def chinese(self):
        return self.original_value.chinese

    def get_value_by_index(self, index):
        return self.original_value.get_value_by_index(index)

    @classmethod
    def details(cls):
        return [(item.value, item.chinese) for item in cls]

    @classmethod
    def get_chinese(cls, code):
        _ = [item.chinese for item in cls if item.value == code]
        if not _:
            raise AttributeError('{}值非法'.format(code))
        return _.pop()

    @classmethod
    def get_value(cls, chinese):
        _ = [item.value for item in cls if item.chinese == chinese]
        if not _:
            raise AttributeError('{}值非法'.format(chinese))
        return _.pop()


class ChineseTuple(TupleBase):
    def get_value_by_index(self, index):
        return self._value[index]

    @property
    def chinese(self):
        return self._value[1]


class VenusEnum(Enum):

    @classmethod
    def values(cls):
        return [i.value for i in list(cls)]
