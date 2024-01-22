# -*- coding: utf-8 -*-
# @Time    : 2020/10/21 1:10 下午
# @Author  : zoey
# @File    : healthy.py
# @Software: PyCharm

import datetime
import json

from rest_framework.response import Response
from rest_framework.views import APIView
from zero.user.tasks import sync_user_from_jira, User
from zero.coverage.models import FullCoverage, DiffCoverage, JenkinsBuildTask, CoveragePipeline
# from zero.jira.tasks import _sync_sprints, _sync_boards, sync_jira_issue


class TestHealthyViewSet(APIView):

    # @login_or_permission_required('qa.edit')
    def get(self, request):
        pipelines = CoveragePipeline.objects.all()
        omo = []
        trade = []
        jlgl = []
        reading = []
        for pipeline in pipelines:
            if pipeline.step2:
                coverage_param = json.loads(pipeline.coverage_params)
                coverage_param['proj_lang'] = 'java'
                pipeline.coverage_params = json.dumps(coverage_param)
            if pipeline.name.startswith('h5/'):
                pipeline.terminal = 'FE'
            if pipeline.name.startswith('增长中台') or pipeline.name.startswith('下沉') or pipeline.name.startswith('推广人'):
                pipeline.business = 'omo'
                omo.append(pipeline.project_id)
            elif pipeline.name.startswith('交易中台'):
                pipeline.business = 'trade'
                trade.append(pipeline.project_id)
            elif pipeline.name.startswith('叽里呱啦'):
                pipeline.business = 'jlgl'
                jlgl.append(pipeline.project_id)
            elif pipeline.name.startswith('呱呱阅读'):
                pipeline.business = 'reading'
                reading.append(pipeline.project_id)
            pipeline.save()


        # _sync_boards()
        # _sync_sprints()
        # sync_jira_issue()
        # sync_user_from_jira()
        # user = User.objects.get(username='zoey')
        # permisstions = list(user.get_all_permissions())
        return Response(data={'msg': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    def post(self, request):
        return Response(data={'msg': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
