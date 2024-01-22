# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/16 8:48 下午
@Author  : Demon
@File    : urls.py
"""

from django.conf.urls import url
from zero.api.views.lesson_central.lesson_central_score import LessonScoreViewSet

urlpatterns = [
    # url(r'^get_lesson_score$', LessonScoreView.as_view(), name='get_lesson_score'),
]