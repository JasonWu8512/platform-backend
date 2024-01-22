# -*- coding: utf-8 -*-
# @Time    : 2020/11/2 1:02 下午
# @Author  : zoey
# @File    : admin.py
# @Software: PyCharm

from django.contrib import admin
from zero.jira.models import JiraIssue


class JiraIssueAdmin(admin.ModelAdmin):
    list_display = ('updated_at', 'id', 'key', 'type', 'created', 'updated')
    list_filter = ['type']
    search_fields = ['type']


admin.site.register(JiraIssue, JiraIssueAdmin)
