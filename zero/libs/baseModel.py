# -*- coding: utf-8 -*-
# @Time    : 2021/1/28 10:27 上午
# @Author  : zoey
# @File    : baseModel.py
# @Software: PyCharm
import mongoengine as mongo
from django.db import models
import datetime


class BaseModel(models.Model):
    """ 所有表的父类 """

    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", help_text="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="上次修改时间", help_text="上次修改时间")
    objects = models.Manager()


class BaseDocument(mongo.DynamicDocument):
    created_at = mongo.DateTimeField(default=datetime.datetime.now)
    updated_at = mongo.DateTimeField(default=datetime.datetime.utcnow)
    meta = {'abstract': True}

    @classmethod
    def hard_delete(cls, **query):
        return cls.objects(**query).delete()

    @classmethod
    def base_upsert(cls, query=None, **upsert_filter):
        query = query or {}
        return cls.objects(**query).modify(
            set_on_insert__created_at=datetime.datetime.now(),
            set__updated_at=datetime.datetime.now(),
            upsert=True,
            new=True,
            **upsert_filter
        )

    @classmethod
    def query_first(cls, **query):
        return cls.objects(**query).first()

    @classmethod
    def query_all(cls, **query):
        return cls.objects(**query).all()
