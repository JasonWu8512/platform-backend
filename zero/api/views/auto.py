# -*- coding: utf-8 -*-
# @Time    : 2021/3/12 11:30 上午
# @Author  : zoey
# @File    : auto.py
# @Software: PyCharm
from zero.api import BaseViewSet
from django.db.models import Q
from rest_framework.decorators import list_route, detail_route
from zero.auto.siris import *
from zero.auto.commands import gitTool
from mongoengine import Q as mgQ
from zero.api.decorators import schema
from zero.utils.format import get_data
from zero.api.decorators import login_or_permission_required
from zero.utils.format import check_cron_format
from django_celery_beat.models import CrontabSchedule, PeriodicTask
from django.db import transaction
from zero.auto.tasks import generate_allure_report, trigger_auto_case_run
from zero.coverage.commands import jenkinsTool, JenkinsTaskStatus
import zero.utils.superResponse as Response
import logging
import json

trace = logging.getLogger('trace')


class AutoCaseTagViewSet(BaseViewSet):

    queryset = AutoCaseTags.objects.filter()
    serializer_class = CaseTagsSerializer

    def list(self, request, *args, **kwargs):
        """标签列表"""
        data = self.serializer_class(self.get_queryset(), many=True).data
        return Response.success(data=data)

    @list_route(methods=['post'], url_path='fetch')
    def fetch_tags_from_git(self, request):
        """更新标签"""
        tags = gitTool.get_tag_list()
        for tag in tags:
            try:
                AutoCaseTags.objects.get_or_create(name=tag)
            except Exception as e:
                trace.error(e)
                continue
        AutoCaseTags.objects.filter().exclude(name__in=tags).delete()
        return Response.success()


class AutoCaseTreeViewSet(BaseViewSet):

    queryset = AutoCaseTree.query_all()
    serializer_class = CaseTreeSerializer

    def list(self, request, *args, **kwargs):
        """用例树"""
        data = self.serializer_class(AutoCaseTree.query_all(), many=True).data
        return Response.success(data=data)

    @list_route(methods=['post'], url_path='fetch')
    def fetch_case_from_git(self, request):
        """刷新用例树"""
        case_tree = gitTool.get_case_tree_list(dir='testcase')
        children = case_tree[0].get('children')
        children_keys = [child['id'] for child in children]
        for child in children:
            try:
                AutoCaseTree.base_upsert({'id': child['id']}, **{'children': child['children'], 'name': child['name']})
            except Exception as e:
                trace.error(e)
                continue
        query = mgQ(id__nin=children_keys)
        AutoCaseTree.objects(query).delete()
        return Response.success()


class AutoCaseConfigViewSet(BaseViewSet):

    queryset = AutoCaseConfig.query_all()
    serializer_class = CaseConfigSerializer

    @login_or_permission_required('qa.edit')
    @schema(CreateCaseConfigSchema)
    def create(self, request, *args, **kwargs):
        """创建或更新一个自动化用例配置"""
        # 校验定时表达式
        if self.filtered['crontab_schedule']:
            if not check_cron_format(self.filtered['crontab_schedule']):
                return Response.bad_request(message='cron表达式验证不通过')
            else:
                crons = self.filtered['crontab_schedule'].split(' ')
                # 在Django的celery_beat CrontabSchedule表中查询或创建这个crontab
                _, created = CrontabSchedule.objects.get_or_create(minute=crons[0], hour=crons[1], day_of_week=crons[4],
                                                                   day_of_month=crons[2], month_of_year=crons[3],
                                                                   timezone='Asia/Shanghai')
        # 创建时不能重名
        if not request.data.get('id') and len(AutoCaseConfig.objects(name=self.filtered['name'])):
            return Response.bad_request(message='任务名称已存在请重新输入')
        try:
            if request.data.get('id'):
                with transaction.atomic():
                    # 创建/更新自动化配置
                    config = AutoCaseConfig.base_upsert({'id': request.data.get('id')}, **dict(self.filtered, **{'crontab_id': None if not self.filtered['crontab_schedule'] else _.id }))
            else:
                config = AutoCaseConfig.objects().create(**dict(self.filtered, **{"creator": self.username, 'crontab_id': None if not self.filtered['crontab_schedule'] else _.id}))
            # 在django-celery-beat PeriodicTask创建定时任务
            if config.crontab_id:
                PeriodicTask.objects.update_or_create(task='zero.auto.tasks.trigger_auto_case_run',
                                                      kwargs=json.dumps({"config_id": config.id}),
                                                      defaults={'name': f'{config.name}-{config.id}',
                                                                'enabled': config.enable_auto_trigger,
                                                                'crontab_id': config.crontab_id})
        except Exception as e:
            return Response.bad_request(message=e.message)
        return Response.success()

    @schema(CaseConfigListSchema)
    def list(self, request, *args, **kwargs):
        """配置列表"""
        offset, limit, name = get_data(self.filtered, 'offset', 'limit', 'name')
        query = mgQ()
        if name:
            query &= mgQ(name__contains=name)
        queryset = AutoCaseConfig.objects(query).order_by('-created_at')
        total = len(queryset)
        data = CaseConfigSerializer(queryset[offset: offset + limit], many=True).data
        return Response.success(data={'data': data, 'total': total})

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """删除自动化配置"""
        id = kwargs.get('pk')
        # 删除自动化用例配置
        AutoCaseConfig.hard_delete(**{'id': id})
        # 删除关联的自动化任务
        PeriodicTask.objects.filter(name__endswith=id).delete()
        return Response.success()

    @login_or_permission_required('qa.edit')
    @list_route(methods=['post'], url_path='run/(?P<cid>[^/]+)')
    def run_case(self, request, cid=None):
        """执行用例"""
        config_id = cid
        # trigger_auto_case_run(config_id=config_id, username=self.username)
        trigger_auto_case_run.apply_async(kwargs={"config_id": config_id, "username": self.username}, countdown=1)
        return Response.success()

    @list_route(methods=['post'], url_path='trigger_run/(?P<cid>[^/]+)')
    def trigger_run_case(self, request, cid=None):
        """执行用例"""
        config_id = cid
        # trigger_auto_case_run(config_id=config_id, username=self.username)
        trigger_auto_case_run.apply_async(kwargs={"config_id": config_id, "username": "jenkins"}, countdown=1)
        return Response.success()

    @list_route(methods=['post'], url_path='trigger_run_by_ops')
    def trigger_run_case_by_ops(self, request):
        """执行用例"""
        request_body = request.data
        trace.info(request_body)
        config_id = request_body.get('cid')
        if not config_id:
            return Response.bad_request(message='cid is required')
        trigger_auto_case_run.apply_async(kwargs={"config_id": config_id, "username": "ops", "alert_when_fail": True}, countdown=1)
        return Response.success()

class AutoRunHistoryViewSet(BaseViewSet):
    """自动化执行历史记录"""
    queryset = AutoCaseRunHistory.objects.filter()
    serializer_class = AutoRunHistorySerializer

    @schema(GetBuildHistorySchema)
    def list(self, request, *args, **kwargs):
        """自动化执行记录历史"""
        offset, limit, name, config_id = get_data(self.filtered, 'offset', 'limit', 'config_name', 'config_id')
        query = Q()
        if name:
            query &= Q(auto_config_name__contains=name)
        elif config_id:
            query = Q(auto_config_id=config_id)
        queryset = AutoCaseRunHistory.objects.filter(query).order_by('-created_at')
        data = AutoRunHistorySerializer(queryset[offset: offset+limit], many=True).data
        return Response.success(data={'data': data, 'total': len(queryset)})


class AutoAllureViewSet(BaseViewSet):
    """自动化allure报告"""
    queryset = AutoCaseAllureReport.objects().all()
    serializer_class = AllureReportSerializer

    def get(self, request, pk=None):
        """根据historyid获取报告概览及用例套详情"""
        pass

    @list_route(methods=['get'], url_path='detail/(?P<cid>[^/]+)')
    def get_case_allure_detail(self, request, cid):
        """获取单个用例执行详情"""
        caseid = cid
        query = AutoCaseAllureDetail.query_first(**{'id': caseid})
        data = AllureCaseDetailSerializer(query).data
        return Response.success(data=data)







