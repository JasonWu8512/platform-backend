# -*- coding: utf-8 -*-
# @Time    : 2020/11/2 1:02 下午
# @Author  : zoey
# @File    : admin.py
# @Software: PyCharm
from django.contrib import admin
from django.contrib.auth.models import Permission, ContentType


class PermissionAdmin(admin.ModelAdmin):
    # 添加时提交字段表单
    fields = ['name', 'content_type', 'codename']
    # 列表展示字段
    list_display = ('name', 'content_type', 'codename')
    # 列表过滤字段
    list_filter = ['content_type']
    # 列表搜索字段
    search_fields = ['codename']


class ContentTypeAdmin(admin.ModelAdmin):
    # 添加时提交字段表单
    fields = ['app_label', 'model']
    # 列表展示字段
    list_display = ('app_label', 'model')
    # 列表过滤字段
    list_filter = ['app_label']
    # 列表搜索字段
    search_fields = ['app_label']


admin.site.register(Permission, PermissionAdmin)
admin.site.register(ContentType, ContentTypeAdmin)
