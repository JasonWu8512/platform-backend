# -*- coding: utf-8 -*-
# @Time    : 2020/10/21 1:22 下午
# @Author  : zoey
# @File    : urls.py
# @Software: PyCharm
"""zero URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url, include
from django.conf.urls.static import static
from rest_framework import routers
from zero.api.views.healthy import TestHealthyViewSet
from rest_framework_jwt.views import obtain_jwt_token, verify_jwt_token, refresh_jwt_token

from zero.api.views.sonar import SonarViewSet
from zero.api.views.user import UserViewSet
from zero.api.views.jira import JiraViewSet
from zero.api.views.pxxmock import MockViewSet, MockSwitchViewSet
# from zero.api.views.dataTool import DataViewSet, ApolloViewSet, ApolloAppChatViewSet, ApolloIntlAppChatViewSet, \
#     ApolloIntlViewSet
from zero.api.views.dataTool import DataViewSet, ApolloViewSet, ApolloAppChatViewSet
from zero.api.views.testTrack import CaseViewSet, TestPlanViewSet, TestReviewViewSet, CaseTreeViewSet
from rest_framework.routers import Route, DynamicDetailRoute, SimpleRouter, DynamicListRoute
from zero.api.views.lesson_central.lesson_central_score import LessonScoreViewSet
from zero.api.views.organization import AceDepartmentViewSet, AceAccountViewSet, AceChatViewSet, \
    AceGitlabProjectChatViewSet, AceGitlabProjectViewSet, AceGitlabProjectPRViewSet, AceApprovalConfigViewSet
from zero.api.views.coverage import FullCoverageViewSet, JenkinsProjectCommitViewSet, CoveragePiplineViewSet, \
    JenkinsTaskViewSet, DiffCoverageViewSet, GitProjectViewSet, ServerDeployHistoryViewSet, GitLabApiViewSet
from zero.api.views.auto import AutoCaseConfigViewSet, AutoCaseTagViewSet, AutoCaseTreeViewSet, AutoAllureViewSet, \
    AutoRunHistoryViewSet


class CustomReadOnlyRouter(SimpleRouter):
    routes = [
        # List route.
        Route(
            url=r'^{prefix}$',
            mapping={
                'get': 'list',
                'post': 'create'
            },
            name='{basename}-list',
            initkwargs={'suffix': 'List'}
        ),
        # Dynamically generated list routes.
        # Generated using @list_route decorator
        # on methods of the viewset.
        DynamicListRoute(
            url=r'^{prefix}/{methodname}$',
            name='{basename}-{methodnamehyphen}',
            initkwargs={}
        ),
        # Detail route.
        Route(
            url=r'^{prefix}/{lookup}$',
            mapping={
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy'
            },
            name='{basename}-detail',
            initkwargs={'suffix': 'Instance'}
        ),
        # Dynamically generated detail routes.
        # Generated using @detail_route decorator on methods of the viewset.
        DynamicDetailRoute(
            url=r'^{prefix}/{lookup}/{methodname}$',
            name='{basename}-{methodnamehyphen}',
            initkwargs={}
        ),
    ]


def url_register(router, view_sets):
    """ 用于绑定URL """
    for name, view_set in view_sets:
        router.register(name, view_set, name)


jlgl_router = CustomReadOnlyRouter()
url_register(jlgl_router, [('user', UserViewSet),
                           ('jira', JiraViewSet),
                           ('', MockViewSet),
                           ('mock', MockSwitchViewSet),
                           ('dataTool', DataViewSet),
                           ('dataTool/apollo/config', ApolloViewSet),
                           #  ('dataTool/apolloIntl/config', ApolloIntlViewSet),
                           ('dataTool/apollo/notify', ApolloAppChatViewSet),
                           #   ('dataTool/apolloIntl/notify', ApolloIntlAppChatViewSet),
                           ('test/plan', TestPlanViewSet),
                           ('test/manual/case', CaseViewSet),
                           ('test/case/tree', CaseTreeViewSet),
                           ('test/review', TestReviewViewSet),
                           ('lesson', LessonScoreViewSet),
                           ('ace/department', AceDepartmentViewSet),
                           ('ace/account', AceAccountViewSet),
                           ('ace/chat', AceChatViewSet),
                           ('ace/gitlab/project', AceGitlabProjectViewSet),
                           ('ace/gitlab/chat_config', AceGitlabProjectChatViewSet),
                           ('ace/gitlab/pr_config', AceGitlabProjectPRViewSet),
                           ('ace/approval/notify_config', AceApprovalConfigViewSet),
                           ('coverage/git/project', GitProjectViewSet),
                           ('coverage/full/report', FullCoverageViewSet),
                           ('coverage/diff/report', DiffCoverageViewSet),
                           ('coverage/pipeline', CoveragePiplineViewSet),
                           ('coverage/jenkins/task', JenkinsTaskViewSet),
                           ('coverage/jenkins/commit', JenkinsProjectCommitViewSet),
                           ('coverage/jenkins/server/deploy/history', ServerDeployHistoryViewSet),
                           ('auto/case/config', AutoCaseConfigViewSet),
                           ('auto/case/tag', AutoCaseTagViewSet),
                           ('auto/case/tree', AutoCaseTreeViewSet),
                           ('auto/case/allure', AutoAllureViewSet),
                           ('auto/case/run/history', AutoRunHistoryViewSet),
                           ('gitlab', GitLabApiViewSet)
                           ])

urlpatterns = [
    url(r'^user/login', obtain_jwt_token, name='login'),
    url(r'^healthy', TestHealthyViewSet.as_view()),
    url(r'^sonar', SonarViewSet.as_view()),
    url(r'^bigdata/', include('zero.api.views.warehouse.urls')),
    url(r'^buried/', include('zero.api.views.buried.urls')),
    url(r'^', include(jlgl_router.urls)),

    # url(r"^login/$", )
]
