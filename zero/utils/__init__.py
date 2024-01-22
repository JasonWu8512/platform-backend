# -*- coding: utf-8 -*-
# @Time    : 2020/11/4 4:57 下午
# @Author  : zoey
# @File    : __init__.py.py
# @Software: PyCharm
from zero.libs.exceptions.exceptions import ValidateException


def get_object_or_not_found(
        klass, _select_models=(), _prefetch_models=(), _original_manager: bool = False, _err_msg=None, **kwargs):
    """
    :param _original_manager:
    :param _err_msg:
    :type klass: (() -> T) | T
    :type _select_models: list
    :type _prefetch_models: list
    :rtype: T
    :raise: serializers.ValidationError
    """
    try:
        if _original_manager is False:
            result = klass.objects.select_related(*_select_models).prefetch_related(*_prefetch_models).get(**kwargs)
        else:
            result = klass.original_objects.select_related(*_select_models).prefetch_related(*_prefetch_models) \
                .get(**kwargs)
    except (klass.DoesNotExist, ValueError):  # 找不到
        if _err_msg:
            raise ValidateException(_err_msg)
        else:
            raise ValidateException(f'{klass.__name__} 不存在')
    return result
