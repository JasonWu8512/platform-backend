# coding=utf-8
# @Time    : 2021/4/27 4:56 下午
# @Author  : jerry
# @File    : common.py
import json
import time

import chinese_calendar
from django.contrib.auth.models import User
from zero.jira.commands import DepartmentLeader
from zero.libs.redis import RedisClient
from zero.organization.commands import default_deactive_time
from zero.organization.models import AceDepartment, AceAccount, AceDepartmentAccount
from zero.organization.siri import AccountSiri, DevDepartmentSiri, DepartmentSiri
from zero.jira.siris import JiraBugCountGroup, JiraProjectTaskEstimate, JiraPeopleCountGroup, JiraDepartTaskEstimate, JiraBugCountDepart
from zero.jira.models import *
from zero.utils.contextLib import catch_error
from zero.utils.format import mode_number, second_2_days, merge_2_dict_list, dateToTimeStamp, get_three_month_start_end
from django.db.models import Q, Count, Sum
from zero.jira.commands import JiraStoryTestStatus, JiraIssueType
from collections import Counter
from itertools import groupby, chain
from operator import itemgetter
import datetime

task_resolution = ['完成', 'Unresolved']


def get_month_report_response(start, end):
    users = AccountSiri(AceAccount.objects.filter(user_role="QA"), many=True).data
    QA_users = [user.get('jira_user') for user in users if user.get('jira_user')]
    bug_query = Q(created__gte=start, created__lte=end, type=JiraIssueType.BUG.chinese,
                  resolution__in=['完成', 'Unresolved']) & ~Q(
        proj_key__in=['QA', 'DESIGND', 'WEBEDITOR', 'DEM', 'OPERATION']) & ~Q(bugOwner__in=QA_users)
    task_query = Q(created__gte=start, created__lte=end) & Q(
        type__in=[JiraIssueType.SUBTASK.chinese, JiraIssueType.TASK.chinese]) & Q(
        resolution__in=['完成', 'Unresolved']) & ~Q(proj_key__in=['QA', 'DESIGND', 'WEBEDITOR', 'DEM', 'OPERATION']) & ~Q(
        assignee__in=QA_users)
    total_bugs = JiraBugCountGroup(
        JiraIssue.objects.filter(bug_query).values(
            'bug_level', 'sub_bug_level').annotate(count=Count('key')).order_by('bug_level', 'sub_bug_level'),
        many=True).data
    # 统计所有的估时
    total_estimate = JiraProjectTaskEstimate(
        JiraIssue.objects.filter(task_query).aggregate(
            total_estimate=Sum('original_time_estimate'))).data
    # 统计人数
    try:
        total_people_count = len(JiraIssue.objects.filter(task_query).values('assignee').distinct())
    except Exception as e:
        raise e
    # 按项目统计bug情况
    proj_bugs = JiraIssue.objects.filter(bug_query).values(
        'bug_level', 'sub_bug_level', 'proj_id').annotate(count=Count('key')).order_by('proj_id', 'bug_level',
                                                                                       'sub_bug_level')
    # 按项目统计估时
    proj_estimates = JiraIssue.objects.filter(task_query).values('proj_id').annotate(
        total_estimate=Sum('original_time_estimate'))
    # 按项目统计人数
    people_count = JiraPeopleCountGroup(JiraIssue.objects.filter(task_query).values('proj_id').annotate(
        people_count=Count('assignee', distinct=True)).order_by('proj_id'), many=True).data

    proj_bugs = [{'proj_name': key, 'bugs': list(bug_groups)} for key, bug_groups in
                 groupby(JiraBugCountGroup(proj_bugs, many=True).data, itemgetter('proj_name'))]
    proj_bugs = list(map(lambda x: dict(x, **{'count': sum([y['count'] for y in x['bugs']]) or 0,
                                              'offline_count': sum(
                                                  [y['count'] for y in x['bugs'] if y['bug_level'] == '线下']) or 0,
                                              'online_count': sum(
                                                  [y['count'] for y in x['bugs'] if y['bug_level'] == '线上']) or 0,
                                              'point': sum(y['point'] for y in x['bugs']) or 0,
                                              'online_point': sum(
                                                  [y['point'] for y in x['bugs'] if y['bug_level'] == '线上']) or 0,
                                              'offline_point': sum(
                                                  [y['point'] for y in x['bugs'] if y['bug_level'] == '线下']) or 0,
                                              }), proj_bugs))
    # 每个项目的估时统计
    proj_estimates = JiraProjectTaskEstimate(proj_estimates, many=True).data
    # 合并项目的估时和bug、人数
    details = merge_2_dict_list(proj_bugs, proj_estimates, 'proj_name')
    bug_times = get_month_bug_time_by_project(start, end)
    details = merge_2_dict_list(details, bug_times, 'proj_name')
    details = merge_2_dict_list(details, people_count, 'proj_name')
    for index in range(len(details)):
        details[index]['offline_bug_rate'] = mode_number(details[index].get('offline_point'), details[index].get("day"),
                                                         2)
    details.sort(key=lambda x: x['proj_name'])
    response_data = {'summary': {**{'bugs': total_bugs, 'people_count': total_people_count},
                                 **{'count': sum([y['count'] for y in total_bugs]) or 0,
                                    'online_count': sum(
                                        [y['count'] for y in total_bugs if y['bug_level'] == '线上']) or 0,
                                    'offline_count': sum(
                                        [y['count'] for y in total_bugs if y['bug_level'] == '线下']) or 0
                                    },
                                 # **{'point': sum([y['point'] for y in total_bugs]) or 0},
                                 # **{'online_point': sum(
                                 #     [y['point'] for y in total_bugs if y['bug_level'] == '线上']) or 0},
                                 # **{'offline_point': sum(
                                 #     [y['point'] for y in total_bugs if y['bug_level'] == '线下']) or 0},
                                 **total_estimate,
                                 **{'offline_bug_rate':
                                        mode_number(sum([y['point'] for y in total_bugs if y['bug_level'] == '线下']),
                                                    total_estimate['day'], 2)
                                    }},
                     'details': details}
    return response_data


def get_month_report_by_project(start, end):
    projects = JiraProject.objects.filter().exclude(key__icontains='QA')
    base_qurey = Q(created__gte=start, created__lte=end, resolution__in=['完成', 'Unresolved'])
    proj_resp = []
    for project in projects:
        total_bugs = JiraBugCountGroup(
            JiraIssue.objects.filter(base_qurey, type=JiraIssueType.BUG.chinese, proj_id=project.id).values(
                'bug_level', 'sub_bug_level').annotate(count=Count('key')).order_by('bug_level', 'sub_bug_level'),
            many=True).data
        # 统计所有的估时
        total_estimate = JiraProjectTaskEstimate(
            JiraIssue.objects.filter(base_qurey, proj_id=project.id).exclude(
                type=JiraIssueType.BUG.chinese).aggregate(
                total_estimate=Sum('original_time_estimate'))).data
        response_data = {'proj_name': project.name}
        point = sum([y['point'] for y in total_bugs]) or 0
        offline_point = sum(
            [y['point'] for y in total_bugs if y['bug_level'] == '线下']) or 0
        response_data.update(
            {
                'count': sum([y['count'] for y in total_bugs]) or 0,
                'point': point,
                'online_point': sum(
                    [y['point'] for y in total_bugs if y['bug_level'] == '线上']) or 0,
                'offline_point': offline_point,
                'offline_bug_rate': mode_number(offline_point, total_estimate['day'], 2)
            }
        )

        proj_resp.append(response_data)
    return proj_resp


def get_month_bug_time_by_project(start, end):
    users = AccountSiri(AceAccount.objects.filter(user_role="QA"), many=True).data
    QA_users = [user.get('jira_user') for user in users if user.get('jira_user')]
    projects = JiraProject.objects.filter().exclude(key__in=['QA', 'DESIGND', 'WEBEDITOR', 'DEM', 'OPERATION'])
    base_qurey = Q(created__gte=start, created__lte=end, resolution__in=['完成', 'Unresolved'],
                   type=JiraIssueType.BUG.chinese) & ~Q(bugOwner__in=QA_users)
    proj_resp = []
    for project in projects:
        offline_bug_fixtime_list = JiraIssue.objects.filter(base_qurey, proj_id=project.id, bug_level='线下',
                                                            fix_time__isnull=False).values_list('fix_time', flat=True)
        online_bug_fixtime_list = JiraIssue.objects.filter(base_qurey, proj_id=project.id, bug_level='线上',
                                                           fix_time__isnull=False).values_list('fix_time', flat=True)
        offline_bug_closetime_list = JiraIssue.objects.filter(base_qurey, proj_id=project.id, bug_level='线下',
                                                              close_time__isnull=False).values_list('close_time',
                                                                                                    flat=True)
        online_bug_closetime_list = JiraIssue.objects.filter(base_qurey, proj_id=project.id, bug_level='线上',
                                                             close_time__isnull=False).values_list('close_time',
                                                                                                   flat=True)
        bug_fixtime_list = JiraIssue.objects.filter(base_qurey, proj_id=project.id,
                                                    sub_bug_level__in=['P0', 'P1', 'P2', 'P3', 'S0', 'S1'],
                                                    fix_time__isnull=False).values_list('fix_time', flat=True)
        bug_closetime_list = JiraIssue.objects.filter(base_qurey, proj_id=project.id,
                                                      sub_bug_level__in=['P0', 'P1', 'P2', 'P3', 'S0', 'S1'],
                                                      close_time__isnull=False).values_list('close_time', flat=True)
        proj_resp.append({
            'proj_name': project.name,
            'offline_avg_fix_time': mode_number(
                mode_number(sum(offline_bug_fixtime_list), len(offline_bug_fixtime_list), 2), 3600, 2),
            'offline_avg_close_time': mode_number(
                mode_number(sum(offline_bug_closetime_list), len(offline_bug_closetime_list), 2), 3600, 2),
            'online_avg_fix_time': mode_number(
                mode_number(sum(online_bug_fixtime_list), len(online_bug_fixtime_list), 2), 3600, 2),
            'online_avg_close_time': mode_number(
                mode_number(sum(online_bug_closetime_list), len(online_bug_closetime_list), 2), 3600, 2),
            'avg_fix_time': mode_number(
                mode_number(sum(bug_fixtime_list), len(bug_fixtime_list), 2), 3600, 2),
            'avg_close_time': mode_number(
                mode_number(sum(bug_closetime_list), len(bug_closetime_list), 2), 3600, 2)
        })

    return proj_resp


def get_month_bug_time_by_depart(start, end):
    all_users = get_department_users()
    base_qurey = Q(created__gte=start, created__lte=end, resolution__in=['完成', 'Unresolved'],
                   type=JiraIssueType.BUG.chinese)
    depart_resp = []
    for user in all_users:
        offline_bug_fixtime_list = JiraIssue.objects.filter(base_qurey, bugOwner__in=user['jira_users'],
                                                            bug_level='线下', fix_time__isnull=False).values_list(
            'fix_time', flat=True)
        online_bug_fixtime_list = JiraIssue.objects.filter(base_qurey, bugOwner__in=user['jira_users'],
                                                           bug_level='线上', fix_time__isnull=False).values_list(
            'fix_time', flat=True)
        offline_bug_closetime_list = JiraIssue.objects.filter(base_qurey, bugOwner__in=user['jira_users'],
                                                              bug_level='线下', close_time__isnull=False).values_list(
            'close_time', flat=True)
        online_bug_closetime_list = JiraIssue.objects.filter(base_qurey, bugOwner__in=user['jira_users'],
                                                             bug_level='线上', close_time__isnull=False).values_list(
            'close_time', flat=True)
        bug_fixtime_list = JiraIssue.objects.filter(base_qurey, bugOwner__in=user['jira_users'],
                                                    sub_bug_level__in=['P0', 'P1', 'P2', 'P3', 'S0', 'S1'],
                                                    fix_time__isnull=False).values_list('fix_time', flat=True)
        bug_closetime_list = JiraIssue.objects.filter(base_qurey, bugOwner__in=user['jira_users'],
                                                      sub_bug_level__in=['P0', 'P1', 'P2', 'P3', 'S0', 'S1'],
                                                      close_time__isnull=False).values_list('close_time', flat=True)
        depart_resp.append({'depart_name': user['depart_name'],
                            'offline_avg_fix_time': mode_number(
                                mode_number(sum(offline_bug_fixtime_list), len(offline_bug_fixtime_list), 2), 3600, 2),
                            'offline_avg_close_time': mode_number(
                                mode_number(sum(offline_bug_closetime_list), len(offline_bug_closetime_list), 2), 3600,
                                2),
                            'online_avg_fix_time': mode_number(
                                mode_number(sum(online_bug_fixtime_list), len(online_bug_fixtime_list), 2), 3600, 2),
                            'online_avg_close_time': mode_number(
                                mode_number(sum(online_bug_closetime_list), len(online_bug_closetime_list), 2), 3600,
                                2),
                            'avg_fix_time': mode_number(
                                mode_number(sum(bug_fixtime_list), len(bug_fixtime_list), 2), 3600, 2),
                            'avg_close_time': mode_number(
                                mode_number(sum(bug_closetime_list), len(bug_closetime_list), 2), 3600,
                                2)})
    return depart_resp


def get_month_report_by_department(start, end):
    # 获取技术部下所有人员（离职除外）
    query = Q(deactivated_at=default_deactive_time) & Q(parent_open_department_id="od-6ac439ac289537cafd7d6e5cdff6a5e9")
    with catch_error():
        queryset = AceDepartment.objects.filter(query)
        depart_data = DepartmentSiri(queryset, many=True).data
        parent_nodes = [node.open_department_id for node in queryset]
        while len(AceDepartment.objects.filter(parent_open_department_id__in=parent_nodes,
                                               deactivated_at=default_deactive_time)):
            extra_queryset = AceDepartment.objects.filter(parent_open_department_id__in=parent_nodes,
                                                          deactivated_at=default_deactive_time).exclude(
                open_department_id__in=parent_nodes)
            parent_nodes = [node.open_department_id for node in extra_queryset]
            depart_data.extend(DepartmentSiri(extra_queryset, many=True).data)
    all_departs = [depart.get('open_department_id') for depart in depart_data]
    user_ids = AceDepartmentAccount.objects.filter(open_department_id__in=all_departs,
                                                   deactivated_at=default_deactive_time).values_list('account_id',
                                                                                                     flat=True)
    users = AccountSiri(AceAccount.objects.filter(id__in=user_ids), many=True).data
    jira_users = [user.get('jira_user') for user in users]
    bug_query = Q(created__gte=start, created__lte=end, type=JiraIssueType.BUG.chinese,
                  resolution__in=['完成', 'Unresolved'], bugOwner__in=jira_users)
    task_query = Q(created__gte=start, created__lte=end) & ~Q(type=JiraIssueType.BUG.chinese) & Q(
        resolution__in=['完成', 'Unresolved']) & Q(bugOwner__in=jira_users)
    # 统计全部bug
    total_bugs = JiraBugCountDepart(
        JiraIssue.objects.filter(bug_query).values(
            'bug_level', 'sub_bug_level').annotate(count=Count('key')).order_by('bug_level', 'sub_bug_level'),
        many=True).data
    # 统计所有的估时
    total_estimate = JiraDepartTaskEstimate(
        JiraIssue.objects.filter(task_query).aggregate(
            total_estimate=Sum('original_time_estimate'))).data
    # 统计全部人数
    total_people = JiraIssue.objects.filter(task_query).values('assignee').distinct()
    total_people_count = len(total_people)
    # 按部门统计bug情况
    depart_bugs = JiraIssue.objects.filter(bug_query).values(
        'bug_level', 'sub_bug_level', 'bugOwner').annotate(count=Count('key')).order_by('bugOwner', 'bug_level',
                                                                                        'sub_bug_level')
    # 按部门统计估时
    depart_estimates = JiraIssue.objects.filter(task_query).values('bugOwner').annotate(
        total_estimate=Sum('original_time_estimate'))
    depart_bugs = JiraBugCountDepart(depart_bugs, many=True).data
    depart_bugs.sort(key=lambda x: x['depart_name'])
    depart_bugs = [{'depart_name': key, 'bugs': list(bug_groups)} for key, bug_groups in
                   groupby(depart_bugs, itemgetter('depart_name'))]
    depart_bugs = list(map(lambda x: dict(x, **{'count': sum([y['count'] for y in x['bugs']]) or 0,
                                                'offline_count': sum(
                                                    [y['count'] for y in x['bugs'] if y['bug_level'] == '线下']) or 0,
                                                'online_count': sum(
                                                    [y['count'] for y in x['bugs'] if y['bug_level'] == '线上']) or 0,
                                                'point': sum(y['point'] for y in x['bugs']) or 0,
                                                'online_point': sum(
                                                    [y['point'] for y in x['bugs'] if y['bug_level'] == '线上']) or 0,
                                                'offline_point': sum(
                                                    [y['point'] for y in x['bugs'] if y['bug_level'] == '线下']) or 0,
                                                }), depart_bugs))
    for index in range(len(depart_bugs)):
        if depart_bugs[index]['bugs']:
            depart_bugs[index]['bugs'] = [{"bug_level": "线上", "sub_bug_level": "P0",
                                           "depart_name": depart_bugs[index]['depart_name'],
                                           "count": sum([y['count'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线上' and y['sub_bug_level'] == 'P0']) or 0,
                                           "point": sum([y['point'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线上' and y['sub_bug_level'] == 'P0']) or 0},
                                          {"bug_level": "线上", "sub_bug_level": "P1",
                                           "depart_name": depart_bugs[index]['depart_name'],
                                           "count": sum([y['count'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线上' and y['sub_bug_level'] == 'P1']) or 0,
                                           "point": sum([y['point'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线上' and y['sub_bug_level'] == 'P1']) or 0},
                                          {"bug_level": "线上", "sub_bug_level": "P2",
                                           "depart_name": depart_bugs[index]['depart_name'],
                                           "count": sum([y['count'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线上' and y['sub_bug_level'] == 'P2']) or 0,
                                           "point": sum([y['point'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线上' and y['sub_bug_level'] == 'P2']) or 0},
                                          {"bug_level": "线上", "sub_bug_level": "P3",
                                           "depart_name": depart_bugs[index]['depart_name'],
                                           "count": sum([y['count'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线上' and y['sub_bug_level'] == 'P3']) or 0,
                                           "point": sum([y['point'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线上' and y['sub_bug_level'] == 'P3']) or 0},
                                          {"bug_level": "线下", "sub_bug_level": "S0",
                                           "depart_name": depart_bugs[index]['depart_name'],
                                           "count": sum([y['count'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线下' and y['sub_bug_level'] == 'S0']) or 0,
                                           "point": sum([y['point'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线下' and y['sub_bug_level'] == 'S0']) or 0},
                                          {"bug_level": "线下", "sub_bug_level": "S1",
                                           "depart_name": depart_bugs[index]['depart_name'],
                                           "count": sum([y['count'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线下' and y['sub_bug_level'] == 'S1']) or 0,
                                           "point": sum([y['point'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线下' and y['sub_bug_level'] == 'S1']) or 0},
                                          {"bug_level": "线下", "sub_bug_level": "S2",
                                           "depart_name": depart_bugs[index]['depart_name'],
                                           "count": sum([y['count'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线下' and y['sub_bug_level'] == 'S2']) or 0,
                                           "point": sum([y['point'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线下' and y['sub_bug_level'] == 'S2']) or 0},
                                          {"bug_level": "线下", "sub_bug_level": "S3",
                                           "depart_name": depart_bugs[index]['depart_name'],
                                           "count": sum([y['count'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线下' and y['sub_bug_level'] == 'S3']) or 0,
                                           "point": sum([y['point'] for y in depart_bugs[index]['bugs'] if
                                                         y['bug_level'] == '线下' and y['sub_bug_level'] == 'S3']) or 0}
                                          ]
    # 每个部门的估时统计
    depart_estimates = JiraDepartTaskEstimate(depart_estimates, many=True).data
    depart_estimates.sort(key=lambda x: x['depart_name'])
    estimates = groupby(depart_estimates, itemgetter("depart_name"))
    depart_times = [
        {'depart_name': key, 'times': [(x['total_estimate'], x['day'], x['bugOwner']) for x in list(bug_groups)]} for
        key, bug_groups in estimates]
    department_estimates = []
    for depart_time in depart_times:
        estimate_list = []
        day_list = []
        people = []
        for time in depart_time.get('times'):
            estimate_list.append(time[0])
            day_list.append(time[1])
            people.append(time[2])
        all_estimate = sum(estimate_list)
        day = round(sum(day_list), 3)
        people_count = len(set(people))
        depart_time.update({'total_estimate': all_estimate})
        depart_time.update({'day': day})
        depart_time.update(({'people_count': people_count}))
        del depart_time['times']
        department_estimates.append(depart_time)
    department_estimates.sort(key=lambda x: x['depart_name'])
    # 合并项目的估时和bug
    details = merge_2_dict_list(depart_bugs, department_estimates, 'depart_name')
    bug_times = get_month_bug_time_by_depart(start, end)
    bug_times.sort(key=lambda x: x['depart_name'])
    details = merge_2_dict_list(details, bug_times, 'depart_name')
    details.sort(key=lambda x: x['depart_name'])
    for index in range(len(details)):
        details[index]['offline_bug_rate'] = mode_number(details[index].get('offline_point'),
                                                         details[index].get("day"), 2)
    response_data = {'summary': {**{'bugs': total_bugs},
                                 **{'people_count': total_people_count},
                                 **{'count': sum([y['count'] for y in total_bugs]) or 0,
                                    'online_count': sum(
                                        [y['count'] for y in total_bugs if y['bug_level'] == '线上']) or 0,
                                    'offline_count': sum(
                                        [y['count'] for y in total_bugs if y['bug_level'] == '线下']) or 0
                                    },
                                 **total_estimate,
                                 **{'offline_bug_rate': mode_number(sum([y['point'] for y in total_bugs
                                                                         if y['bug_level'] == '线下']),
                                                                    total_estimate['day'], 2)
                                    }},
                     'details': details}
    return response_data

def cal_sprint_story_status(sprint_id,type='qa'):
    '''计算每个迭代周期内story的状态'''
    # 遍历出还未到截止日期的所有sprint
    # qa_version = JiraFixVersions.objects.filter(sprint_id=sprint_id, name__icontains='QA').values_list('id')
    users = AccountSiri(AceAccount.objects.filter(user_role="QA"), many=True).data
    qa_user = [user.get('jira_user') for user in users if user.get('jira_user')]
    sprint = JiraSprint.objects.get(id=sprint_id)
    try:
        dates = []
        date = sprint.start_date
        # 得到每个sprint的日期列表
        while date and sprint.end_date and date <= sprint.end_date:
            dates.append(date.strftime("%Y-%m-%d"))
            date = date + datetime.timedelta(1)
        # 查询每个sprint的story
        total_story = JiraIssue.objects.filter(type='Story', sprint_id__contains=f"'{sprint_id}'",
                                                      ).values('key', 'assignee', 'summary')
        date_stories = {key: [] for key in dates}
        total_estimate = 0
        for story in total_story:
            # 所有子任务的估时总和为需求的需求人天
            story_estimate = second_2_days(
                sum(JiraIssue.objects.filter(parent_key=story['key']).values_list('original_time_estimate', flat=True)))
            total_estimate += story_estimate
            # 查询所有需求的截止时间不为空开发子任务
            if type == 'dev':
                tasks = JiraIssue.objects.filter(
                    parent_key=story['key'], resolution__in=task_resolution, target_end__isnull=False)\
                    .exclude(assignee__in=qa_user)\
                    .values('target_end', 'resolution')
            # 查询所有需求的截止时间不为空测试子任务
            elif type == 'qa':
                query = Q(parent_key=story['key'], resolution__in=task_resolution, target_end__isnull=False, assignee__in=qa_user)
                tasks = JiraIssue.objects.filter(query).values('target_end', 'resolution')
            if len(tasks):
                # 获得一个需求中，所有子任务target_end日期为story的截止日期
                story_end = max(task['target_end'] for task in tasks)
                # 当前日期与需求截止日期的天数差
                story_days = (datetime.datetime.now() - story_end).days
                if story_days < 1:
                    story_status = JiraStoryTestStatus.InProgress.value
                else:
                    story_status = JiraStoryTestStatus.Normal.value
                for task in tasks:
                    if (datetime.datetime.now() - task['target_end']).days >= 1 and task['resolution'] == 'Unresolved':
                        story_status = JiraStoryTestStatus.Delay.value
                        continue
                if story_end.strftime("%Y-%m-%d") in dates:
                    date_stories[story_end.strftime("%Y-%m-%d")].append({'status': story_status,
                                                                         'estimate': story_estimate,
                                                                         'key': f"http://jira.jiliguala.com/browse/{story['key']}",
                                                                         'assignee': story['assignee'],
                                                                         'summary': story['summary']})
        # 计算所有天数中每天最大的延期、正常、未提测需求数，便于构造echarts数据
        max_delay, max_normal, max_inprogress = 0, 0, 0
        for key in dates:
            status_dict = Counter(item['status'] for item in date_stories[key])
            max_delay, max_normal, max_inprogress = max(max_delay,
                                                        status_dict.get(JiraStoryTestStatus.Delay.value, 0)), max(
                max_normal, status_dict.get(JiraStoryTestStatus.Normal.value, 0)), max(max_inprogress, status_dict.get(
                JiraStoryTestStatus.InProgress.value, 0))
        delay_flag, normal_flag, inprogress_flag = False or not max_delay, False or not max_normal, False or not max_inprogress
        # 构造echarts series数据
        date_stories_format = {key: [] for key in dates}
        series = []
        if not normal_flag:
            for key in dates:
                date_stories_format[key].extend([{'value': item['estimate'], 'key': item['key'],
                                                  'name': f"{item['summary']} 主R:{item['assignee']}"} for item in date_stories[key] if item['status'] == JiraStoryTestStatus.Normal.value])
                date_stories_format[key].extend([0] * (max_normal - len(date_stories_format[key])))
        if not delay_flag:
            for key in dates:
                date_stories_format[key].extend([{'value': item['estimate'], 'key': item['key'],
                                                  'name': f"{item['summary']} 主R:{item['assignee']}"} for item in date_stories[key] if item['status'] == JiraStoryTestStatus.Delay.value])
                date_stories_format[key].extend([0] * (max_normal + max_delay - len(date_stories_format[key])))
        if not inprogress_flag:
            for key in dates:
                date_stories_format[key].extend([{'value': item['estimate'], 'key': item['key'],
                                                  'name': f"{item['summary']} 主R:{item['assignee']}"} for item in date_stories[key] if
                                                 item['status'] == JiraStoryTestStatus.InProgress.value])
                date_stories_format[key].extend([0] * (max_normal + max_delay + max_inprogress - len(date_stories_format[key])))
        for i in range(max_normal + max_delay + max_inprogress):
            if i < max_normal:
                series.append({
                'name': '正常' if type == 'dev' else '测试完成',
                'type': 'bar',
                'stack': '提测',
                'emphasis': {
                    'focus': 'series'
                },
                'data': [date_stories_format[item][i] for item in dates]})
            elif max_normal <= i < max_normal + max_delay:
                series.append({
                    'name': '延期' if type == 'dev' else '测试未完成',
                    'type': 'bar',
                    'stack': '提测',
                    'emphasis': {
                        'focus': 'series'
                    },
                    'data': [date_stories_format[item][i] for item in dates]
                })
            elif max_normal + max_delay <= i < max_normal + max_delay + max_inprogress:
                series.append({
                    'name': '未提测' if type == 'dev' else '测试未开始',
                    'type': 'bar',
                    'stack': '提测',
                    'emphasis': {
                        'focus': 'series'
                    },
                    'data': [date_stories_format[item][i] for item in dates]
                })
        average_estimate = mode_number(total_estimate, len(dates), 3)
        if len(series):
            series[0].update({'markLine': {'data': [{'yAxis': average_estimate}],
                                           'silent': True,
                                           'lineStyle': {
                                                'color': '#4b67b8',
                                               }
                                           }})
        return {'dates': dates, 'stories': series}
    except Exception as e:
        raise e

def cal_sprint_task_status_overview(sprint, row_id):
    """冲刺总揽计算"""
    dates = []
    date = sprint['start_date']
    # 得到每个sprint的日期列表
    while date and sprint['end_date'] and date <= sprint['end_date']:
        dates.append(date)
        date = date + datetime.timedelta(1)
    all_subTask = JiraIssue.objects.filter(type=JiraIssueType.SUBTASK.chinese, resolution__in=task_resolution, sprint_id__contains=f'\'{sprint["id"]}\'', target_end__isnull=False).order_by('target_end').values('id', 'target_end', 'resolution')
    tasks = []
    for dt in dates:
        resolution_set = set([item['resolution'] for item in all_subTask if item['target_end'].strftime("%Y-%m-%d") == dt.strftime("%Y-%m-%d")])
        days = (datetime.date.today() - dt).days
        task = {'id': f"{sprint['id']}{dates.index(dt)}",
                'sprint_id': sprint['id'],
                'proj_id': sprint['proj_id'],
                'row_id': str(row_id),
                'time': {
                    'start': time.mktime(dt.timetuple()) * 1000,
                    'end': time.mktime((dt + datetime.timedelta(1)).timetuple()) * 1000 - 1
                }}
        if days > 0 and resolution_set in [{'完成'}, set()]:
            task['status'] = JiraStoryTestStatus.Normal.value
            if tasks and tasks[-1]['status'] == task['status']:
                tasks[-1]['time']['end'] = task['time']['end']
            else:
                tasks.append(task)
        elif days > 0 and 'Unresolved' in resolution_set:
            task['status'] = JiraStoryTestStatus.Delay.value
            if tasks and tasks[-1]['status'] == task['status']:
                tasks[-1]['time']['end'] = task['time']['end']
            else:
                tasks.append(task)
        elif days == 0:
            task['status'] = JiraStoryTestStatus.Today.value
            if tasks and tasks[-1]['status'] == task['status']:
                tasks[-1]['time']['end'] = task['time']['end']
            else:
                tasks.append(task)
        else:
            task['status'] = JiraStoryTestStatus.InProgress.value
            if tasks and tasks[-1]['status'] == task['status']:
                tasks[-1]['time']['end'] = task['time']['end']
            else:
                tasks.append(task)
    return tasks


def get_department_users():
    """获取技术部下对应员工"""
    # now_date = datetime.datetime.now()
    # 获取本月的第一天，为了去除上月之前离职的员工
    # first_day = datetime.datetime(now_date.year, now_date.month, day=1)
    # initial_date = datetime.datetime(year=1970, month=1, day=1)
    all_users = []
    query = Q(deactivated_at=default_deactive_time) & Q(parent_open_department_id="od-6ac439ac289537cafd7d6e5cdff6a5e9")
    with catch_error():
        # 获取技术部下所有部门
        queryset = AceDepartment.objects.filter(query).values("open_department_id", "name",
                                                              "parent_open_department_ids")
        department_data = DevDepartmentSiri(queryset, many=True).data
        parent_nodes = [node.get('open_department_id') for node in queryset]
        while len(AceDepartment.objects.filter(parent_open_department_id__in=parent_nodes,
                                               deactivated_at=default_deactive_time)):
            extra_queryset = AceDepartment.objects.filter(parent_open_department_id__in=parent_nodes,
                                                          deactivated_at=default_deactive_time).exclude(
                open_department_id__in=parent_nodes).values("open_department_id", "name", "parent_open_department_ids")
            parent_nodes = [node.get('open_department_id') for node in extra_queryset]
            department_data.extend(DevDepartmentSiri(extra_queryset, many=True).data)
        department_data.sort(key=lambda x: x['full_name'])
        for department in department_data:
            depart_dict = {}
            # 判断该部门下是否有二级部门，若有二级部门则当前部门不统计，已最小部门单位为维度统计
            # secondary_department = AceDepartment.objects.filter(
            #     parent_open_department_id=department['open_department_id']).values()
            # if secondary_department:
            #     continue
            # 每个部门的leader
            leader = AceAccount.objects.filter(id=department.get('leader_id'))
            leader_name = leader[0].name if leader else DepartmentLeader.get_chinese(
                department['full_name'].split('/')[0])
            # 每个部门下的人员(排除离职人员)
            user_ids = AceDepartmentAccount.objects.filter(
                open_department_id=department.get('open_department_id'),
                deactivated_at=default_deactive_time).values_list('account_id', flat=True)
            users = AccountSiri(AceAccount.objects.filter(id__in=user_ids), many=True).data
            jira_users = [user.get('jira_user') for user in users]
            depart_dict.update(
                {'depart_name': department['full_name'], "jira_users": jira_users, "leader": leader_name})
            all_users.append(depart_dict)
    return all_users


def judge_sprint_exception(sprint_id):
    exception_point = json.loads(RedisClient.get_client('cache').get(f'sprint_warning_{sprint_id}') or '{}')
    if exception_point:
        return exception_point
    sprint = JiraSprint.objects.get(id=sprint_id)
    if not sprint.start_date or not sprint.end_date:
        raise ValueError('sprint没有设置开始、结束日期')
    scrum_master = JiraProject.objects.get(id=sprint.proj_id).lead
    # 判断有没有task起止时间不完整
    query = Q(sprint_id__contains=f"'{sprint_id}'") & Q(type=JiraIssueType.SUBTASK.chinese) & (Q(target_start__isnull=True) | Q(target_end__isnull=True))
    target_start_end_null_task = JiraIssue.objects.filter(query)
    if len(target_start_end_null_task):
        exception_point['target_start_end_null_exception'] = []
        for task in target_start_end_null_task:
            exception_point['target_start_end_null_exception'].append(f'{task.key}--{task.summary}， 经办人: {task.assignee}')
    # 判断有没有task起止时间超过迭代时间范围
    query = Q(sprint_id__contains=f"'{sprint_id}'") & (Q(target_start__lt=sprint.start_date) | Q(target_end__gt=sprint.end_date))
    target_start_end_exce_task = JiraIssue.objects.filter(query)
    if len(target_start_end_exce_task):
        exception_point['target_start_end_wrong_exception'] = []
        for task in target_start_end_exce_task:
            exception_point['target_start_end_wrong_exception'].append(f'{task.key}--{task.summary}， 经办人: {task.assignee}')
    # 判断有没有bug未关联迭代
    no_sprint_bugs = JiraIssue.objects.filter(type=JiraIssueType.BUG.chinese, proj_id=sprint.proj_id, created__gte=sprint.start_date.strftime("%Y-%m-%d 00:00:00"), created__lte=sprint.end_date.strftime("%Y-%m-%d 23:59:59"), sprint_id__isnull=True)
    if len(no_sprint_bugs):
        exception_point['bug_no_sprint_exception'] = []
        for bug in no_sprint_bugs:
            exception_point['bug_no_sprint_exception'].append(f'{bug.key}--{bug.summary}， 报告人: {bug.creator}')
    # 判断有没有story未拆子任务，跟测&回归、资源损耗这两个story除外
    has_sub_tasks_story = list(set(JiraIssue.objects.filter(sprint_id__contains=f"'{sprint_id}'", parent_key__isnull=False).values_list('parent_key', flat=True)))
    no_sub_tasks_story = JiraIssue.objects.filter(type=JiraIssueType.STORY.chinese, sprint_id__contains=f"'{sprint_id}'").exclude(key__in=has_sub_tasks_story).\
        exclude(Q(summary__contains='跟测&回归')|Q(summary__contains='资源损耗'))
    if len(no_sub_tasks_story):
        exception_point['story_no_sub_task_exception'] = []
        for story in no_sub_tasks_story:
            exception_point['story_no_sub_task_exception'].append(f'{story.key}--{story.summary}， SM: {scrum_master}')
    # 判断有没有story未关联epic，跟测&回归、资源损耗这两个story除外
    no_epic_story = JiraIssue.objects.filter(type=JiraIssueType.STORY.chinese, sprint_id__contains=f"'{sprint_id}'", epic_key__isnull=True).exclude(summary__contains='跟测&回归').exclude(summary__contains='资源损耗')
    if len(no_epic_story):
        exception_point['no_epic_story_exception'] = []
        for story in no_epic_story:
            exception_point['no_epic_story_exception'].append(f'{story.key}--{story.summary}， 报告人: {story.creator}')
    # 判断迭代内必须创建跟测&回归、资源损耗这两个story
    no_common_story = JiraIssue.objects.filter(Q(sprint_id__contains=f"'{sprint_id}'") & Q(type=JiraIssueType.STORY.chinese) & (Q(summary__contains='跟测&回归')|Q(summary__contains='资源损耗')))
    if len(no_common_story) < 2:
        exception_point['no_common_story_exception'] = []
        if len(no_common_story):
            if '跟测&回归' not in no_common_story.first().summary:
                exception_point['no_common_story_exception'].append(f'未创建【跟测&回归】通用型Story， SM：{scrum_master}')
            elif '资源损耗' not in no_common_story.first().summary:
                exception_point['no_common_story_exception'].append(f'未创建【资源损耗】通用型Story， SM：{scrum_master}')
        else:
            exception_point['no_common_story_exception'].append(f'未创建【跟测&回归】通用型Story， SM：{scrum_master}')
            exception_point['no_common_story_exception'].append(f'未创建【资源损耗】通用型Story， SM：{scrum_master}')
    # 判断迭代内必须创建需求变更/新增、技改这两个epic(Epic不跟迭代关联，统计迭代所属项目下有无即可)
    no_common_epics = JiraIssue.objects.filter(
        Q(proj_key=sprint.proj_key) & Q(type=JiraIssueType.EPIC.chinese) & Q(resolution="Unresolved")
        & (Q(summary__contains='需求变更') | Q(summary__contains='技改')))
    if len(no_common_epics) < 2:
        exception_point['no_common_epic_exception'] = []
        if len(no_common_epics):
            if '需求变更' not in no_common_epics.first().summary:
                exception_point['no_common_epic_exception'].append(f'未创建【需求变更/新增】 Epic， SM：{scrum_master}')
            elif '技改' not in no_common_epics.first().summary:
                exception_point['no_common_epic_exception'].append(f'未创建【技改】 Epic:， SM：{scrum_master}')
        else:
            exception_point['no_common_epic_exception'].append(f'未创建【需求变更/新增】 Epic， SM：{scrum_master}')
            exception_point['no_common_epic_exception'].append(f'未创建【技改】 Epic:， SM：{scrum_master}')
    RedisClient.get_client('cache').set(f'sprint_warning_{sprint_id}', json.dumps(exception_point), ex=300)
    return exception_point


def create_personal_resource_report():
    """同步技术部个人月度资源"""
    month_str = datetime.datetime.now().strftime("%Y-%m")
    month = month_str.split('-')
    days = get_three_month_start_end(int(month[0]), int(month[1]))
    all_users = get_department_users()
    work_days = chinese_calendar.get_workdays(start=days["current_month_first_day"],
                                              end=days["current_month_last_day"])
    resp = []
    for users in all_users:
        for user in users['jira_users']:
            user_dict = {}
            if user:
                email = User.objects.filter(username=user).values_list('email', flat=True)
                user_name = AceAccount.objects.filter(email=email[0]).first().name
                # 上月开始，本月完成
                pre_task_query = Q(target_start__gte=days['first_day_of_pre_month'],
                                   target_start__lte=days['last_day_of_pre_month']) & Q(
                    target_end__gte=days['current_month_first_day'],
                    target_end__lte=days['current_month_last_day']) & Q(
                    type=JiraIssueType.SUBTASK.chinese) & Q(bugOwner=user) & Q(bugOwner__isnull=False) & Q(
                    original_time_estimate__isnull=False)
                # 本月开始，本月完成
                current_task_query = Q(target_start__gte=days['current_month_first_day'],
                                       target_start__lte=days['current_month_last_day']) & Q(
                    target_end__gte=days['current_month_first_day'],
                    target_end__lte=days['current_month_last_day']) & Q(
                    type=JiraIssueType.SUBTASK.chinese) & Q(bugOwner=user) & Q(bugOwner__isnull=False) & Q(
                    original_time_estimate__isnull=False)
                # 本月开始，下月完成
                next_task_query = Q(target_start__gte=days['current_month_first_day'],
                                    target_start__lte=days['current_month_last_day']) & Q(
                    target_end__gte=days['first_day_of_next_month'],
                    target_end__lte=days['last_day_of_next_month']) & Q(
                    type=JiraIssueType.SUBTASK.chinese) & Q(bugOwner=user) & Q(bugOwner__isnull=False) & Q(
                    original_time_estimate__isnull=False)
                # 上月开始，本月完成的数据
                pre_datas = JiraIssue.objects.filter(pre_task_query).values('target_start', 'target_end',
                                                                            'original_time_estimate')
                pre_work_days = 0
                for pre_data in pre_datas:
                    pre_work_day = chinese_calendar.get_workdays(start=days['current_month_first_day'],
                                                                 end=pre_data.get('target_end'))
                    all_pre_work_day = chinese_calendar.get_workdays(start=pre_data.get('target_start'),
                                                                 end=pre_data.get('target_end'))
                    pre_estimate = round(len(pre_work_day) / len(all_pre_work_day), 6) * pre_data.get(
                        'original_time_estimate')
                    pre_work_days = pre_work_days + pre_estimate
                # 本月开始，本月完成的数据
                current_datas = JiraIssue.objects.filter(current_task_query).values('target_start', 'target_end',
                                                                                    'original_time_estimate')
                current_work_days = 0
                for current_data in current_datas:
                    cur_estimate = current_data.get('original_time_estimate')
                    current_work_days = current_work_days + cur_estimate
                # 本月开始，下月完成的数据
                next_datas = JiraIssue.objects.filter(next_task_query).values('target_start', 'target_end',
                                                                              'original_time_estimate')
                next_work_days = 0
                for next_data in next_datas:
                    next_work_day = chinese_calendar.get_workdays(start=next_data.get('target_start'),
                                                                  end=days['current_month_last_day'])
                    all_next_work_day = chinese_calendar.get_workdays(start=next_data.get('target_start'),
                                                                      end=next_data.get('target_end'))
                    next_estimate = round(len(next_work_day) / len(all_next_work_day), 6) * next_data.get(
                        'original_time_estimate')
                    next_work_days = next_work_days + next_estimate
                pre_work_days = second_2_days(pre_work_days)
                current_work_days = second_2_days(current_work_days)
                next_work_days = second_2_days(next_work_days)
                total_working_days = 1 * len(work_days)
                target_days_diff = total_working_days - (pre_work_days + current_work_days + next_work_days)
                productivity = round((total_working_days - target_days_diff) / total_working_days, 2)
                user_dict.update({"depart_name": users['depart_name'], "leader": users['leader'], "user_name": user_name,
                                  "work_days": len(work_days),
                                  "total_working_days": total_working_days,
                                  "pre_department_days": pre_work_days,
                                  "current_department_days": current_work_days,
                                  "next_department_days": next_work_days,
                                  "target_days_diff": target_days_diff,
                                  "productivity": productivity})
                resp.append(user_dict)
    return resp


def get_delay_story(stories, now_date, sprint_id, qa_tasks):
    """获取某个迭代延期的需求"""
    delay_story = []
    qa_keys = [task.get('key') for task in qa_tasks]
    for story in stories:
        # 取出所有子任务(QA的子任务除外)，按截止日期排序,最晚子任务结束时间是需求的提测时间
        sub_tasks = JiraIssue.objects.filter(parent_key=story, target_end__isnull=False).exclude(
            key__in=qa_keys).order_by('-target_end')
        if sub_tasks:
            # 提测时间小于今天的，若该story下还有未完成的子任务，则为延期story
            if sub_tasks.first().target_end < now_date:
                delay_tasks = JiraIssue.objects.filter(parent_key=story, resolution='Unresolved').exclude(
                    key__in=qa_keys)
                if delay_tasks:
                    delay_story.append(story)
            else:
                continue
    # 延期的需求需要存库
    old_delay_story = SprintEstimate.objects.filter(sprint_id=sprint_id, terminal='total').values_list(
        'delay_story')
    if old_delay_story:
        old_delay_story = old_delay_story[0]
    delay_story.extend(old_delay_story)
    delay_story = list(set(delay_story))
    return delay_story
