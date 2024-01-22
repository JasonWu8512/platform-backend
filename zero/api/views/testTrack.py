# -*- coding: utf-8 -*-
# @Time    : 2020/10/22 10:00 上午
# @Author  : zoey
# @File    : auto.py
# @Software: PyCharm
import json

import requests
from django import http
from zero.organization.models import AceAccount
from zero.testTrack.models import *
from zero.testTrack.siris import *
from xmind2testcase.utils import get_xmind_testcase_list
from zero.utils.fileHandle import store_upload_tmp_file
from zero.utils.format import get_data, mode_number
from zero.api.decorators import schema
import zero.utils.superResponse as Response
from zero.api import BaseViewSet
from zero.api.baseSiri import OffsetLimitSiri
from jira.exceptions import JIRAError
from zero.testTrack.models import ManualCase, TestPlanModel
from rest_framework.decorators import list_route, detail_route
from zero.api.decorators import login_or_permission_required
from itertools import groupby
from operator import itemgetter
from collections import Counter
from mongoengine import Q
from django.db.models import Q as dbQ
from django.db import transaction
from zero.testTrack.commands import PlanStatus, ProgressStatus, ReviewStatus, make_mode_list, build_tree, PlanStatusCounter, send_email, Header
from email.mime.text import MIMEText
from zero.testTrack.tasks import save_test_plan_tree
from zero.jira.tasks import sync_jira_basedata
from zero.jira.commands import JiraIssueType, jiraTool
from zero.utils.contextLib import catch_error
import logging
import shortuuid
import datetime

logger = logging.getLogger('api')


class CaseTreeViewSet(BaseViewSet):
    queryset = ModuleTree.objects.filter(deleted=False)
    serializer_class = CaseTreeSerializer

    @schema(GetCaseTreeSerializer)
    def list(self, request, *args, **kwargs):
        query = dbQ(deleted=False)
        name, proj_id = get_data(self.filtered, 'name', 'proj_id')
        if name:
            query = query & dbQ(name=name)
        if proj_id:
            query = query & dbQ(proj_id=proj_id)
        with catch_error():
            queryset = ModuleTree.objects.filter(query)
            data = CaseTreeSerializer(queryset, many=True).data
            parent_nodes = [node.id for node in queryset]
            while len(ModuleTree.objects.filter(parent__in=parent_nodes, deleted=False)):
                extra_queryset = ModuleTree.objects.filter(parent__in=parent_nodes, deleted=False).exclude(
                    id__in=parent_nodes)
                parent_nodes = [node.id for node in extra_queryset]
                data.extend(CaseTreeSerializer(extra_queryset, many=True).data)
            node_list = make_mode_list(data)
            node_list.sort(key=lambda x: x.id)

            tree = build_tree(node_list, None)
        return Response.success(data=tree)

    @login_or_permission_required('normal.query')
    @schema(CaseTreeSerializer)
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = ModuleTree.objects.create(**self.filtered)
        proj = JiraProject.objects.get(id=data.proj_id)
        TestReviewModel.objects.create(name=self.filtered['name'], tree_id=data.id, proj_id=data.proj_id,
                                       proj_key=proj.key, creator=self.username)
        return Response.success()

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        # tree, remove_tree, proj_id = get_data(self.filtered, 'tree', 'remove_tree', 'proj_id')
        ids = [kwargs.get('pk')]
        # ModuleTree.objects.filter(id=kwargs.get('pk')).update(deleted=True)
        nodes = ModuleTree.objects.filter(id__in=ids, deleted=False)
        with catch_error():
            while len(nodes):
                ids = list(set([str(node.id) for node in nodes] + ids))
                review_ids = list(set([node.review_id for node in nodes]))
                # 删除树及其子节点
                nodes.update(deleted=True)
                # 删除所有节点关联的评审
                TestReviewModel.objects.filter(id__in=review_ids).update(deleted=True)
                # 删除所有节点关联的功能用例
                ManualCase.objects(tree_id__in=ids).delete()
                # 删除所有节点关联的计划用例
                TestPlanCase.objects(tree_id__in=ids).delete()
                nodes = ModuleTree.objects.filter(parent__in=ids, deleted=False).all()
        return Response.success()

    @transaction.atomic
    @schema(CaseTreeSerializer)
    def partial_update(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        name = self.filtered.get('name')
        ModuleTree.objects.filter(id=pk).update(**self.filtered)
        TestReviewModel.objects.filter(tree_id=pk).update(name=name)
        return Response.success()


class CaseViewSet(BaseViewSet):
    queryset = ManualCase.query_all()
    serializer_class = ManualCaseSerializer

    @login_or_permission_required('qa.edit')
    @schema(ManualCaseSerializer)
    @list_route(methods=['post'], url_path='add')
    def add_single_case(self, request):
        # tree_id, name, importance, execution_type, steps, preconditions, qa, summary, version = get_data(self.filtered, 'tree_id', 'name',
        # 'importance', 'execution_type', 'steps', 'preconditions', 'qa', 'summary', 'version')
        case = self.filtered
        del self.filtered['created_at']
        del self.filtered['updated_at']
        tree_id = case.get('tree_id')

        with catch_error():
            exist_case = ManualCase.query_first(**{'tree_id': tree_id})
            tree_node = ModuleTree.objects.get(id=tree_id)
            case['product'] = exist_case.product if exist_case else tree_node.name
            case['suite'] = exist_case.suite if exist_case else tree_node.name
            case['creator'] = self.username
            case['summary'] = case['name']
            ManualCase.objects.create(**case)
        return Response.success()

    @transaction.atomic
    @login_or_permission_required('qa.edit')
    @schema(UploadXmindCaseSerializer)
    @list_route(methods=['post'], url_path='upload')
    def save_manualcasexmind(self, request):
        """
        xmind 转case包含以下字段
        TestCase
        :param name: test case name
        :param version: test case version infomation
        :param summary: test case summary infomation
        :param preconditions: test case pre condition
        :param execution_type: manual:1 or automate:2
        :param importance: high:1, middle:2, low:3
        :param estimated_exec_duration: estimated execution duration
        :param steps: test case step list
        """
        with catch_error():
            username = self.username
            proj_id, tree_id, file = get_data(self.filtered, 'proj_id', 'tree_id', 'case_file')
            if not len(ModuleTree.objects.filter(id=tree_id)):
                return Response.bad_request(message='该模块不存在，无法导入用例')
            case_file = store_upload_tmp_file(file, 'auto_xmind')
            case_json = get_xmind_testcase_list(case_file)
            for case in case_json:
                # 拓展字段
                id = shortuuid.uuid()
                case['id'] = id
                case['proj_id'] = proj_id
                case['tree_id'] = tree_id  # 此字段用来关联模块
                case['creator'] = username  # 此字段用来存储上传者
                case['qa'] = username  # 此字段用来存储测试执行者
                case['status'] = ReviewStatus.INIT.value  # 初始化状态为待评审
                case['reviewer'] = ''  # 用例评审人
                ManualCase.base_upsert({'id': id}, **case)
        return Response.success('success')

    @login_or_permission_required('normal.query')
    @transaction.atomic
    @schema(SingleUpdateCase)
    @list_route(methods=['patch'], url_path='(?P<cid>[^/]+)/update')
    def update_manual_case(self, request, cid=None):
        """修改用例套中的一个用例"""
        username = self.username
        type, status, case, review_id, plan_id, executor, step_results, step_status, issue_ids, smoke_check, add_step,\
            update_step, delete_step = \
            get_data(self.filtered, 'type', 'status', 'case', 'review_id', 'plan_id', 'executor', 'step_actual_results',
                     'step_actual_status', 'issue_ids', 'smoke_check', 'add_step', 'update_step', 'delete_step')
        query = {'id': cid}
        update_time = {'updated_at': datetime.datetime.now()}
        with catch_error():
            # 仅更新用例库
            if type == 'delete':
                ManualCase.hard_delete(**query)
                TestPlanCase.hard_delete(**{'case_id': cid})
            if type == 'update_case':
                plan_cases = TestPlanCase.objects(case_id=cid).values_list('plan_id', 'step_actual_results', 'step_actual_status')
                ManualCase.base_upsert(query=query, **{**case, **update_time})
                for plan_case in plan_cases:
                    if delete_step and plan_case[1]:
                        plan_case[1] = [x for index, x in enumerate(plan_case[1]) if index not in delete_step]
                        plan_case[2] = [x for index, x in enumerate(plan_case[2]) if index not in delete_step]
                    if add_step and plan_case[1]:
                        for step_number in add_step:
                            plan_case[1].insert(step_number, "")
                            plan_case[2].insert(step_number, "pass")
                    plan_case = {'importance': case['importance'], 'tree_id': case['tree_id'],
                                 'plan_id': plan_case[0], 'step_actual_results': plan_case[1],
                                 'step_actual_status': plan_case[2]}
                    TestPlanCase.base_upsert({'case_id': cid, 'plan_id': plan_case['plan_id']}, **{**plan_case, **update_time})
            # 更新计划关联的用例
            elif type == 'update_plan_status':
                # 每次缺陷列表有变化时同步一下jira的数据
                if len(JiraIssue.objects.filter(key__in=issue_ids)) != len(issue_ids):
                    sync_jira_basedata.delay()
                update_value = {**{"executor": self.username}, **update_time}
                if status:
                    update_value.update({'status': status})
                if step_status:
                    update_value.update({'step_actual_status': step_status})
                if step_results:
                    update_value.update({'step_actual_results': step_results})
                if issue_ids:
                    update_value.update({'issue_ids': issue_ids})
                plan = TestPlanModel.objects.get(id=plan_id)
                if not plan.actual_start:
                    TestPlanModel.objects.filter(id=plan_id).update(
                        actual_start=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status=ProgressStatus.INPROGRESS.value,
                    updated_at=datetime.datetime.now())

                TestPlanCase.objects(plan_id=plan_id, case_id=cid).update(**update_value)
            elif type == 'update_plan_smoke_check':
                TestPlanCase.objects(plan_id=plan_id, case_id=cid).update(smoke_check=smoke_check, updated_at=datetime.datetime.now())
                if len(TestPlanCase.objects(plan_id=plan_id, smoke_check=PlanStatus.FAIL.value)) > 0 and len(
                        TestPlanModel.objects.filter(id=plan_id, has_rejected=False)) > 0:
                    TestPlanModel.objects.filter(id=plan_id).update(has_rejected=True,
                                                                    status=ProgressStatus.REJECT.value, updated_at=datetime.datetime.now())
            # 指派用例执行人
            elif type == 'update_plan_executor':
                TestPlanCase.objects(plan_id=plan_id, case_id=cid).update(executor=executor, updated_at=datetime.datetime.now())
            # 更新评审状态
            elif type == 'update_review_status':
                if not TestReviewModel.objects.get(id=review_id).reviewer:
                    return Response.bad_request(message='请先到评审列表分配评审人')
                if username not in TestReviewModel.objects.get(id=review_id).reviewer:
                    return Response.bad_request(message='您没有权限操作')
                ManualCase.objects(**query).update(set__status=status, reviewer=username, updated_at=datetime.datetime.now())
                review = TestReviewModel.objects.get(id=review_id)
                if review.status == ProgressStatus.INIT.value:
                    TestReviewModel.objects.filter(id=review_id).update(status=ProgressStatus.INPROGRESS.value, updated_at=datetime.datetime.now())
                # 如果该评审的用例评审状态属于初始化或驳回的用例数为0，则自动更新该评审完成
                no_review_case = ManualCase.objects(tree_id=review.tree_id, status__in=[ReviewStatus.INIT.value,
                                                                                        ReviewStatus.REJECT.value])
                if len(no_review_case) == 0:
                    TestReviewModel.objects.filter(id=review_id).update(status=ProgressStatus.DONE.value, updated_at=datetime.datetime.now())
        return Response.success()

    @login_or_permission_required('normal.query')
    @schema(BatchUpdateCase)
    @transaction.atomic
    @list_route(methods=['patch'], url_path='batch')
    def batch_update_case(self, request):
        """批量操作用例（删除/执行结果/评审结果/评审人/执行人）"""
        username = self.username
        update_time = {'updated_at': datetime.datetime.now()}
        # 所有动作只有添加者和执行者可以操作。
        type, status, case_ids, case, review_id, plan_id, executor, smoke_check = get_data(self.filtered, 'type',
                                                                                           'status', 'case_ids', 'case',
                                                                                           'review_id', 'plan_id',
                                                                                           'executor', 'smoke_check')
        query = Q(id__in=case_ids)
        with catch_error():
            if type == 'delete':
                with transaction.atomic():
                    ManualCase.objects(query).delete()
                    TestPlanCase.objects(case_id__in=case_ids).delete()
            # 更新用例
            elif type == 'update_case':
                ManualCase.objects(id__in=case_ids).update(**case)
                if 'tree_id' in case.keys() or 'importance' in case.keys():
                    TestPlanCase.objects(case_id__in=case_ids).update(**{**case, **update_time})
            elif type == 'update_plan_status':
                plan = TestPlanModel.objects.get(id=plan_id)
                if not plan.actual_start:
                    TestPlanModel.objects.filter(id=plan_id).update(
                        actual_start=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), updated_at=datetime.datetime.now())
                TestPlanCase.objects(plan_id=plan_id, case_id__in=case_ids).update(status=status, updated_at=datetime.datetime.now())
            elif type == 'update_plan_smoke_check':
                TestPlanCase.objects(plan_id=plan_id, case_id__in=case_ids).update(smoke_check=smoke_check, updated_at=datetime.datetime.now())
                if len(TestPlanCase.objects(plan_id=plan_id, smoke_check=PlanStatus.FAIL.value)) > 0 and len(TestPlanModel.objects.filter(id=plan_id, has_rejected=False)) > 0:
                    TestPlanModel.objects.filter(id=plan_id).update(has_rejected=True, status=ProgressStatus.REJECT.value, updated_at=datetime.datetime.now())
            elif type == 'update_plan_executor':
                TestPlanCase.objects(plan_id=plan_id, case_id__in=case_ids).update(executor=executor, updated_at=datetime.datetime.now())
            elif type == 'update_review_status':
                if username not in TestReviewModel.objects.get(id=review_id).reviewer:
                    return Response.bad_request(message='您没有权限操作')
                ManualCase.objects(query).update(set__status=status, reviewer=username, updated_at=datetime.datetime.now())
                review = TestReviewModel.objects.get(id=review_id)
                if review.status == ProgressStatus.INIT.value:
                    TestReviewModel.objects.filter(id=review_id).update(status=ProgressStatus.INPROGRESS.value, updated_at=datetime.datetime.now())
                # 如果该评审的用例评审状态属于初始化或驳回的用例数为0，则自动更新该评审完成
                no_review_case = ManualCase.objects(tree_id=review.tree_id, status__in=[ReviewStatus.INIT.value,
                                                                                        ReviewStatus.REJECT.value])
                if len(no_review_case) == 0:
                    TestReviewModel.objects.filter(id=review_id).update(status=ProgressStatus.DONE.value, updated_at=datetime.datetime.now())

        return Response.success()

    @schema(GetCaseListSerializer)
    @list_route(methods=['get'], url_path='list')
    def get_case_list(self, request):
        with catch_error():
            offset, limit, tree_id, name, status, reviewer, creator, importance, proj_id = get_data(self.filtered, 'offset',
                                                                                            'limit', 'tree_id', 'name',
                                                                                            'status', 'reviewer',
                                                                                            'creator', 'importance',
                                                                                                     'proj_id')
            query = Q(tree_id=tree_id, name__contains=name) if tree_id else Q(proj_id=proj_id, name__contains=name)
            if status:
                query = query & Q(status__in=status)
            if reviewer:
                query = query & Q(reviewer__in=reviewer)
            if creator:
                query = query & Q(creator__in=creator)
            if importance:
                query = query & Q(importance__in=importance)
            cases = ManualCase.objects(query).limit(limit).skip(offset)
            data = ManualCaseSerializer(cases, many=True).data
            total = len(ManualCase.objects(query))
        return Response.success(data={'data': data, 'total': total})

    @list_route(methods=['post'], url_path='download')
    def down_load_case_xmind(self, request, tid=None):
        """下载用例"""
        tree_id = request.data.get('tree_id')


class TestPlanViewSet(BaseViewSet):
    queryset = TestPlanModel.objects.filter(deleted=0).all()
    serializer_class = TestPlanSerializer

    @transaction.atomic
    @schema(TestPlanSerializer)
    def create(self, request, *args, **kwargs):
        """创建测试计划"""
        with catch_error():
            plan = self.filtered
            data = request.data
            proj_ids = data.get('proj_ids')
            proj_names = data.get('proj_names')
            if not data.get('proj_ids'):
                return Response.bad_request(message='proj_ids必传')
            if data.get('stage') == PlanStage.SMOKE.value and (not data.get('story_ids')):
                return Response.bad_request(message='story_ids必传')
            plan.update({"proj_id_list": ','.join(proj_ids),
                         "proj_name_list": ','.join(proj_names),
                         "stories": ','.join(data.get('story_ids') or []),
                         "pipelines": ','.join([str(item) for item in data.get('pipeline_ids', [])])})
            plan = TestPlanModel.objects.create(**plan)
            plan_tree = [{'id': proj_id, 'name': proj_names[index], "children": []} for index, proj_id in enumerate(proj_ids)]
            TestPlanTree.base_upsert(query={"id": plan.id}, **{"id": plan.id, "tree": plan_tree})
        return Response.success()

    @schema(GetPlanSerializer)
    def list(self, request, *args, **kwargs):
        """计划列表"""

        offset, limit, name, proj_id, owner, status, stage, is_reject = get_data(
            self.filtered, 'offset', 'limit', 'name', 'proj_id', 'owner', 'status', 'stage', 'is_reject'
        )
        query = dbQ(deleted=False, name__icontains=name)
        if proj_id:
            proj_queries = [dbQ(proj_id_list__contains=i) for i in proj_id]
            proj_query = proj_queries.pop()
            for item in proj_queries:
                proj_query |= item
            query = query & proj_query
        if owner:
            query = query & dbQ(owner__in=owner)
        if status:
            query = query & dbQ(status__in=status)
        if stage:
            query = query & dbQ(stage__in=stage)
        if is_reject:
            query = query & dbQ(reject_count__gt=0)
        queryset = TestPlanModel.objects.filter(query).order_by('-created_at')
        total = len(queryset)
        serializers = TestPlanSerializer(queryset[offset:offset + limit], many=True)
        return Response.success(data={'data': serializers.data, 'total': total})

    def get(self, request, pk=None):
        # case_ids = TestPlanCase.objects.filter(review_id=pk).values('case_id')
        pass

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        """更新测试计划"""
        pk = kwargs.get('pk')
        update_time = {'updated_at': datetime.datetime.now()}
        with catch_error():
            data = request.data
            # 有项目更新，需要删除关联的用例
            origin_plan = TestPlanModel.objects.get(id=pk)
            origin_plan_ids = origin_plan.proj_ids
            tree = TestPlanTreeSerializer(TestPlanTree.query_first(**{'id': pk})).data.get('tree')
            if data.get('issue_jql'):
                try:
                    _ = jiraTool.jiraClient.search_issues(jql_str=data.get('issue_jql'), maxResults=10)
                except JIRAError as e:
                    return Response.bad_request(message=e.text)
            if 'story_ids' in data:
                data.update({'stories': ','.join(data.get('story_ids') or [])})
                del data['story_ids']
            if 'pipeline_ids' in data:
                data.update({'pipelines': ','.join([str(item) for item in data.get('pipeline_ids')] or [])})
                del data['pipeline_ids']
            if data.get('proj_ids'):
                data.update({'proj_id_list': ','.join(data.get('proj_ids', [])), 'proj_name_list': ','.join(data.get('proj_names'))})

                # 对比更新后的项目和原关联项目，按需删除关联的用例和用例树
                for proj_id in origin_plan_ids:
                    if proj_id not in data.get('proj_ids'):
                        # 删除关联的用例
                        TestPlanCase.hard_delete(**{"plan_id": pk, "proj_id": proj_id})
                        # 删除关联的用例树
                        tree = list(filter(lambda x: x['id'] != proj_id, tree))
                for index, proj_id in enumerate(data.get('proj_ids')):
                    if proj_id not in origin_plan_ids:
                        tree.append({'id': proj_id, 'name': data.get('proj_names')[index], 'children': []})
                # 更新计划关联的用例树
                TestPlanTree.base_upsert(query={'id': pk}, **{**{'id': pk, 'tree': tree}, **update_time})
                del data['proj_ids']
                del data['proj_names']
            # 更新测试计划状态前，校验所有关联case的执行状态
            # cases = TestPlanCase.query_all(**{"plan_id": pk})
            # status_set = set([case['status'] for case in cases])
            if request.data.get('status') == ProgressStatus.DONE.value:
                # if status_set not in [{PlanStatus.PASS.value, PlanStatus.SKIP.value}, {PlanStatus.PASS.value}, {PlanStatus.SKIP.value}]:
                #     return Response.bad_request(message="请先确认所有用例已执行通过")
                # else:
                data.update({'actual_end': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                TestPlanModel.objects.filter(id=pk).update(**{**data, **update_time})
            elif request.data.get('status') == ProgressStatus.REJECT.value:
                TestPlanModel.objects.filter(id=pk).update(has_rejected=True, **{**data, **update_time})
            else:
                TestPlanModel.objects.filter(id=pk).update(**{**data, **update_time})
        return Response.success()

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """删除测试计划，并删除关联的用例"""
        with catch_error():
            pk = kwargs.get('pk')
            TestPlanModel.objects.filter(id=pk).update(deleted=True)
            TestPlanCase.hard_delete(**{'plan_id': pk})
        return Response.success()

    @schema(GetCaseListSerializer)
    @detail_route(methods=['get'], url_path='case')
    def get_plan_case(self, request, pk=None):
        """获取计划关联的用例列表"""
        offset, limit, importance, tree_id, executor, proj_id, status, name = get_data(self.filtered, 'offset', 'limit',
                                                                                 'importance', 'tree_id', 'executor',
                                                                                 'proj_id', 'status', 'name')
        # 什么都不传时获取计划下所有用例
        query = Q(plan_id=pk)
        if name:
            # case_ids = TestPlanCase.objects(query).value_list('case_id')
            # case_ids = ManualCase.objects(id__in=case_ids, name__contains=request.query_params.get('name')).value_list('id')
            query = query & Q(name__contains=name)
        if importance:
            query = query & Q(importance__in=importance)
        if tree_id:
            query = query & Q(tree_id=tree_id)
        if executor:
            query = query & Q(executor__in=executor)
        if proj_id:
            query = query & Q(proj_id=proj_id)
        if status:
            query = query & Q(status__in=status)
        with catch_error():
            cases = TestPlanCase.objects(query).order_by('created_at').limit(limit).skip(offset)
            total = len(TestPlanCase.objects(query))
            data = TestPlanCaseSerializer(cases, many=True).data
        return Response.success(data={'data': data, 'total': total})

    @schema(GetPlanNoRelateCaseSerializer)
    @detail_route(methods=['get'], url_path='case/no_relate')
    def get_plan_not_relate_case(self, request, pk=None):
        """获取计划某个模块下还未关联的用例"""
        offset, limit, proj_id, tree_id = get_data(self.filtered, 'offset', 'limit', 'proj_id', 'tree_id')
        relate_query = Q(proj_id=proj_id) if not tree_id else Q(tree_id=tree_id)
        with catch_error():
            related_case = TestPlanCase.objects(relate_query & Q(plan_id=pk))
            # 已经关联的用例
            related_case_ids = [case.case_id for case in related_case]
            # 查询未关联的用例
            if request.query_params.get('name'):
                relate_query = relate_query & Q(name__contains=request.query_params.get('name'))
            if request.query_params.get('importance'):
                relate_query = relate_query & Q(importance__in=request.query_params.get('importance'))
            if request.query_params.get('creator'):
                relate_query = relate_query & Q(creator__in=request.query_params.get('creator'))
            cases = ManualCase.objects(relate_query & Q(id__nin=related_case_ids)).order_by('created_at').limit(limit).skip(offset)
            data = ManualCaseSerializer(cases, many=True).data
            total = len(ManualCase.objects(relate_query & Q(id__nin=related_case_ids)))
        return Response.success(data={'data': data, 'total': total})

    @detail_route(methods=['get'], url_path='tree')
    def get_plan_tree(self, request, pk=None):
        """获取测试计划关联的树"""
        query = Q(plan_id=pk)
        tree = TestPlanTree.query_first(**{'id': pk})
        return Response.success(data=tree.tree)

    @transaction.atomic
    @schema(RelatePlanCaseSerializer)
    @detail_route(methods=['post'], url_path='case/relate')
    def relate_plan_case(self, request, pk=None):
        """关联/取关用例"""
        tree_id, proj_id, operation, case_ids = get_data(self.filtered, 'tree_id', 'proj_id', 'operation',
                                                            'case_ids')
        tree_ids = set([])
        # 关联用例
        with catch_error():
            if operation == 'add':
                cases = ManualCase.objects(id__in=case_ids).order_by('created_at')
                for case in cases:
                    tree_ids.add(case.id)
                    query = {'plan_id': pk, 'case_id': case.id}
                    plan_case = {
                        "plan_id": pk,
                        "case_id": case.id,
                        "name": case.name,
                        "status": PlanStatus.INIT.value,
                        "executor": '',
                        "importance": case.importance,
                        "tree_id": case.tree_id,
                        "proj_id": case.proj_id
                    }
                    TestPlanCase.base_upsert(query=query, **plan_case)
            # 取关用例
            if operation == 'remove':
                if case_ids:
                    query = Q(plan_id=pk) & Q(case_id__in=case_ids)
                    TestPlanCase.objects(query).delete()
                # 全部取消关联时，必须传tree_id,如果是根节点，is_project必须为true
                elif tree_id:
                    TestPlanCase.hard_delete(**{"plan_id": pk, "tree_id": tree_id})
                elif proj_id:
                    TestPlanCase.hard_delete(**{"plan_id": pk, "proj_id": proj_id})
                else:
                    TestPlanCase.hard_delete(**{"plan_id": pk})
            save_test_plan_tree(pid=pk)
        return Response.success()

    @detail_route(methods=['get'], url_path='smoke/pass_rate')
    def get_smoke_pass_rate(self, request, pk=None):
        """测试报告之冒烟通过率"""
        with catch_error():
            smoke_plan = TestPlanModel.objects.filter(parent=pk)
            smoke_states = []
            for plan in smoke_plan:
                if not plan.story_ids:
                    continue
                cases = TestPlanCase.objects(plan_id=str(plan.id))
                status = [case.status for case in cases]
                tmp = dict(PlanStatusCounter(), **Counter(status))
                reject_count = 0
                approval_count = 0
                if plan.approval_instance:
                    instance_codes = json.loads(plan.approval_instance).get("instance_codes")
                    approval_count = len(AceLarkCallback.objects.filter(instance_code__in=instance_codes, callback_type="approval_task").exclude(status=PlanInstanceStatus.CANCELED.value))
                    reject_count = plan.reject_count or 0
                story = JiraIssue.objects.filter(id__in=plan.story_ids).values_list('summary', flat=True)
                smoke_states.append({**tmp, **{'name': plan.name, 'story': story, 'reject_count': reject_count, 'approval_count': approval_count, 'case_count': len(cases)}})
                # cases.extend(TestPlanCase.objects(plan_id=str(plan.id)))
            # 冒烟用例按模块分组
            # cases.sort(key=itemgetter('tree_id'))
            # case_groups = groupby(cases, itemgetter('tree_id'))
            # for tree_id, group in case_groups:
            #     status = [case.status for case in group]
            #     tmp = dict(PlanStatusCounter(), **Counter(status))
            #     smoke_states.append({**tmp, **{'pass_rate': mode_number(tmp[PlanStatus.PASS.value] * 100, len(status), 2),
            #                                    'name': ModuleTree.objects.get(id=tree_id).name,
            #                                    'case_count': len(status)}})
        return Response.success(data=smoke_states)

    @list_route(methods=['get'], url_path='wash_data')
    def wash_data(self, request):
        plans = TestPlanModel.objects.all()
        for plan in plans:
            sprints = []
            if plan.epics:
                try:
                    stories = JiraIssue.objects.filter(type=JiraIssueType.STORY.chinese, epic_key__in=plan.epics).values_list('sprint_id', flat=True)
                    if stories:
                        for story in stories:
                            sprints.extend(eval(story))
                except:
                    print(plan.id, sprints)
                print(plan.id, sprints)
                if sprints:
                    plan.sprint_id = sprints[0]
                    plan.save()
                else:
                    plan.sprint_id = 0
                    plan.save()
        return Response.success()

    @detail_route(methods=['get'], url_path='report')
    def get_plan_report(self, request, pk=None):
        """获取测试计划的测试报告"""
        # 获取用例执行结果
        with catch_error():
            plan = TestPlanModel.objects.get(id=pk)
            # components = ','.join(plan.report_components)
            cases = TestPlanCaseSerializer(TestPlanCase.objects(plan_id=pk), many=True).data
            tickets = JiraVersionTasksSerializer(JiraIssue.objects.filter(sprint_id__contains=f"'{plan.sprint_id}'", type=JiraIssueType.STORY.chinese),
                                                 many=True).data
            cases.sort(key=itemgetter('tree_id'))
            # 按模块对用例分组
            cases = groupby(cases, itemgetter('tree_id'))
            module_case_results = []
            total_issues = []
            total_status_list = []
            executors = set({})
            if plan.issue_jql:
                try:
                    issues = jiraTool.jiraClient.search_issues(jql_str=plan.issue_jql, maxResults=100)
                except JIRAError as e:
                    return Response.server_error(message=e.text)
                while len(issues) < issues.total:
                    issues.extend(jiraTool.jiraClient.search_issues(jql_str=plan.issue_jql, startAt=len(issues), maxResults=100))
                issue_ids = [issue.id for issue in issues]
                total_issues = JiraVersionTasksSerializer(JiraIssue.objects.filter(id__in=issue_ids, resolution__in=['完成', 'Unresolved']), many=True).data
            for key, group in cases:
                status_list = []
                # issues = []
                for case in group:
                    # 统计每个模块的用例执行情况
                    status_list.append(case.get('status'))
                    # 统计每个模块的缺陷列表
                    # issues.extend(case.get('issues'))
                    # 统计每个模块的失败用例
                    executors.add(case.get('executor'))
                total_status_list.extend(status_list)
                counter = dict(PlanStatusCounter(), **Counter(status_list))
                pass_rate = mode_number(counter.get(PlanStatus.PASS.value, 0) * 100, len(status_list), 2)
                module = ModuleTree.objects.get(id=key)
                module_case_results.append({**{'module': module.name,
                                               'case_count': len(status_list),
                                               'project': module.proj_name,
                                               # 'issue_count': len(issues),
                                               'pass_rate': pass_rate}, **counter})
                # total_issues.extend(issues)
                # total_fail_cases.extend(fail_cases)
            execute_result = Counter(total_status_list)
            issue_levels = [bug['sub_bug_level'] for bug in total_issues]
            issue_owners = [bug['bugOwner'] for bug in total_issues]
        return Response.success(data={
            'base_info': {'executors': list(executors), 'proj_names': plan.proj_names, 'owner': plan.owner,
                          'start': plan.actual_start, 'end': plan.actual_end, 'name': plan.name,
                          'description': plan.description, 'history_id': plan.history_id,
                          'pipeline_ids': plan.pipeline_ids,
                          'jql': plan.issue_jql, 'stage': plan.stage},
            'module_execute_result': module_case_results,
            'bug_list': total_issues,
            'execute_result': execute_result,
            'bug_level_charts': [[key, value] for key, value in Counter(issue_levels).items()],
            'bug_owner_charts': [[key, value] for key, value in Counter(issue_owners).items()],
            'ticket_list': tickets}
        )

    @login_or_permission_required('qa.edit')
    @detail_route(methods=['post'], url_path='send_report')
    def send_report_email(self, request, pk=None):
        from email.mime.multipart import MIMEMultipart
        with catch_error():
            img = request.data.get('img')
            receivers = request.data.get('receivers', [])
            plan = TestPlanModel.objects.get(id=pk)
            if self.username != plan.owner:
                return Response.bad_request(message='您不是此计划的负责人，不能发送报告哟')
            if self.email not in receivers:
                receivers.append(self.email)
            ace_account = AceAccount.objects.get(email=self.email)
            message = MIMEMultipart()
            message.attach(MIMEText(f'<h>{ace_account.name} （{self.email}） 发送了 {plan.name}测试报告</h>', 'html', 'utf-8'))
            subject = f'{plan.name}测试报告'
            message['Subject'] = Header(subject, 'utf-8')
            message.attach(MIMEText(f'<p><img src="{img}" alt="image1"></p>', 'html','utf-8'))
            send_email(receivers, message)
        return Response.success()

    @detail_route(methods=['post'], url_path='smoke/packaging_test')
    def create_packaging_test(self, request, pk=None):
        """ 提交开发提测审批流 """
        # 获取用例执行结果
        with catch_error():
            data = request.data
            user_email = data.get('user_email')
            instance = json.loads(TestPlanModel.objects.get(id=pk).approval_instance or "{}")
            open_id = AceAccount.objects.get(email=user_email).lark_open_id

            body = {
                "event": {
                    "type": "message",
                    "text": f"/packaging_test {data}",
                    "open_id": open_id,
                },
                "uuid": shortuuid.uuid(),
                "token": "zero_jiliguala",
            }
            resp = requests.post('https://ace.jiliguala.com/endpoints/lark/', json=body)
            if resp.status_code != http.HttpResponse.status_code:
                return http.JsonResponse(resp.json(), status=resp.status_code)

            data["instance_codes"] = instance.get("instance_codes", [])
            data["instance_codes"].append(resp.json().get("message"))
            TestPlanModel.objects.filter(id=pk).update(**{'approval_instance': json.dumps(data)})
            return Response.success()

    @detail_route(methods=['post'], url_path='smoke/packaging_test/approval_status')
    def update_approval_status(self, request, pk=None):
        """ 更新开发提测审批流状态 """
        # 获取用例执行结果
        with catch_error():
            data = request.data
            instance = json.loads(TestPlanModel.objects.get(id=pk).approval_instance)
            user_id = AceAccount.objects.get(email=data.get('user_email')).lark_user_id

            body = {
                "event": {
                    "type": "message",
                    "text": f"/approval_status -s {data.get('status')} -i {instance.get('instance_codes')[-1]}",
                    "user_id": user_id,
                },
                "uuid": shortuuid.uuid(),
                "token": "zero_jiliguala",
            }
            resp = requests.post('https://ace.jiliguala.com/endpoints/lark/', json=body)
            if resp.status_code != http.HttpResponse.status_code:
                return http.JsonResponse(resp.json(), status=resp.status_code)

            if data.get("status") == PlanInstanceStatus.REJECTED.value:
                reject_count = TestPlanModel.objects.get(id=pk).reject_count + 1
                TestPlanModel.objects.filter(id=pk).update(**{'reject_count': reject_count})
            return http.JsonResponse(resp.json(), status=resp.status_code)


class TestReviewViewSet(BaseViewSet):
    queryset = TestReviewModel.objects.filter(deleted=False).all()
    serializer_class = TestReviewSerializer

    @schema(TestReviewSerializer)
    def create(self, request, *args, **kwargs):
        with catch_error():
            data = self.filtered
            data.update({'reviewer': ','.join(request.data.get('reviewer', []))})
            TestReviewModel.objects.create(**data)
        return Response.success()

    @schema(GetReviewSerializer)
    def list(self, request, *args):
        tree_ids = ManualCase.objects.distinct("tree_id")
        offset, limit, name, status, proj_id, reviewer, creator = get_data(self.filtered, 'offset', 'limit', 'name', 'status', 'proj_id', 'reviewer', 'creator')
        query = dbQ(tree_id__in=tree_ids, deleted=False)
        if name:
            query = query & dbQ(name__icontains=name)
        if status:
            query = query & dbQ(status__in=status)
        if proj_id:
            query = query & dbQ(proj_id__in=proj_id)
        if reviewer:
            query = query & dbQ(reviewer__in=reviewer)
        if creator:
            query = query & dbQ(creator__in=creator)
        queryset = TestReviewModel.objects.filter(query).order_by('-created_at')
        total = len(queryset)
        data = TestReviewSerializer(queryset[offset:offset + limit], many=True).data
        return Response.success(data={'data': data, 'total': total})

    def get(self, request, pk=None):
        pass

    # def patch(self, request, pk=None):
    #     pass
    @login_or_permission_required('normal.query')
    @transaction.atomic
    @schema(TestReviewSerializer)
    def partial_update(self, request, *args, **kwargs):
        with catch_error():
            username = self.username
            pk = kwargs.get('pk')
            data = self.filtered

            if request.data.get('reviewer'):
                data.update({'reviewer': ','.join(request.data.get('reviewer'))})
            # if data.get('status'):
            #     review = TestReviewModel.objects.get(id=pk)
            #     if username not in review.reviewer:
            #         return Response.bad_request(message='您不在评审人列表无法执行此操作')
            TestReviewModel.objects.filter(id=pk).update(**{**data, **{'updated_at': datetime.datetime.now()}})
        return Response.success()
