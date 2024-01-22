# -*- coding: utf-8 -*-
# @Time    : 2021/2/4 5:52 下午
# @Author  : zoey
# @File    : organization.py
# @Software: PyCharm

from django.db.models import Q
from rest_framework.decorators import list_route, detail_route
from zero.organization.siri import *
from zero.organization.commands import make_mode_list, build_tree, default_deactive_time
from zero.api import BaseViewSet
from zero.testTrack.siris import ApprovalConfigSerializer
from zero.utils.contextLib import catch_error
import zero.utils.superResponse as Response
from zero.api.decorators import schema
from zero.jira.models import JiraIssue
from zero.utils.format import get_data
import datetime
import time

class AceDepartmentViewSet(BaseViewSet):
    queryset = AceDepartment.objects.filter(deactivated_at=default_deactive_time)
    serializer_class = DepartmentSiri

    @schema(getDepartmentSchema)
    def list(self, request, *args, **kwargs):
        query = Q(deactivated_at=default_deactive_time)
        open_department_id = self.filtered.get('open_department_id')
        if open_department_id:
            query = query & Q(department_id=open_department_id)
        with catch_error():
            queryset = AceDepartment.objects.filter(query)
            data = DepartmentSiri(queryset, many=True).data
            parent_nodes = [node.open_department_id for node in queryset]
            while len(AceDepartment.objects.filter(parent_open_department_id__in=parent_nodes, deactivated_at=default_deactive_time)):
                extra_queryset = AceDepartment.objects.filter(parent_open_department_id__in=parent_nodes, deactivated_at=default_deactive_time).exclude(
                    open_department_id__in=parent_nodes)
                parent_nodes = [node.open_department_id for node in extra_queryset]
                data.extend(DepartmentSiri(extra_queryset, many=True).data)
            node_list = make_mode_list(data)
            tree = build_tree(node_list, None)
        return Response.success(data=tree)


class AceAccountViewSet(BaseViewSet):
    queryset = AceAccount.objects.filter(deactivated_at=default_deactive_time)
    serializer_class = DepartmentSiri

    @schema(getDepartmentSchema)
    def list(self, request, *args, **kwargs):
        query = Q(deactivated_at=default_deactive_time)
        open_department_id = self.filtered.get('open_department_id')
        if open_department_id:
            query = query & Q(open_department_id=open_department_id)
        with catch_error():
            queryset = AceDepartment.objects.filter(query)
            data = DepartmentSiri(queryset, many=True).data
            parent_nodes = [node.open_department_id for node in queryset]
            while len(AceDepartment.objects.filter(parent_open_department_id__in=parent_nodes,
                                                   deactivated_at=default_deactive_time)):
                extra_queryset = AceDepartment.objects.filter(parent_open_department_id__in=parent_nodes,
                                                              deactivated_at=default_deactive_time).exclude(
                    open_department_id__in=parent_nodes)
                parent_nodes = [node.open_department_id for node in extra_queryset]
                data.extend(DepartmentSiri(extra_queryset, many=True).data)
            department_id_list = [node['open_department_id'] for node in data]
        user_ids = AceDepartmentAccount.objects.filter(open_department_id__in=department_id_list).values_list('account_id', flat=True)
        users = AccountSiri(AceAccount.objects.filter(id__in=user_ids), many=True).data
        return Response.success(data=users)

    @schema(getUserTaskSchema)
    @list_route(methods=['get'], url_path='task/gantt')
    def get_tasks(self, request):
        start_date, end_date, account_ids = get_data(self.filtered, 'start_date', 'end_date', 'account_ids')
        users = AccountSiri(AceAccount.objects.filter(id__in=account_ids), many=True).data
        gantt_time = {
            'from': int(time.mktime(datestrToDate(start_date).timetuple()) * 1000),
            'to': int(time.mktime((datestrToDate(end_date) + datetime.timedelta(1)).timetuple()) * 1000 - 1)
        }
        base_query = Q(target_end__gte=start_date, target_end__lte=end_date)
        total_tasks = []
        rows = []
        row_id = 1
        with catch_error():
            for user in users:
                if user.get('jira_user'):
                    issues = JiraIssue.objects.filter(base_query, assignee=user['jira_user'])
                    dates = []
                    for issue in issues:
                        date = issue.target_start
                        while date <= issue.target_end:
                            dates.append(date)
                            date = date + datetime.timedelta(1)
                    dates = sorted(list(set(dates)))
                    tasks = []
                    for index, date in enumerate(dates):
                        if not tasks or (date - dates[index - 1]).days > 1:
                            tasks.append({'id': uuid.uuid4().hex,
                                          'assignee': user.get('name'),
                                          'key': f'http://jira.jiliguala.com/browse/{issues.first().key}?jql="Target end" >= {start_date} AND "Target end" <= {end_date} and assignee = {user.get("jira_user")}',
                                          'row_id': str(row_id),
                                          'time': {
                                              'start': time.mktime(date.timetuple()) * 1000,
                                              'end': time.mktime((date + datetime.timedelta(1)).timetuple()) * 1000 - 1
                                          }})
                        elif (date - dates[index - 1]).days == 1:
                            tasks[-1]['time']['end'] = time.mktime(
                                (date + datetime.timedelta(1)).timetuple()) * 1000 - 1
                    row_id += 1
                    rows.append({'assignee': user.get('name')})
                    total_tasks.extend(tasks)
        return Response.success(data={'items': total_tasks, 'rows': rows, 'time': gantt_time})


class AceChatViewSet(BaseViewSet):
    queryset = AceChat.objects.filter()
    serializer_class = AceChatSiri

    @schema(getChatScheme)
    def list(self, request, *args, **kwargs):
        name = self.filtered.get('name') or ''
        queryset = AceChat.objects.filter(name__contains=name)
        data = AceChatSiri(queryset, many=True).data
        return Response.success(data=data)


class AceGitlabProjectViewSet(BaseViewSet):
    queryset = AceGitlabProject.objects.filter()
    serializer_class = AceGitlabProjectSiri

    @schema(getGitlabProjectScheme)
    def list(self, request, *args, **kwargs):
        queryset = AceGitlabProject.objects.filter()
        data = AceGitlabProjectSiri(queryset, many=True).data
        total = len(queryset)
        return Response.success(data={'data': data, 'total': total})


class AceGitlabProjectChatViewSet(BaseViewSet):
    queryset = AceGitlabProjectChat.objects.filter()
    serializer_class = AceGitlabProjectChatSiri

    @schema(getGitlabProjectChatScheme)
    def list(self, request, *args, **kwargs):
        project = self.filtered.get('project') or ''
        offset = int(request.query_params.get('offset'))
        limit = int(request.query_params.get('limit'))
        queryset = AceGitlabProjectChat.objects.filter(project__contains=project, is_active=True)
        data = AceGitlabProjectChatSiri(queryset[offset: offset + limit], many=True).data
        total = len(queryset)
        return Response.success(data={'data': data, 'total': total})

    @schema(AceGitlabProjectChatSchema)
    def create(self, request, *args, **kwargs):
        project, source_branch, target_branch, chat_id = get_data(self.filtered, 'project', 'source_branch', 'target_branch', 'chat_id')
        AceGitlabProjectChat.objects.create(project=project, source_branch=source_branch, target_branch=target_branch, chat_id=chat_id, is_active=True)
        return Response.success()

    @list_route(methods=['patch', 'delete'], url_path='(?P<rid>[^/]+)')
    def edit_gitlab_chat_config(self, request, rid=None):
        """编辑PR合并群聊配置"""
        if request.method.lower() == 'patch':
            project, source_branch, target_branch, chat_id = request.data.get('project'), \
                                                             request.data.get('source_branch'), \
                                                             request.data.get('target_branch'), \
                                                             request.data.get('chat_id')
            try:
                AceGitlabProjectChat.objects.filter(id=rid).update(source_branch=source_branch, target_branch=target_branch, chat_id=chat_id)
            except Exception as e:
                return Response.server_error(message=str(e))
            return Response.success()
        else:
            AceGitlabProjectChat.objects.filter(id=rid).delete()
            return Response.success()

    # def destroy(self, request, *args, **kwargs):
    #     """删除群聊配置"""
    #     id = kwargs.get('pk')
    #     AceGitlabProjectChat.objects.filter(id=id).delete()
    #     return Response.success()


class AceGitlabProjectPRViewSet(BaseViewSet):
    """PR合并自动同步jira状态"""
    queryset = AceGitlabProjectChat.objects.filter(is_jira_active__isnull=False)
    serializer_class = AceGitlabProjectPRSiri

    @schema(getGitlabProjectChatScheme)
    def list(self, request, *args, **kwargs):
        project = self.filtered.get('project') or ''
        offset = int(request.query_params.get('offset'))
        limit = int(request.query_params.get('limit'))
        queryset = AceGitlabProjectChat.objects.filter(project__contains=project, is_jira_active__isnull=False)
        data = AceGitlabProjectPRSiri(queryset[offset: offset + limit], many=True).data
        total = len(queryset)
        return Response.success(data={'data': data, 'total': total})

    @schema(AceGitlabProjectPRSchema)
    def create(self, request, *args, **kwargs):
        project, is_jira_active = get_data(self.filtered, 'project', 'is_jira_active')
        AceGitlabProjectChat.objects.create(project=project, is_jira_active=is_jira_active)
        return Response.success()

    @list_route(methods=['patch', 'delete'], url_path='(?P<rid>[^/]+)')
    def edit_gitlab_pr_config(self, request, rid=None):
        """编辑PR合并配置"""
        if request.method.lower() == "patch":
            project, is_jira_active = request.data.get('project'), request.data.get('is_jira_active')
            try:
                AceGitlabProjectChat.objects.filter(id=rid).update(project=project, is_jira_active=is_jira_active)
            except Exception as e:
                return Response.server_error(message=str(e))
        else:
            AceGitlabProjectChat.objects.filter(id=rid).delete()
        return Response.success()


class AceApprovalConfigViewSet(BaseViewSet):
    """ 审批流配置 """
    @schema(AceApprovalConfigChatScheme)
    def list(self, request, *args, **kwargs):
        """ 获取审批流配置列表 """
        offset, limit, project = get_data(self.filtered, 'offset', 'limit', 'project')
        query = Q(is_active=True)
        if project:
            query = query & Q(project__icontains=project)
        queryset = AceJiraProjectChat.objects.filter(query).order_by('-created_at')
        total = len(queryset)
        serializers = ApprovalConfigSerializer(queryset[offset:offset + limit], many=True)
        return Response.success(data={'data': serializers.data, 'total': total})

    @schema(AceApprovalConfigChatScheme)
    def create(self, request, *args, **kwargs):
        project, chat_id = get_data(self.filtered, 'project', 'chat_id')
        AceJiraProjectChat.objects.create(project=project, chat_id=chat_id, is_active=True)
        return Response.success()

    @list_route(methods=['patch', 'delete'], url_path='(?P<rid>[^/]+)')
    @schema(AceApprovalConfigChatScheme)
    def edit_approval_config(self, request, rid=None):
        """ 编辑审批流通知配置 """
        if request.method.lower() == "patch":
            project, chat_id = get_data(self.filtered, 'project', 'chat_id')
            try:
                AceJiraProjectChat.objects.filter(id=rid).update(project=project, chat_id=chat_id, is_active=True)
            except Exception as e:
                return Response.server_error(message=str(e))
        else:
            AceJiraProjectChat.objects.filter(id=rid).delete()
        return Response.success()
