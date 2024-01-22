# -*- coding: utf-8 -*-
# @Time    : 2021/7/19 3:38 下午
# @Author  : zoey
# @File    : admin.py
# @Software: PyCharm
from django.contrib import admin
#  from zero.dataTool.models import ApolloAppItems, ApolloIntlAppItems
from zero.dataTool.models import ApolloAppItems


class ApolloAppItemsAdmin(admin.ModelAdmin):
    list_display = ('appId', 'key',)
    list_filter = ['appId']
    search_fields = ['appId', 'key']


# class ApolloIntlAppItemsAdmin(admin.ModelAdmin):
#     list_display = ('appId', 'key',)
#     list_filter = ['appId']
#     search_fields = ['appId', 'key']


admin.site.register(ApolloAppItems, ApolloAppItemsAdmin)
#  admin.site.register(ApolloIntlAppItems, ApolloIntlAppItemsAdmin)
