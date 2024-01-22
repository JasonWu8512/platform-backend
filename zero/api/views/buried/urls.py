# -*- coding: utf-8 -*-
"""
@Time    : 2021/6/10 6:11 下午
@Author  : Demon
@File    : buriedDeal.py
"""
from django.conf.urls import url, include
from zero.api.views.buried.buriedDeal import BuriedViewSet, BuriedColumnEnumsViewSet, BuriedEventViewSet, BuriedCheckViewSet, BuriedAmpProfileViewSet

urlpatterns = [
    url(r'^project/fetchList$', BuriedViewSet.as_view(actions={"post": "list_project"}), name='project_fetch_list'),
    url(r'^event/fetchList$', BuriedEventViewSet.as_view(actions={"post": "list_event"}), name='event_fetch_list'),
    url(r'^event/fetchColumnEnum$', BuriedColumnEnumsViewSet.as_view(actions={"post": "list_enum"}), name='column_list'),

    url(r'^event/checkIsExistBuried$', BuriedCheckViewSet.as_view(actions={"post": "check_enum"}), name='check_buried'),
    url(r'^event/getUserEvents$', BuriedAmpProfileViewSet.as_view(actions={"post": "get_events_by_uid"}), name='get_events_by_uid'),
]
