# -*- coding: utf-8 -*-
# @Time    : 2020/11/11 9:35 上午
# @Author  : zoey
# @File    : jira.py
# @Software: PyCharm
import datetime
import itertools
import time
from dateutil import parser
from bson.objectid import ObjectId
from zero.api.decorators import login_or_permission_required
from django.db.models import Q, Count, Sum
from itertools import groupby
from operator import itemgetter
from zero.api import BaseViewSet
from zero.api.baseSiri import OffsetLimitSiri
from zero.utils.format import get_data, second_2_days, get_month_start_end, get_special_month_start_end, mode_number, get_date_any
from zero.api.decorators import schema
from rest_framework.decorators import list_route
import zero.utils.superResponse as Response
from zero.jira.commands import JiraIssueType
from zero.jira.common import cal_sprint_story_status, get_month_report_response, get_month_bug_time_by_project, get_month_report_by_department, get_month_report_by_project, cal_sprint_task_status_overview, judge_sprint_exception
from zero.jira.models import JiraProject, JiraFixVersions, JiraIssue, JiraSprint, JiraBusinessCycle, SprintEstimate, \
    DepartmentEstimate
from zero.jira.siris import (JiraEpicSerializer, JiraProjectSerializer, JiraSprintSerializer, GetBugStatus,
                             GetMonthReport,
                             BaseParaSerializer, GetVersionsSerializer, JiraVersionTasksSerializer,
                             JiraBusinessCycleSiri, SprintEstimateSiri, JiraEpicSiri,
                             DepartmentEstimateSiri, DepartmentEsSiri,
                             PlatformBug, SprintBugPoint, SprintBugFixTime, SprintBugCloseTime, BugDetails)
from zero.jira.tasks import sync_jira_issue, calc_sprint_estimate_report


class JiraViewSet(BaseViewSet):
    queryset = JiraIssue.objects.all()
    serializer_class = OffsetLimitSiri

    @login_or_permission_required(['pm.edit'])
    @list_route(methods=['post'], url_path='sync_jira_data')
    def sync_jira_data(self, request):
        sync_jira_issue.apply_async(countdown=1, kwargs={'days': 60})
        return Response.success(message='正在同步数据，请稍等三分钟查看')

    @schema()
    @list_route(methods=['get'], url_path='projects')
    def get_projects(self, request):
        # 获取所有项目信息
        projects = JiraProject.objects.all().order_by('name')
        seri = JiraProjectSerializer(projects, many=True).data
        for proj in seri:
            proj['sprints'] = JiraSprintSerializer(proj['sprints'], many=True).data
            if request.query_params.get('closed'):
                proj['sprints'] = [x for x in proj['sprints'] if x['closed'] == 1]
        return Response.success({'datas': seri})

    @schema(BaseParaSerializer)
    @list_route(methods=['get'], url_path='sprints')
    def get_sprints(self, request):
        # 获取指定项目下的所有迭代信息
        query = Q(proj_id=self.filtered.get('proj_id'))
        if self.filtered.get('closed'):
            query = query & Q(closed=1)
        sprints = JiraSprint.objects.filter(query).order_by('-start_date')
        seri = JiraSprintSerializer(sprints, many=True)
        return Response.success({'datas': seri.data})

    @list_route(methods=['get'], url_path='stories')
    def get_stories(self, request):
        query = Q(type=JiraIssueType.STORY.chinese)
        if request.query_params.get('sprint_id'):
            query &= Q(sprint_id__contains=f"'{request.query_params.get('sprint_id')}'")
        stories = JiraEpicSiri(JiraIssue.objects.filter(query).order_by('-created'), many=True).data
        return Response.success(data=stories)

    @list_route(methods=['get'], url_path='sprints/latest')
    def get_latest_proj_sprint(self, request):
        # 获取最近一个迭代
        if request.query_params.get('closed'):
            sprint = JiraSprint.objects.filter(closed=1).order_by('start_date').reverse().first()
        else:
            sprint = JiraSprint.objects.filter().order_by('start_date').reverse().first()
        seri = JiraSprintSerializer(sprint)
        return Response.success(seri.data)

    @list_route(methods=['get'], url_path='sprint/specific')
    def get_sprint_JLGL(self, request):
        """返回固定的sprintId,效能数据专用"""
        sprint = {"id": "191", "proj_id": "10002"}
        return Response.success(sprint)

    @list_route(methods=['get'], url_path='epics')
    @schema(OffsetLimitSiri)
    def get_epic_list(self, request):
        # 获取版本列表
        offset, limit = get_data(self.filtered, 'offset', 'limit')
        search = request.query_params.get('search')
        query = Q(summary__contains=search, type='Epic')
        epics = request.query_params.getlist('epics')
        if epics:
            query |= Q(key__in=epics)
        data = JiraIssue.objects.filter(query).order_by('-created')[offset: offset + limit]
        data = JiraEpicSerializer(data, many=True).data
        return Response.success(data=data)

    @schema(GetVersionsSerializer)
    @list_route(methods=['get'], url_path='version/details')
    def get_versions(self, request):
        """获取指定迭代下的版本工作量报告"""
        versions = JiraFixVersions.objects.filter(sprint_id=self.filtered.get('sprint_id'))
        version_data = []
        for version in versions:
            if self.filtered.get('type') == 'Bug' and ('QA' in version.name.upper() or 'UI' in version.name.upper()):
                continue
            baseQuery = Q(bugOwner__isnull=False) & Q(fix_version__contains=f"'{version.id}'") & Q(
                resolution__in=['完成', 'Unresolved'])
            tasks = JiraIssue.objects.filter(baseQuery)
            datas = JiraVersionTasksSerializer(tasks, many=True).data
            datas.sort(key=itemgetter('bugOwner'))
            # 按人对task分组
            datas_group = groupby(datas, itemgetter('bugOwner'))
            if self.filtered.get('type') == 'Bug':
                tasks = JiraIssue.objects.filter(baseQuery)
                datas = JiraVersionTasksSerializer(tasks, many=True).data
                datas.sort(key=itemgetter('bugOwner'))
                details = [
                    {'bugOwner': key,
                     'tasks': [task for task in list(tasks) if task['type'] == JiraIssueType.BUG.chinese]}
                    for key, tasks in datas_group]
            elif self.filtered.get('type') == 'noBug':
                details = [
                    {'bugOwner': key,
                     'tasks': [task for task in list(tasks) if task['type'] != JiraIssueType.BUG.chinese]}
                    for key, tasks in datas_group]
                details = list(filter(lambda x: x['tasks'], details))
            else:
                details = [{'bugOwner': key, 'tasks': list(tasks)} for key, tasks in datas_group]
            details = list(map(lambda x: dict(x, **{
                'online_point': sum([y['point'] for y in x['tasks'] if y['bug_level'] == '线上']) or 0,
                'offline_point': sum([y['point'] for y in x['tasks'] if y['bug_level'] == '线下']) or 0,
                'day':
                    second_2_days(
                        JiraIssue.objects.filter(bugOwner=x['bugOwner'], fix_version__contains=f"'{version.id}'",
                                                 resolution__in=['完成', 'Unresolved']).aggregate(
                            total_estimate=Sum('original_time_estimate'))['total_estimate'])}), details))
            version_data.append({'version': version.name, 'details': details})
        return Response.success({'datas': version_data})

    @schema(GetBugStatus)
    @list_route(methods=['get'], url_path='bug/summary')
    def get_bug_summary(self, request):
        """获取bug数，开发人天， 人天bug数"""
        proj_id, start_date, end_date = get_data(self.filtered, 'proj_id', 'start_date', 'end_date')
        # 查询子任务的时间条件
        task_queryset = Q(target_start__gte=start_date) & Q(target_start__lte=end_date) & Q(
            resolution__in=['完成', 'Unresolved'])
        # 查询bug数的时间条件
        bug_queryset = Q(created__gte=start_date) & Q(created__lte=end_date)
        if proj_id:
            task_queryset = task_queryset & Q(proj_id=proj_id)
            bug_queryset = bug_queryset & Q(proj_id=proj_id)
        bug_count = JiraIssue.objects.filter(bug_queryset, type=JiraIssueType.BUG.chinese).count()
        total_estimate = JiraIssue.objects.filter(task_queryset, type=JiraIssueType.SUBTASK.chinese,
                                                  original_time_estimate__isnull=False).aggregate(
            total_estimate=Sum('original_time_estimate'))
        # 把秒转成天数，8小时是一天
        estimate_days = second_2_days(total_estimate['total_estimate'])
        return Response.success(data=[{'name': '缺陷数量', 'data': bug_count},
                                      {'name': '总工作人天', 'data': estimate_days},
                                      {'name': '人天bug率',
                                       'data': mode_number(bug_count, estimate_days, 1)}])

    @schema(GetMonthReport)
    @list_route(methods=['get'], url_path='month/report')
    def get_month_report(self, request):
        """获取指定月份报告"""
        month = self.filtered['month'].split('-')
        start, end = get_month_start_end(int(month[0]), int(month[1]))
        # 统计所有的bug情况
        response_data = get_month_report_response(start=start, end=end)

        return Response.success(response_data)

    @schema(GetMonthReport)
    @list_route(methods=['get'], url_path='department/month/report')
    def get_department_month_report(self, request):
        """获取部门月份报告"""
        month = self.filtered['month'].split('-')
        start, end = get_month_start_end(int(month[0]), int(month[1]))
        response_data = get_month_report_by_department(start, end)
        return Response.success(response_data)

    def get_week_report(self):
        pass

    @schema(GetMonthReport)
    @list_route(methods=['get'], url_path='month/quality/trend')
    def get_month_quality_trend(self, request):
        # 默认查看最近选中月份最近六个月
        now = datetime.datetime.now()
        month = self.filtered['month'].split('-')
        year1, month1 = int(month[0]), int(month[1])
        year2, month2 = now.year, now.month
        num = (year2 - year1) * 12 + (month2 - month1)
        n = request.query_params.get('n', 6)
        datas = []
        for i in range(num, num+n):
            start_end = get_special_month_start_end(i)
            report_data = get_month_report_by_project(start=start_end.get('start'), end=start_end.get('end'))
            datas.insert(0, {start_end.get('xserie'): report_data})

        return Response.success(data=datas)

    @schema()
    @list_route(methods=['get'], url_path='demand/response/cycle')
    def get_project_cycle(self, request):
        """项目度量"""
        try:
            dt = request.query_params.get('query_date')
            project_cycle = JiraBusinessCycleSiri(JiraBusinessCycle.objects.filter(end_date=dt), many=True).data
            return Response.success(project_cycle)
        except Exception as e:
            return Response.server_error(message=e)

    @schema()
    @list_route(methods=['get'], url_path='demand/business/sprint/cycle')
    def get_business_sprint_cycle(self, request):
        """每条产线迭代维度近半年需求响应周期"""
        proj_id = request.query_params.get('proj_id')
        business_cycle = []
        # 半年内的sprint
        query_sprint = Q(start_date__gte=get_date_any(n=-180), start_date__lte=get_date_any()) & ~Q(
            complete_date=None)
        query_story = Q(created__gte=get_date_any(n=-180), created__lte=get_date_any()) & ~Q(sprint_id='[]')
        sprint_arr = JiraSprintSerializer(JiraSprint.objects.filter(query_sprint, proj_id=proj_id).order_by('start_date'),
                                          many=True).data
        if sprint_arr:
            for spr in sprint_arr:
                dict = {}
                story_arr = JiraEpicSiri(JiraIssue.objects.filter(query_story, sprint_id__contains=f"\'{spr['id']}\']",
                                                                  type=JiraIssueType.STORY.chinese), many=True).data
                if story_arr:
                    dict.update({"sprint_name": spr['name']})
                    complete_dt = spr['complete_date']
                    start_dt = spr['start_date']
                    if complete_dt == start_dt:
                        dt_cycle = 1
                    else:
                        spr_cycle = parser.parse(complete_dt) - parser.parse(start_dt)
                        dt_cycle = str(spr_cycle).split(" ")[0]
                    dict.update({"develop_cycle": float(dt_cycle)})
                    story_num = 0
                    story_sum = 0
                    for story in story_arr:
                        create_date = story['created'].split(" ")[0]
                        story_num = story_num + 1
                        if complete_dt == create_date:
                            date_cycle = 1
                        else:
                            cycle = parser.parse(complete_dt) - parser.parse(create_date)
                            date_cycle = str(cycle).split(" ")[0]
                        story_sum = story_sum + (int(date_cycle))
                    if story_num != 0:
                        delivery_avg = round(story_sum / story_num, 2)
                        dict.update({"delivery_cycle": delivery_avg})
                    business_cycle.append(dict)
        return Response.success(business_cycle)

    @schema(GetMonthReport)
    @list_route(methods=['get'], url_path='month/bug_time/trend')
    def get_month_bug_time_trend(self, request):
        # 默认查最近选中月份六个月
        now = datetime.datetime.now()
        month = self.filtered['month'].split('-')
        year1, month1 = int(month[0]), int(month[1])
        year2, month2 = now.year, now.month
        num = (year2 - year1) * 12 + (month2 - month1)
        n = request.query_params.get('n', 6)
        datas = []
        for i in range(num, num + n).__reversed__():
            start_end = get_special_month_start_end(i)
            report_data = get_month_bug_time_by_project(start=start_end.get('start'), end=start_end.get('end'))
            datas.append({start_end.get('xserie'): report_data})
        return Response.success(data=datas)

    @list_route(methods=['get'], url_path='sprint/bug_time/trend')
    def get_sprint_bug_time_trend(self, request):
        '''获取最近半年每个迭代的bug平均解决、关闭时长'''
        date = get_date_any(-180)
        proj_id = request.query_params.get('proj_id')
        res_datas = []
        sprints = JiraSprint.objects.values_list('id', 'name').filter(complete_date__gte=date,
                                                                      proj_id=proj_id,
                                                                      start_date__isnull=False).order_by('start_date')
        base_qurey = Q(resolution__in=['完成', 'Unresolved'], type=JiraIssueType.BUG.chinese)
        for sprint in sprints:
            total_issue_count = len(
                JiraIssue.objects.filter(type='Bug', resolution__in=['完成', 'Unresolved'], sprint_id__contains=f"\'{sprint[0]}\']"))
            if total_issue_count:
                offline_bug_fixtime_list = JiraIssue.objects.filter(base_qurey, proj_id=proj_id, bug_level='线下',
                                                                    fix_time__isnull=False,
                                                                    sprint_id__contains=f"\'{sprint[0]}\']").values_list('fix_time', flat=True)
                online_bug_fixtime_list = JiraIssue.objects.filter(base_qurey, proj_id=proj_id, bug_level='线上',
                                                                   fix_time__isnull=False,
                                                                   sprint_id__contains=f"\'{sprint[0]}\']").values_list('fix_time',
                                                                                                       flat=True)
                offline_bug_closetime_list = JiraIssue.objects.filter(base_qurey, proj_id=proj_id, bug_level='线下',
                                                                      close_time__isnull=False,
                                                                      sprint_id__contains=f"\'{sprint[0]}\']").values_list('close_time',
                                                                                                            flat=True)
                online_bug_closetime_list = JiraIssue.objects.filter(base_qurey, proj_id=proj_id, bug_level='线上',
                                                                     close_time__isnull=False,
                                                                     sprint_id__contains=f"\'{sprint[0]}\']").values_list('close_time',
                                                                                                           flat=True)
                res_datas.append({'sprint_name': sprint[1],
                                  'offline_avg_fix_time': mode_number(mode_number(sum(offline_bug_fixtime_list), len(offline_bug_fixtime_list), 2), 3600, 2),
                                  'offline_avg_close_time': mode_number(mode_number(sum(offline_bug_closetime_list), len(offline_bug_closetime_list), 2), 3600, 2),
                                  'online_avg_fix_time': mode_number(mode_number(sum(online_bug_fixtime_list), len(online_bug_fixtime_list), 2), 3600, 2),
                                  'online_avg_close_time': mode_number(mode_number(sum(online_bug_closetime_list), len(online_bug_closetime_list), 2), 3600, 2)})
        return Response.success(data=res_datas)

    @list_route(methods=['get'], url_path='sprint/story/throughput')
    def get_story_throughput_by_sprint(self, request):
        '''获取每个迭代的需求交付吞吐率'''
        date = get_date_any(-180)
        sprints = JiraSprint.objects.values_list('id', 'name').filter(complete_date__gte=date, proj_id=request.query_params.get('proj_id'),
                                                                      start_date__isnull=False).order_by('start_date')
        res_datas = []
        for sprint in sprints:
            # done_story_count = len(JiraIssue.objects.filter(type='Story', resolution='完成', sprint_id__contains=f"\'{sprint[0]}\']"))
            total_story_count = len(JiraIssue.objects.filter(type='Story', resolution__in=['完成', 'Unresolved'], sprint_id__contains=f"\'{sprint[0]}\']"))
            if total_story_count:
                res_datas.append({'sprint_name': sprint[1],
                                  # 'done_story_count': done_story_count,
                                  'total_story_count': total_story_count,
                                  # 'throughput': mode_number(done_story_count, total_story_count, 2)
                                  })
        return Response.success(data=res_datas)

    @schema(GetVersionsSerializer)
    @list_route(methods=['get'], url_path='sprint/estimate/report')
    def get_estimate_report_by_sprint(self, request):
        '''获取指定迭代的各端工时情况'''
        report = SprintEstimateSiri(SprintEstimate.objects(sprint_id=self.filtered.get('sprint_id')), many=True).data
        report.sort(key=lambda x: x['terminal_id'])
        return Response.success(data=report)

    @login_or_permission_required('pm.edit')
    @schema()
    @list_route(methods=['patch'], url_path='sprint/total/estimate/(?P<sprId>[^/]+)')
    def edit_sprint_total_estimate(self, request, sprId=None):
        '''编辑迭代总工时报告'''
        try:
            sprint_id = sprId
            content = request.data
            SprintEstimate.base_upsert({'sprint_id': sprint_id, 'terminal': "total"}, **content)
        except Exception as e:
            return Response.server_error(message=e.args[0])
        return Response.success()

    @login_or_permission_required('pm.edit')
    @schema(SprintEstimateSiri)
    @list_route(methods=['patch'], url_path='sprint/estimate/report/(?P<rid>[^/]+)')
    def edit_sprint_estimate_report(self, request, rid=None):
        '''编辑迭代工时报告'''
        try:
            SprintEstimate.base_upsert({'id': ObjectId(rid)}, **self.filtered)
        except Exception as e:
            return Response.server_error(message=e.args[0])
        return Response.success()

    @list_route(methods=['get'], url_path='sprint/warning')
    def get_sprint_warning(self, request):
        sprint_id = request.query_params.get('sprint_id')
        try:
            data = judge_sprint_exception(sprint_id)
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        return Response.success(data=data)

    @list_route(methods=['get'], url_path='sprint/story/test/status')
    def get_sprint_story_test_status(self, request):
        sprint_id = request.query_params.get('sprint_id')
        data = cal_sprint_story_status(sprint_id=sprint_id, type='qa')
        return Response.success(data=data)

    @list_route(methods=['get'], url_path='sprint/story/test/planning')
    def get_sprint_story_test_planning(self, request):
        sprint_id = request.query_params.get('sprint_id')
        data = cal_sprint_story_status(sprint_id=sprint_id, type='dev')
        return Response.success(data=data)

    @list_route(methods=['get'], url_path='sprint/story/overview')
    def get_sprint_story_overview(self, request):
        sprints = JiraSprint.objects.filter(started=1, closed=0).exclude(proj_key='QA').order_by('name').values('id', 'start_date', 'end_date', 'name', 'proj_id')
        row_id = 1
        rows = []
        items = []
        for sprint in sprints:
            master = JiraProject.objects.get(id=sprint['proj_id']).lead
            tasks = cal_sprint_task_status_overview(sprint, row_id=row_id)
            rows.append({
                'sprint_name': sprint['name'],
                'master': master,
                'sprint_id': sprint['id'],
                'proj_id': sprint['proj_id'],
            })
            items.extend(tasks)
            row_id += 1
        return Response.success(data={'rows': rows, 'items': items})


    @schema(GetVersionsSerializer)
    @list_route(methods=['get'], url_path='sprint/story/resource/rank')
    def get_story_rank(self, request):
        """占用研发测试资源前十的需求"""
        sprint_id = request.query_params.get('sprint_id')
        stories = JiraIssue.objects.filter(type='Story', sprint_id__contains=f"'{sprint_id}'").values(
            'key', 'summary')
        base_query = Q(resolution__in=['完成', 'Unresolved']) & Q(type='Sub-task')
        story_list = []
        for story in stories:
            story_dict = {}
            tasks = JiraIssue.objects.filter(base_query, parent_key=story['key'])
            if tasks:
                estimate = sum([task.original_time_estimate for task in tasks])
                story_dict.update({"name": story['summary'], "estimate": round(estimate / 28800, 2)})
                story_list.append(story_dict)
        story_list.sort(key=lambda x: x['estimate'], reverse=True)
        if len(story_list) > 10:
            del story_list[10:]
        story_list.sort(key=lambda x: x['estimate'])
        return Response.success(story_list)

    @schema(GetMonthReport)
    @list_route(methods=['get'], url_path='month/resource/report')
    def get_month_resource_report(self, request):
        """获取月度资源报告"""
        res_datas = DepartmentEstimateSiri(DepartmentEstimate.objects(month=self.filtered.get('month')), many=True).data
        res_datas.sort(key=lambda x: x['depart_name'])
        return Response.success(res_datas)

    @login_or_permission_required('pm.edit')
    @schema(DepartmentEsSiri)
    @list_route(methods=['patch'], url_path='month/resource/report/(?P<rid>[^/]+)')
    def edit_month_resource_report(self, request, rid=None):
        '''编辑月度资源报告'''
        try:
            DepartmentEstimate.base_upsert({'id': ObjectId(rid)}, **self.filtered)
        except Exception as e:
            return Response.server_error(message=e.args[0])
        return Response.success()

    @schema(GetVersionsSerializer)
    @list_route(methods=['get'], url_path='develop/bug/statistical')
    def get_develop_bug_statistical(self, request):
        """研发测试投入及bug数"""
        sprint_id = request.query_params.get('sprint_id')
        base_query = Q(sprint_id__contains=f"[\'{sprint_id}\'") & Q(type=JiraIssueType.BUG.chinese) & Q(
            resolution__in=['完成', 'Unresolved', '延期处理'])
        platform = JiraIssue.objects.filter(base_query).values('platform').annotate(count=Count('key')).order_by(
            'platform')
        platforms = PlatformBug(platform, many=True).data
        H5_index = 0
        # 用于判断是否同时存在H5与web的bug
        H5_exist = False
        for index in range(len(platforms)):
            if platforms[index]['platform'] == "H5":
                H5_index = index
                H5_exist = True
                break
        for i in range(len(platforms)):
            if platforms[i]['platform'] == "Web":
                if not H5_exist:
                    platforms[i]['platform'] = "H5"
                    break
                else:
                    platforms[H5_index]['count'] = platforms[H5_index]['count'] + platforms[i]['count']
                    platforms.pop(i)
                    break
        reports = SprintEstimateSiri(SprintEstimate.objects(sprint_id=sprint_id), many=True).data
        reports.sort(key=lambda x: x['terminal_id'])
        times = [{'terminal': report['terminal'],
                  'days': report['business_story_days'] + report['tech_story_days'] + report['change_story_days']}
                 for report in reports]
        resp = []
        key = []
        for time in times:
            plat_data = {}
            if time['days']:
                for platform in platforms:
                    if time['terminal'] == 'Bigdata' and platform['platform'] == "数仓":
                        plat_data.update({'platform': 'Bigdata', 'people_count': round(time['days'], 3),
                                          'bugs': platform['count']})
                        resp.append(plat_data)
                        key.append(time['terminal'])
                        continue
                    elif time['terminal'].lower() == platform['platform'].lower():
                        plat_data.update({'platform': platform['platform'], 'people_count': round(time['days'], 3),
                                          'bugs': platform['count']})
                        resp.append(plat_data)
                        key.append(time['terminal'])
                        continue
        for t in times:
            if t['days'] and t['terminal'] not in key:
                resp.append({'platform': t['terminal'], 'people_count': round(t['days'], 3), 'bugs': 0})
        return Response.success(resp)

    @schema()
    @list_route(methods=['get'], url_path='sprint/subtask')
    def get_sprint_version_sub_task(self, request):
        """获取组别的子任务"""
        resp = {}
        sprint_id = request.query_params.get('sprint_id')
        terminal = request.query_params.get('terminal')
        if terminal == "Server":
            terminal = "BE"
        elif terminal == "H5":
            terminal = "FE"
        # 全部story
        stories = JiraIssue.objects.filter(type='Story', sprint_id__contains=f"'{sprint_id}'").values_list(
            'key', flat=True)
        # 当前迭代全部子任务
        task_query = Q(type='Sub-task') & Q(parent_key__in=stories) & ~Q(resolution='不做了')
        sub_tasks = JiraIssue.objects.filter(task_query).values_list('fix_version', flat=True)
        # 当前迭代涉及到的版本
        version_ids = list(set(["".join(filter(str.isdigit, sub_task)) for sub_task in sub_tasks]))
        versions = JiraFixVersions.objects.filter(id__in=version_ids).values('id', 'name')
        # 过滤出当前版本
        name = set([ver.get('name') for ver in versions if terminal in ver.get('name')])
        ver_id = [ver.get('id') for ver in versions if terminal in ver.get('name')]
        # 拼接jql需要的数据
        ver_name = "(" + ",".join(name) + ")"
        sub_task = JiraIssue.objects.filter(sprint_id__contains=f"\'{sprint_id}\']",
                                            fix_version__contains=f"'{ver_id[0]}'").values('key')
        resp.update({'key': sub_task[0]['key'], 'version': ver_name})
        return Response.success(resp)

    @schema()
    @list_route(methods=['get'], url_path='sprint/subTask/progress')
    def get_sub_task_progress(self, request):
        response = {}
        rows = []
        items = []
        num = 0
        numb = 0
        date = datetime.datetime.now()
        now_dt = datetime.datetime(date.year, date.month, date.day)
        sprint_id = request.query_params.get('sprint_id')
        sprint = JiraSprint.objects.filter(id=sprint_id, start_date__isnull=False, end_date__isnull=False).values(
            'start_date', 'end_date')
        if not sprint:
            return Response.success()
        start = time.mktime(sprint[0]['start_date'].timetuple()) * 1000
        end = time.mktime(sprint[0]['end_date'].timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000 - 1
        stories = JiraIssue.objects.filter(type='Story', sprint_id__contains=f"'{sprint_id}'").values('key', 'summary', 'assignee')
        for story in stories:
            num = num + 1
            story_id = num
            rows.append({
                'id': str(story_id), "story": story['summary'], "assigen": story['assignee'], "expanded": True
            })
            task_query = Q(assignee__isnull=False) & Q(type='Sub-task') & ~Q(resolution='不做了') & Q(
                target_start__isnull=False) & Q(target_end__isnull=False)
            sub_tasks = JiraIssue.objects.filter(task_query, parent_key=story['key']).values()
            for task in sub_tasks:
                num = num + 1
                if task.get('target_start') == now_dt and task.get('target_end') == now_dt:
                    rows.append({
                        'id': str(num), "story": task['summary'], "assigen": task['assignee'], "parentId": str(story_id)
                    })
                    numb = numb + 1
                    items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                        'start': time.mktime(now_dt.timetuple()) * 1000 + 1,
                        'end': time.mktime(now_dt.timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000
                    }, 'status': 'today'})
                elif task.get('target_end') == now_dt:
                    rows.append({
                        'id': str(num), "story": task['summary'], "assigen": task['assignee'], "parentId": str(story_id)
                    })
                    numb = numb + 1
                    items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                        'start': time.mktime(now_dt.timetuple()) * 1000 + 1,
                        'end': time.mktime(now_dt.timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000
                    }, 'status': 'today'})
                    numb = numb + 1
                    items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                        'start': time.mktime(task.get('target_start').timetuple()) * 1000 + 1,
                        'end': time.mktime(task.get('target_end').timetuple()) * 1000
                    }, 'status': 'normal'})
                elif task.get('target_start') == now_dt:
                    rows.append({
                        'id': str(num), "story": task['summary'], "assigen": task['assignee'], "parentId": str(story_id)
                    })
                    numb = numb + 1
                    items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                        'start': time.mktime(now_dt.timetuple()) * 1000 + 1,
                        'end': time.mktime(now_dt.timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000
                    }, 'status': 'today'})
                    numb = numb + 1
                    items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                        'start': time.mktime(now_dt.timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000 + 1,
                        'end': time.mktime(task.get('target_end').timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000
                    }, 'status': 'inProgress'})
                elif task.get('target_start') > now_dt:
                    rows.append({
                        'id': str(num), "story": task['summary'], "assigen": task['assignee'], "parentId": str(story_id)
                    })
                    numb = numb + 1
                    items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                        'start': time.mktime(task.get('target_start').timetuple()) * 1000 + 1,
                        'end': time.mktime(task.get('target_end').timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000
                    }, 'status': 'inProgress'})
                elif task.get('target_end') < now_dt:
                    if task.get('status') == "Done" :
                        rows.append({
                            'id': str(num), "story": task['summary'], "assigen": task['assignee'],
                            "parentId": str(story_id)
                        })
                        numb = numb + 1
                        items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                            'start': time.mktime(task.get('target_start').timetuple()) * 1000 + 1,
                            'end': time.mktime(task.get('target_end').timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000
                        }, 'status': 'normal'})
                    elif task.get('target_start') == task.get('target_end'):
                        rows.append({
                            'id': str(num), "story": task['summary'], "assigen": task['assignee'],
                            "parentId": str(story_id)
                        })
                        numb = numb + 1
                        items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                            'start': time.mktime(task.get('target_start').timetuple()) * 1000 + 1,
                            'end': time.mktime(task.get('target_end').timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000
                        }, 'status': 'delay'})
                    else:
                        rows.append({
                            'id': str(num), "story": task['summary'], "assigen": task['assignee'], "parentId": str(story_id)
                        })
                        numb = numb + 1
                        items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                            'start': time.mktime(task.get('target_start').timetuple()) * 1000 + 1,
                            'end': time.mktime(task.get('target_end').timetuple()) * 1000
                        }, 'status': 'normal'})
                        numb = numb + 1
                        items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                            'start': time.mktime(task.get('target_end').timetuple()) * 1000 + 1,
                            'end': time.mktime(task.get('target_end').timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000
                        }, 'status': 'delay'})
                else:
                    rows.append({
                        'id': str(num), "story": task['summary'], "assigen": task['assignee'], "parentId": str(story_id)
                    })
                    numb = numb + 1
                    items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                        'start': time.mktime(task.get('target_start').timetuple()) * 1000 + 1,
                        'end': time.mktime(now_dt.timetuple()) * 1000
                    }, 'status': 'normal'})
                    numb = numb + 1
                    items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                        'start': time.mktime(now_dt.timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000 + 1,
                        'end': time.mktime(task.get('target_end').timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000
                    }, 'status': 'inProgress'})
                    numb = numb + 1
                    items.append({'id': str(numb), 'key': task['key'], 'rowId': str(num), 'time': {
                        'start': time.mktime(now_dt.timetuple()) * 1000 + 1,
                        'end': time.mktime(now_dt.timetuple()) * 1000 + 1 * 24 * 60 * 60 * 1000
                    }, 'status': 'today'})
        response.update({'rows': rows, 'items': items, 'start': start, 'end': end})
        return Response.success(response)

    @schema()
    @list_route(methods=['get'], url_path='sprint/bug/point')
    def get_sprint_bug_point(self, request):
        """Bug质量分"""
        repose = []
        sprint_id = request.query_params.get('sprint_id')
        bug_query = Q(platform__isnull=False) & Q(type='Bug') & Q(sub_bug_level__in=['S0', 'S1', 'S2', 'S3']) & Q(
            resolution__in=['完成', 'Unresolved'])
        bugs = SprintBugPoint(JiraIssue.objects.filter(bug_query, sprint_id__contains=f"[\'{sprint_id}\'").values(
            'platform', 'sub_bug_level').annotate(count=Count('key')).order_by('platform', 'sub_bug_level'),
                              many=True).data
        # 从SprintEstimate表获取对应版本用时
        reports = SprintEstimateSiri(SprintEstimate.objects(sprint_id=sprint_id), many=True).data
        reports.sort(key=lambda x: x['terminal_id'])
        # 去掉reports里terminal为total的记录
        if reports:
            reports.pop(-1)
        for report in reports:
            estimate = report['business_story_days'] + report['tech_story_days'] + report[
                'change_story_days']
            if report['terminal'] == "H5":
                point = sum([bug['point'] for bug in bugs if bug['platform'] == "H5" or bug['platform'] == "Web"]) or 0
                point_rate = mode_number(point, estimate, 2)
            elif report['terminal'] == "Bigdata":
                point = sum([bug['point'] for bug in bugs if bug['platform'] == "数仓"]) or 0
                point_rate = mode_number(point, estimate, 2)
            else:
                point = sum([bug['point'] for bug in bugs if bug['platform'].lower() == report['terminal'].lower()]) or 0
                point_rate = mode_number(point, estimate, 2)
            if point_rate:
                repose.append({'platform': report['terminal'], 'point_rate': point_rate})
        return Response.success(repose)

    @schema()
    @list_route(methods=['get'], url_path="sprint/bug/fix/duration")
    def get_bug_fix_duration(self, request):
        """bug修复时长"""
        repose = []
        sprint_id = request.query_params.get('sprint_id')
        type = request.query_params.get('type')
        base_query = Q(platform__isnull=False) & Q(type='Bug') & Q(sub_bug_level__in=['S0', 'S1', 'S2', 'S3']) & Q(
            sprint_id__contains=f"[\'{sprint_id}\'") & Q(resolution__in=['完成', 'Unresolved'])
        if type == "FixedToClosed":
            bugs = SprintBugFixTime(JiraIssue.objects.filter(base_query, fix_time__isnull=False,
                                                             close_time__isnull=False).values(
                'sub_bug_level', 'platform').annotate(count=Count('key'), duration=Sum('close_time')).order_by(
                'sub_bug_level', 'platform'), many=True).data
        elif type == "OpenToFixed":
            bugs = SprintBugFixTime(JiraIssue.objects.filter(base_query, fix_time__isnull=False).values(
                'sub_bug_level', 'platform').annotate(count=Count('key'), duration=Sum('fix_time')).order_by(
                'sub_bug_level', 'platform'), many=True).data
        else:
            bugs = SprintBugCloseTime(JiraIssue.objects.filter(base_query, close_time__isnull=False).values(
                'sub_bug_level', 'platform').annotate(count=Count('key'), fix_duration=Sum('fix_time'),
                                                      close_duration=Sum('close_time')).order_by(
                'sub_bug_level', 'platform'), many=True).data
        platform_set = set(bug['platform'] for bug in bugs)
        level_set = set(bug['sub_bug_level'] for bug in bugs)
        for level in level_set:
            res_dict = {'sub_bug_level': level}
            for platform in platform_set:
                if platform == "H5" or platform == "Web":
                    bugs_list = [bug for bug in bugs if bug['sub_bug_level'] == level]
                    bug_list = [y for y in bugs_list if y['platform'] == "H5" or y['platform'] == "Web"]
                    durations = sum([x['duration'] for x in bug_list])
                    counts = sum([x['count'] for x in bug_list])
                    duration = mode_number(mode_number(durations, counts), 3600) if bug_list else 0
                    res_dict.update({"H5": duration})
                elif platform == "数仓":
                    duration = sum(
                        [y['hours'] for y in bugs if y['sub_bug_level'] == level and y['platform'] == "数仓"]) or 0
                    res_dict.update({"Bigdata": duration})
                else:
                    duration = sum(
                        [y['hours'] for y in bugs if y['sub_bug_level'] == level and y['platform'] == platform]) or 0
                    res_dict.update({platform: duration})
            repose.append(res_dict)
        repose.sort(key=lambda X:X['sub_bug_level'])
        return Response.success(repose)

    @schema()
    @list_route(methods=['get'], url_path='sprint/bug/download')
    def download_bug_detail(self, request):
        """下载bug详情"""
        sprint_id = request.query_params.get('sprint_id')
        sprint_name = JiraSprint.objects.filter(id=sprint_id).values_list('name')[0][0]
        base_query = Q(platform__isnull=False) & Q(type='Bug') & Q(sub_bug_level__in=['S0', 'S1', 'S2', 'S3']) & Q(
            sprint_id__contains=f"[\'{sprint_id}\'") & Q(bugOwner__isnull=False) & Q(resolution__in=['完成', 'Unresolved'])
        bugs = BugDetails(JiraIssue.objects.filter(base_query).values().order_by('bugOwner', 'sub_bug_level'),
                          many=True).data
        for bug in bugs:
            bug.update({'sprint_name': sprint_name})
        return Response.success(bugs)

    @login_or_permission_required('pm.edit')
    @schema()
    @list_route(methods=['get'], url_path='sprint/report/refresh')
    def syn_sprint_report(self, request):
        """同步项目报告"""
        sprint_id = request.query_params.get('sprint_id')
        calc_sprint_estimate_report(spr_id=sprint_id)
        return Response.success()
