# -*- coding: utf-8 -*-
# @Time    : 2020/11/6 2:24 下午
# @Author  : zoey
# @File    : tasks.py
# @Software: PyCharm
from operator import itemgetter

import chinese_calendar

from zero.celery import app
import logging, math
from dateutil import parser
from django.db.models import Q
from django.db import transaction
from zero.jira.siris import JiraSprintSerializer, JiraEpicSiri, JiraProjectSerializer, JiraDelayTaskGroup, \
    JiraEpicSerializer
from zero.utils.format import datestrToDate, timeStampToDate, get_date_any, timestrToDatetime, timeStampToDatetime, \
    get_three_month_start_end, dateToTimeStamp, mode_number, second_2_days
from zero.jira import models
from zero.testTrack.models import TestPlanModel
from zero.jira.commands import JiraIssueType, JiraIssueStatus, jiraTool, JiraTerminalId, JiraTerminalName
from zero.jira.common import get_department_users, shortuuid, get_delay_story
import re
import datetime
from datetime import timedelta
from itertools import islice, groupby
from bulk_update.helper import bulk_update
from zero.organization.models import AceAccount
import traceback
import requests


def date_compile(n=-10):
    date_compile = datetime.datetime.now() + timedelta(minutes=n)
    return date_compile

task_resolution = ['完成', 'Unresolved']

def _sync_project():
    '''同步jira的project数据'''
    logging.info('--------------------同步jira的project数据-----------------------------')
    jira_projs = models.Project.objects.all()
    for jira_proj in jira_projs:
        try:
            lead_name = models.AppUser.objects.get(user_key=jira_proj.lead).lower_user_name
            models.JiraProject.objects.update_or_create(id=jira_proj.id,
                                                        defaults={"key": jira_proj.pkey,
                                                                  "name": jira_proj.pname,
                                                                  "description": jira_proj.description,
                                                                  "lead": lead_name})
        except Exception as e:
            logging.error(f'{jira_proj.pkey}{e}')
            continue
    models.JiraProject.objects.filter(updated_at__lt=date_compile()).delete()


def _sync_boards():
    '''同步jira的看板数据'''
    logging.info('--------------------同步jira的看板数据-----------------------------')
    projects = models.JiraProject.objects.all()
    bulk_creates = []
    for project in projects:
        try:
            boards = jiraTool.get_project_rapidviews(project.id)
            for board in boards['values']:
                bulk_creates.append(models.JiraBoards(id=board['id'], name=board['name'], proj_id=project.id, proj_key=project.key))
            # proj = models.Project.objects.get(Q(originalkey=proj_key) | Q(pkey=proj_key))
            # models.JiraBoards.objects.update_or_create(
            #     id=board.id,
            #     defaults={"proj_id": proj.id, "proj_key": proj.pkey, "name": board.name},
            # )
        except Exception as e:
            logging.error(f'{board.name}{e}')
            continue
    models.JiraBoards.objects.filter().delete()
    models.JiraBoards.objects.bulk_create(bulk_creates)


def _sync_fixVersion():
    '''同步版本'''
    logging.info('-------------------------------同步jira的版本-----------------------------------')
    versions = models.Projectversion.objects.filter()
    sync_versions = []
    for version in versions:
        try:
            sync_versions.append(models.JiraFixVersions(id=version.id, name=version.vname,
                                                        proj_id=version.project,
                                                        proj_key=models.JiraProject.objects.get(id=version.project).key,
                                                        sprint_id=None,
                                                        start_date=version.startdate,
                                                        release_date=version.releasedate,
                                                        description=version.description))
        except Exception as e:
            logging.error(f'{version.vname}{e}')
            continue
    with transaction.atomic():
        models.JiraFixVersions.objects.filter().delete()
        models.JiraFixVersions.objects.bulk_create(sync_versions, 1000)


def _sync_sprints():
    '''同步jira的sprint数据'''
    logging.info('--------------------同步jira的sprint数据-----------------------------')
    sprints = models.Ao60Db71Sprint.objects.filter()
    sprint_ids = [sprint.id for sprint in sprints]
    models.JiraSprint.objects.exclude(id__in=sprint_ids).delete()
    # 已经创建过的sprint
    created_sprint_ids = list(models.JiraSprint.objects.filter().values_list('id', flat=True))
    created_sprints = models.Ao60Db71Sprint.objects.filter(id__in=created_sprint_ids)
    not_exist_sprints = models.Ao60Db71Sprint.objects.exclude(id__in=created_sprint_ids)
    bulk_create_sprints = []
    bulk_update_sprints = []
    for sprint in not_exist_sprints:
        try:
            board = models.JiraBoards.objects.get(id=sprint.rapid_view_id)
            bulk_create_sprints.append(models.JiraSprint(id=sprint.id,
                                                         goal=sprint.goal,
                                                         name=sprint.name,
                                                         board_id=sprint.rapid_view_id,
                                                         proj_id=board.proj_id,
                                                         proj_key=board.proj_key,
                                                         closed=sprint.closed,
                                                         complete_date=timeStampToDate(sprint.complete_date),
                                                         end_date=timeStampToDate(sprint.end_date),
                                                         started=sprint.started,
                                                         start_date=timeStampToDate(sprint.start_date),))
        except Exception as e:
            logging.error(f'{sprint.name}{e}{sprint.rapid_view_id}')
    # 批量创建
    print('批量创建')
    models.JiraSprint.objects.bulk_create(bulk_create_sprints)
    for sprint in created_sprints:
        try:
            board = models.JiraBoards.objects.get(id=sprint.rapid_view_id)
            bulk_update_sprints.append(models.JiraSprint(id=sprint.id,
                                                         goal=sprint.goal,
                                                         name=sprint.name,
                                                         updated_at=datetime.datetime.now(),
                                                         board_id=sprint.rapid_view_id,
                                                         proj_id=board.proj_id,
                                                         proj_key=board.proj_key,
                                                         closed=sprint.closed,
                                                         complete_date=timeStampToDate(sprint.complete_date),
                                                         end_date=timeStampToDate(sprint.end_date),
                                                         started=sprint.started,
                                                         start_date=timeStampToDate(sprint.start_date)))
        except Exception as e:
            logging.error(f'{sprint.name}{e}{sprint.rapid_view_id}')
    # 批量更新
    print('批量更新')
    models.JiraSprint.objects.bulk_update(bulk_update_sprints, ['goal', 'name', 'updated_at','board_id', 'proj_id', 'proj_key', 'closed', 'complete_date', 'end_date', 'started', 'start_date'], batch_size=500)

@app.task()
def calc_sprint_estimate_report(days=-30, spr_id=None):
    """计算每个迭代的各职能团队投入产出"""
    logging.info('-------------------------------计算每个迭代的各职能团队投入产出-----------------------------------')
    date = get_date_any(days)
    now_dt = datetime.datetime.now()
    now_date = datetime.datetime(year=now_dt.year, month=now_dt.month, day=now_dt.day)
    terminalSort = [item.value for item in JiraTerminalId]
    # chinese_calendar插件目前只支持统计2021底的日期内的工作日
    if spr_id:
        sprint_ids = [spr_id]
    else:
        sprint_ids = models.JiraSprint.objects.filter(end_date__gte=date,
                                                      end_date__lte=datetime.datetime(2022, 1, 1)).values_list(
            'id', flat=True)
    # 技改epics
    tech_epics = models.JiraIssue.objects.filter(type='Epic', summary__contains='技改').values_list('key', flat=True)
    # 需求变更epics
    change_epics = models.JiraIssue.objects.filter(type='Epic', summary__contains='需求变更').values_list('key', flat=True)
    for sprint_id in sprint_ids:
        sum_estimate = 0
        qa_estimate = 0
        sum_tech_estimate = 0
        sum_change_estimate = 0
        sum_resource_depletion_estimate = 0
        qa_resource_depletion_estimate = 0
        # 查询已存版本数据
        ters = models.SprintEstimate.objects.filter(sprint_id=sprint_id).values_list('terminal')
        # 查询需求提测打回个数
        reject_story = len(TestPlanModel.objects.filter(sprint_id=sprint_id, stories__isnull=False,
                                                        reject_count__isnull=False).values('stories').distinct())
        # 迭代时间
        sprint = models.JiraSprint.objects.filter(id=sprint_id).values('start_date', 'end_date')
        if sprint[0].get('start_date') and sprint[0].get('end_date'):
            sprint_time = sprint[0].get('start_date').strftime('%Y%m%d') + '-' + sprint[0].get('end_date').strftime(
                '%Y%m%d')
            # 迭代工作日
            sprint_days = len(chinese_calendar.get_workdays(start=sprint[0].get('start_date'), end=sprint[0].get('end_date')))
        else:
            sprint_time = None
            sprint_days = 0
        # 除资源损耗与跟测的所有story
        nomal_story_query = Q(type='Story') & Q(sprint_id__contains=f"'{sprint_id}'") & ~Q(
            summary__contains="【跟测&回归】") & ~Q(summary__contains="【资源损耗】")
        nomal_stories = models.JiraIssue.objects.filter(nomal_story_query).values_list('key', flat=True)
        # 除资源损耗与跟测的所有子任务
        nomal_task_query = Q(type='Sub-task') & Q(parent_key__in=nomal_stories) & ~Q(resolution='不做了')
        nomal_sub_tasks = models.JiraIssue.objects.filter(nomal_task_query).values_list('key', flat=True)
        # 延期子任务
        delay_task_query = Q(type='Sub-task') & Q(parent_key__in=nomal_stories) & Q(resolution='Unresolved') & Q(
            target_end__lt=now_date)
        new_delay_tasks = JiraEpicSerializer(models.JiraIssue.objects.filter(delay_task_query), many=True).data
        new_delay_tasks = [task.get('key') for task in new_delay_tasks]
        old_delay_tasks = models.SprintEstimate.objects.filter(sprint_id=sprint_id, terminal='total').values_list('delay_tasks')
        if old_delay_tasks:
            old_delay_tasks = old_delay_tasks[0]
        new_delay_tasks.extend(old_delay_tasks)
        delay_tasks = list(set(new_delay_tasks))
        # 子任务延期率
        delay_rate = mode_number(len(delay_tasks), len(nomal_sub_tasks), 2)
        # 全部story
        stories = models.JiraIssue.objects.filter(type='Story', sprint_id__contains=f"'{sprint_id}'").values_list(
            'key', flat=True)
        # 当前迭代全部子任务
        task_query = Q(type='Sub-task') & Q(parent_key__in=stories) & ~Q(resolution='不做了')
        sub_tasks = models.JiraIssue.objects.filter(task_query).values_list('fix_version', flat=True)
        # 当前迭代涉及到的版本
        version_ids = list(set(["".join(filter(str.isdigit, sub_task)) for sub_task in sub_tasks]))
        versions = models.JiraFixVersions.objects.filter(id__in=version_ids)
        # 总技改story
        tech_stories = models.JiraIssue.objects.filter((~Q(summary__contains="【跟测&回归】") & ~Q(summary__contains="【资源损耗】")),
                                                       type='Story', sprint_id__contains=f"'{sprint_id}'",
                                                       epic_key__in=tech_epics).values_list('key', flat=True)
        # 总需求变更story
        change_stories = models.JiraIssue.objects.filter((~Q(summary__contains="【跟测&回归】") & ~Q(summary__contains="【资源损耗】")),
                                                         type='Story', sprint_id__contains=f"'{sprint_id}'",
                                                         epic_key__in=change_epics).values_list('key', flat=True)
        # 总业务story
        story_query = Q(type='Story') & Q(sprint_id__contains=f"'{sprint_id}'") & ~Q(
            epic_key__in=change_epics) & ~Q(epic_key__in=tech_epics) & ~Q(
            summary__contains="【跟测&回归】") & ~Q(summary__contains="【资源损耗】")
        business_stories = models.JiraIssue.objects.filter(story_query).values_list('key', flat=True)
        # 跟测&回归story
        regression_stories = models.JiraIssue.objects.filter(type='Story', sprint_id__contains=f"'{sprint_id}'",
                                                             summary__contains="【跟测&回归】").values_list('key', flat=True)
        # 资源损耗story
        resource_depletion_stories = models.JiraIssue.objects.filter(type='Story', sprint_id__contains=f"'{sprint_id}'",
                                                                     summary__contains="【资源损耗】").values_list(
            'key', flat=True)
        # 迭代下全部bug
        total_bug = models.JiraIssue.objects.filter(type='Bug', sprint_id__contains=f"[\'{sprint_id}\'",
                                                    resolution__in=task_resolution).values('key', 'fix_time')
        # bug的平均修复时长
        fix_time = sum([bug.get('fix_time') for bug in total_bug if bug.get('fix_time') or 0])
        avg_fix_time = mode_number(mode_number(fix_time, len(total_bug)), 3600)
        # 版本一样的聚合统计
        ver_dict = {}
        for version in versions:
            if 'UI' in version.name.upper() or 'PM' in version.name.upper():
                continue
            terminal = version.name.split('_')[0].upper() if '_' in version.name else version.name.split('-')[0].upper()
            if terminal in ver_dict.keys():
                ver_dict.get(terminal).append(version)
            else:
                ver_list = []
                ver_list.append(version)
                ver_dict.update({terminal: ver_list})
        ter_list = []
        # 该迭代属于QA的子任务
        qa_tasks = []
        for ter in ver_dict.keys():
            try:
                change_tasks = []
                tech_tasks = []
                business_tasks = []
                regression_tasks = []
                resource_depletion_tasks = []
                if ter in terminalSort:
                    terminal_name = JiraTerminalName.get_chinese(ter)
                else:
                    terminal_name = ter
                # 本次同步数据涉及的版本
                ter_list.append(terminal_name)
                for ver in ver_dict.get(ter):
                    baseQuery = Q(assignee__isnull=False) & Q(fix_version__contains=f"'{ver.id}'") & Q(
                        type='Sub-task') & ~Q(resolution='不做了')
                    # 总需求变更subtasks
                    change_tasks = change_tasks + JiraEpicSiri(models.JiraIssue.objects.filter(
                        baseQuery, parent_key__in=change_stories), many=True).data
                    # 总技改subtasks
                    tech_tasks = tech_tasks + JiraEpicSiri(
                        models.JiraIssue.objects.filter(baseQuery, parent_key__in=tech_stories), many=True).data
                    # 总需求subtasks
                    business_tasks = business_tasks + JiraEpicSiri(
                        models.JiraIssue.objects.filter(baseQuery, parent_key__in=business_stories), many=True).data
                    # 跟测回归需求subtasks
                    regression_tasks = regression_tasks + JiraEpicSiri(
                        models.JiraIssue.objects.filter(baseQuery, parent_key__in=regression_stories), many=True).data
                    # 资源损耗需求subtasks
                    resource_depletion_tasks = resource_depletion_tasks + JiraEpicSiri(
                        models.JiraIssue.objects.filter(baseQuery, parent_key__in=resource_depletion_stories), many=True).data
                # 投入人
                people_set = set([task.get("bugOwner") for task in tech_tasks] +
                                 [task.get("bugOwner") for task in business_tasks] +
                                 [task.get("bugOwner") for task in change_tasks] +
                                 [task.get("bugOwner") for task in regression_tasks] +
                                 [task.get("bugOwner") for task in resource_depletion_tasks])
                people = "(" + ",".join(people_set) + ")"
                # 投入人数
                people_count = len(people_set)
                # 投入工时
                tech_estimate = sum([task.get("original_time_estimate") for task in tech_tasks])
                change_estimate = sum([task.get("original_time_estimate") for task in change_tasks])
                business_estimate = sum([task.get("original_time_estimate") for task in business_tasks])
                regression_estimate = sum([task.get("original_time_estimate") for task in regression_tasks])
                resource_depletion_estimate = sum([task.get("original_time_estimate") for task in resource_depletion_tasks])
                if ter in terminalSort:
                    terminal_id = JiraTerminalId.get_chinese(ter)
                else:
                    terminal_id = 50
                # 总资源人天数
                sum_estimate = sum_estimate + (tech_estimate + business_estimate + change_estimate + regression_estimate
                                               + resource_depletion_estimate)
                # 需求变更总人天数
                sum_change_estimate = sum_change_estimate + change_estimate
                # 资源损耗总人天数
                sum_resource_depletion_estimate = sum_resource_depletion_estimate + resource_depletion_estimate
                # 测试总人天
                if ter == "QA" or ter == "qa":
                    qa_estimate = tech_estimate + business_estimate + change_estimate+ regression_estimate + \
                                  resource_depletion_estimate
                    qa_resource_depletion_estimate = resource_depletion_estimate
                    qa_tasks = business_tasks + change_tasks + tech_tasks
                else:
                    # 技改纯开发人天数
                    sum_tech_estimate = sum_tech_estimate + tech_estimate
                origin_data = models.SprintEstimate.query_first(sprint_id=sprint_id, terminal=terminal_name)
                if origin_data and origin_data.edited:
                    continue
                models.SprintEstimate.base_upsert({'sprint_id': sprint_id, 'terminal': terminal_name},
                                                  **{'sprint_id': sprint_id, 'terminal': terminal_name,
                                                     'edited': False, 'people_count': people_count,
                                                     'business_story_estimate': business_estimate,
                                                     'business_story_count': len(business_stories),
                                                     'tech_story_estimate': tech_estimate,
                                                     'change_story_estimate': change_estimate,
                                                     'tech_story_count': len(tech_stories),
                                                     'change_story_count': len(change_stories),
                                                     "regression_estimate": regression_estimate,
                                                     "resource_depletion_estimate": resource_depletion_estimate,
                                                     "sprint_time": sprint_time, "sprint_days": sprint_days,
                                                     'people': people, 'terminal_id': terminal_id})
            except Exception as e:
                print(e)
                continue
        # 延期需求(子任务里需排除QA的子任务)
        delay_story = get_delay_story(stories=nomal_stories, now_date=now_date, sprint_id=sprint_id,
                                      qa_tasks=qa_tasks)
        # 需求延期率
        delay_story_rate = mode_number(len(delay_story), len(nomal_stories), 2)
        if len(ver_dict):
            # 判断该迭代的项目描述有没有被前端编辑过，编辑过只同步数据，不同步mark
            total_origin_data = models.SprintEstimate.query_first(sprint_id=sprint_id, terminal="total")
            ter_list.append('total')
            if total_origin_data and total_origin_data.edited:
                models.SprintEstimate.base_upsert({'sprint_id': sprint_id, 'terminal': 'total'},
                                                  **{'sprint_id': sprint_id, 'terminal': 'total',
                                                     'edited': True, 'terminal_id': 100,
                                                     'sum_story_count': len(tech_stories) + len(
                                                         business_stories) + len(change_stories) + len(
                                                         regression_stories) + len(resource_depletion_stories),
                                                     'tech_story_count': len(tech_stories), 'delay_tasks': delay_tasks,
                                                     'delay_story': delay_story,
                                                     'change_story_count': len(change_stories)})
            else:
                mark = f'1、本次迭代共上线{len(tech_stories) + len(business_stories) + len(change_stories)}个需求，' \
                       f'其中技改需求{len(tech_stories)}个，需求变更/新增{len(change_stories)}个\n2、本次迭代共投入开发测试' \
                       f'资源{second_2_days(sum_estimate)}人日:\n  1)纯开发{second_2_days(sum_estimate - qa_estimate)}人天，' \
                       f'技改{second_2_days(sum_tech_estimate)}人天({round(mode_number(sum_tech_estimate, (sum_estimate - qa_estimate), 3) * 100, 2)}%)' \
                       f'\n  2)纯测试{second_2_days(qa_estimate)}人天\n  3)其中{len(change_stories)}次需求变更/新增，' \
                       f'共挤占{second_2_days(sum_change_estimate)}人日开发测试资源\n' \
                       f'3、资源损耗共计{second_2_days(sum_resource_depletion_estimate)}人日,' \
                       f'其中开发{second_2_days(sum_resource_depletion_estimate - qa_resource_depletion_estimate)}人日,' \
                       f'测试{second_2_days(qa_resource_depletion_estimate)}人日\n4、共{len(total_bug)}个' \
                       f'bug，bug平均修复时长为{avg_fix_time}h\n5、回顾会链接：\n6、本次迭代有{reject_story}个需求提测打回\n7、' \
                       f'本次迭代子任务延期率为{delay_rate},本次迭代需求延期率为{delay_story_rate}\n'
                models.SprintEstimate.base_upsert({'sprint_id': sprint_id, 'terminal': 'total'},
                                                  **{'sprint_id': sprint_id, 'terminal': 'total',
                                                     'edited': False, 'terminal_id': 100,
                                                     'sum_story_count': len(tech_stories) + len(
                                                         business_stories) + len(change_stories) + len(
                                                         regression_stories) + len(resource_depletion_stories),
                                                     'tech_story_count': len(tech_stories), 'delay_tasks': delay_tasks,
                                                     'delay_story': delay_story,
                                                     'change_story_count': len(change_stories), 'mark': mark})
        # 删除脏数据
        diff_ter = set(ters).difference(set(ter_list))
        if diff_ter:
            for diff in diff_ter:
                models.SprintEstimate.hard_delete(**{"sprint_id": sprint_id, "terminal": diff})



@app.task()
def sync_jira_basedata(days=60):
    logging.info('---------同步jira项目迭代等数据到测试平台task start-------------------------')
    _sync_project()
    _sync_boards()
    _sync_sprints()
    _sync_fixVersion()
    sync_jira_issue.apply_async(countdown=1, kwargs={'hours': 1, 'days': days})


@app.task()
def sync_jira_issue(hours=1, days=60):
    logging.info('--------------同步最近五分钟更新的jiraissue-----------------')
    # 删除已经删掉的任务
    latest_date = date_compile(-60*24*days)
    issue_ids = list(map(lambda x: int(x), list(models.JiraissueOrigin.objects.filter(updated__gte=latest_date).values_list('id', flat=True))))
    if issue_ids:
        deleted_issues = models.JiraIssue.objects.filter(updated__gte=latest_date).exclude(id__in=issue_ids).delete()
    # 捞出最近1小时有更新过的issue
    update_time = datetime.datetime.now() + timedelta(hours=-hours)
    updated_issues = list(map(lambda x: int(x), list(models.JiraissueOrigin.objects.filter(updated__gte=update_time).values_list('id', flat=True))))
    if not updated_issues:
        logging.info("No updated issues found.")
        return
    else:
        logging.info("Updated issues found.")
        logging.info(updated_issues)
    offset, max_result = 0, 500
    # jql = f'id in {tuple(updated_issues[offset: max_result])}'
    search_issues = []
    objs = []
    while len(search_issues) < len(updated_issues) and len(updated_issues[offset: offset+max_result]):
        jql = f'id in {tuple(updated_issues[offset: offset+max_result])}' if len(updated_issues[offset: offset+max_result]) > 1 else f'id={updated_issues[offset: offset+max_result][0]}'
        search_issues.extend(
            jiraTool.jiraClient.search_issues(jql_str=jql, maxResults=max_result, expand='changelog'))
        offset += max_result
    # 计算任务的解决时长、关闭时长
    for issue in search_issues:
        fix_time, close_time, reopen_count = None, None, 0
        created = timestrToDatetime(issue.fields.created)
        if issue.fields.issuetype.name == JiraIssueType.BUG.value:
            for change in issue.changelog.histories:
                change_time = timestrToDatetime(change.created)
                for item in change.items:
                    if item.field == 'status' and item.toString == 'Fixed':
                        if fix_time:
                            reopen_count += 1
                        fix_time = int((change_time - created).total_seconds())
                    elif item.field == 'status' and item.toString == 'Closed':
                        close_time = int((change_time - created).total_seconds() - fix_time if fix_time else (
                                change_time - created).total_seconds())
        try:
            assignee = issue.fields.assignee.name if issue.fields.assignee else None
            objs.append(models.JiraIssue(id=issue.id, key=issue.key,
                                         type=JiraIssueType.get_chinese(issue.fields.issuetype.name),
                                         proj_id=issue.fields.project.id,
                                         proj_key=issue.fields.project.key,
                                         resolution=issue.fields.resolution.name if issue.fields.resolution else 'Unresolved',
                                         resolution_date=timestrToDatetime(
                                             issue.fields.resolutiondate) if issue.fields.resolutiondate else None,
                                         priority=issue.fields.priority if JiraIssueType.get_chinese(
                                             issue.fields.issuetype.name) == '故事' else None,
                                         assignee=assignee,
                                         created=created,
                                         updated=timestrToDatetime(issue.fields.updated),
                                         status=JiraIssueStatus.get_chinese(issue.fields.status.name),
                                         summary=issue.fields.customfield_10102 if issue.fields.issuetype.name == 'Epic' else issue.fields.summary,
                                         description=issue.fields.description,
                                         creator=issue.fields.creator.name,
                                         original_time_estimate=issue.fields.timeoriginalestimate or 0,
                                         bugOwner=issue.fields.customfield_10108.name if hasattr(issue.fields,
                                                                                                 'customfield_10108') and hasattr(
                                             issue.fields.customfield_10108, 'name') else assignee,
                                         env=issue.fields.customfield_10110.value if issue.fields.issuetype.name == '故障' and issue.fields.customfield_10110 else None,
                                         platform=issue.fields.customfield_10111.value if issue.fields.issuetype.name == '故障' and issue.fields.customfield_10111 else None,
                                         bug_level=issue.fields.customfield_10107.value if issue.fields.issuetype.name == '故障' and issue.fields.customfield_10107 else None,
                                         sub_bug_level=issue.fields.customfield_10107.child.value if issue.fields.issuetype.name == '故障' and hasattr(
                                             issue.fields.customfield_10107, 'child') else None,
                                         fix_version=str([version.id for version in issue.fields.fixVersions or []]),
                                         # target_start=datestrToDate(issue.fields.customfield_10205),
                                         # target_end=datestrToDate(issue.fields.customfield_10206),
                                         issue_links=str(
                                             [{"link_id": link.id, "link_type": link.type.name} for link in
                                              issue.fields.issuelinks or []]),
                                         sprint_id=str(
                                             [re.sub(r'\D', '', re.search(r'id=\d+', sprint).group()) for sprint in
                                              issue.fields.customfield_10104 or []]),
                                         epic_key=issue.fields.customfield_10100,
                                         parent_key=issue.fields.parent.key if hasattr(issue.fields,
                                                                                       'parent') else None,
                                         fix_time=fix_time,
                                         close_time=close_time,
                                         reopen_count=reopen_count))

        except Exception as e:
            logging.error(f"同步JiraissueOrigin和JiraIssue数据时发生错误: {str(e)}")
            logging.error(f'{issue.id}: {e}')
            continue
    try:
        with transaction.atomic():
            models.JiraIssue.objects.filter(id__in=updated_issues).delete()
            models.JiraIssue.objects.bulk_create(objs, batch_size=2000)
    except Exception as e:
        raise e
    # 更新project_key, parent_key
    jira_projs = models.Project.objects.all()
    bulk_updates = []
    query = Q(epic_key__isnull=False)
    for proj in jira_projs:
        query &= ~Q(epic_key__startswith=f'{proj.pkey}-')
        if proj.pkey != proj.originalkey:
            issues = models.JiraIssue.objects.filter(proj_id=proj.id).exclude(proj_key=proj.pkey)
            for issue in issues:
                bulk_updates.append(models.JiraIssue(id=issue.id, key=f"{proj.pkey}-{issue.key.split('-')[-1]}",
                                                     proj_key=proj.pkey, parent_key=f"{proj.pkey}-{issue.parent_key.split('-')[-1]}" if issue.parent_key else None))
    models.JiraIssue.objects.bulk_update(bulk_updates, ['key', 'proj_key', 'parent_key'], batch_size=2000)
    # 如果proj_key被改,更新epic_key
    issues = list(map(lambda x: int(x), list(models.JiraIssue.objects.filter(query).values_list('id', flat=True))))
    if len(issues):
        offset, max_result = 0, 500
        search_issues = []
        objs = []
        while len(search_issues) < len(issues) and issues[offset: offset+max_result]:
            jql = f'id in {tuple(issues[offset: offset+max_result])}' if len(issues[offset: offset+max_result]) > 1 else f'id={issues[offset: offset+max_result][0]}'
            search_issues.extend(
                jiraTool.jiraClient.search_issues(jql_str=jql, maxResults=max_result, expand='changelog'))
            offset += max_result
        for issue in search_issues:
            objs.append(models.JiraIssue(id=issue.id, epic_key=issue.fields.customfield_10100))
        models.JiraIssue.objects.bulk_update(objs, ['epic_key'], batch_size=2000)
# def sync_jira_issue(hours=1, days=60):
#     logging.info('--------------同步最近五分钟更新的jiraissue-----------------')
#
#     # 删除已经删掉的任务
#     latest_date = datetime.now() - timedelta(days=days)
#     issue_ids = list(models.JiraissueOrigin.objects.filter(updated__gte=latest_date).values_list('id', flat=True))
#     models.JiraIssue.objects.filter(updated__gte=latest_date).exclude(id__in=issue_ids).delete()
#
#     # 捞出最近1小时有更新过的issue
#     update_time = datetime.now() - timedelta(hours=hours)
#     updated_issues = list(models.JiraissueOrigin.objects.filter(updated__gte=update_time).values_list('id', flat=True))
#     if not updated_issues:
#         return
#
#     offset, max_result = 0, 500
#     search_issues = []
#     objs = []
#     while len(search_issues) < len(updated_issues) and len(updated_issues[offset: offset + max_result]):
#         # 修改了jql的生成方式，使用参数化查询来避免潜在的SQL注入问题
#         jql = "id in %s" if len(updated_issues[offset: offset + max_result]) > 1 else "id = %s"
#         search_issues.extend(
#             jiraTool.jiraClient.search_issues(jql_str=jql, params=(tuple(updated_issues[offset: offset + max_result]),),
#                                               maxResults=max_result, expand='changelog'))
#         offset += max_result
#
#     # 计算任务的解决时长、关闭时长
#     for issue in search_issues:
#         fix_time, close_time, reopen_count = None, None, 0
#         created = timestrToDatetime(issue.fields.created)
#         if issue.fields.issuetype.name == JiraIssueType.BUG.value:
#             for change in issue.changelog.histories:
#                 change_time = timestrToDatetime(change.created)
#                 for item in change.items:
#                     if item.field == 'status' and item.toString == 'Fixed':
#                         if fix_time:
#                             reopen_count += 1
#                         fix_time = int((change_time - created).total_seconds())
#                     elif item.field == 'status' and item.toString == 'Closed':
#                         close_time = int((change_time - created).total_seconds() - fix_time if fix_time else (
#                                     change_time - created).total_seconds())
#
#         try:
#             assignee = issue.fields.assignee.name if issue.fields.assignee else None
#             objs.append(models.JiraIssue(
#                 id=issue.id,
#                 key=issue.key,
#                 type=JiraIssueType.get_chinese(issue.fields.issuetype.name),
#                 proj_id=issue.fields.project.id,
#                 proj_key=issue.fields.project.key,
#                 resolution=issue.fields.resolution.name if issue.fields.resolution else 'Unresolved',
#                 resolution_date=timestrToDatetime(issue.fields.resolutiondate) if issue.fields.resolutiondate else None,
#                 priority=issue.fields.priority if JiraIssueType.get_chinese(
#                     issue.fields.issuetype.name) == '故事' else None,
#                 assignee=assignee,
#                 created=created,
#                 updated=timestrToDatetime(issue.fields.updated),
#                 status=JiraIssueStatus.get_chinese(issue.fields.status.name),
#                 summary=issue.fields.customfield_10102 if issue.fields.issuetype.name == 'Epic' else issue.fields.summary,
#                 description=issue.fields.description,
#                 creator=issue.fields.creator.name,
#                 original_time_estimate=issue.fields.timeoriginalestimate or 0,
#                 bugOwner=issue.fields.customfield_10108.name if hasattr(issue.fields, 'customfield_10108') and hasattr(
#                     issue.fields.customfield_10108, 'name') else assignee,
#                 env=issue.fields.customfield_10110.value if issue.fields.issuetype.name == '故障' and issue.fields.customfield_10110 else None,
#                 platform=issue.fields.customfield_10111.value if issue.fields.issuetype.name == '故障' and issue.fields.customfield_10111 else None,
#                 bug_level=issue.fields.customfield_10107.value if issue.fields.issuetype.name == '故障' and issue.fields.customfield_10107 else None,
#                 sub_bug_level=issue.fields.customfield_10107.child.value if issue.fields.issuetype.name == '故障' and hasattr(
#                     issue.fields.customfield_10107, 'child') else None,
#                 fix_version=str([version.id for version in issue.fields.fixVersions or []]),
#                 target_start=datestrToDate(issue.fields.customfield_10205),
#                 target_end=datestrToDate(issue.fields.customfield_10206),
#                 issue_links=str(
#                     [{"link_id": link.id, "link_type": link.type.name} for link in issue.fields.issuelinks or []]),
#                 sprint_id=str([re.sub(r'\D', '', re.search(r'id=\d+', sprint).group()) for sprint in
#                                issue.fields.customfield_10104 or []]),
#                 epic_key=issue.fields.customfield_10100,
#                 parent_key=issue.fields.parent.key if hasattr(issue.fields, 'parent') else None,
#                 fix_time=fix_time,
#                 close_time=close_time,
#                 reopen_count=reopen_count
#             ))
#         except Exception as e:
#             logging.error(f"同步JiraissueOrigin和JiraIssue数据时发生错误: {str(e)}")
#             continue
#
#     try:
#         with transaction.atomic():
#             # 使用批量删除和批量创建来提高性能
#             models.JiraIssue.objects.filter(id__in=updated_issues).delete()
#             models.JiraIssue.objects.bulk_create(objs, batch_size=2000)
#     except Exception as e:
#         raise e
#
#     # 更新project_key, parent_key
#     jira_projs = models.Project.objects.all()
#     bulk_updates = []
#     query = Q(epic_key__isnull=False)
#
#     for proj in jira_projs:
#         query &= ~Q(epic_key__startswith=f'{proj.pkey}-')
#         if proj.pkey != proj.originalkey:
#             issues = models.JiraIssue.objects.filter(proj_id=proj.id).exclude(proj_key=proj.pkey)
#             for issue in issues:
#                 bulk_updates.append(models.JiraIssue(
#                     id=issue.id,
#                     key=f"{proj.pkey}-{issue.key.split('-')[-1]}",
#                     proj_key=proj.pkey,
#                     parent_key=f"{proj.pkey}-{issue.parent_key.split('-')[-1]}" if issue.parent_key else None
#                 ))
#
#     models.JiraIssue.objects.bulk_update(bulk_updates, ['key', 'proj_key', 'parent_key'], batch_size=2000)
#
#     # 如果proj_key被改,更新epic_key
#     issues = list(models.JiraIssue.objects.filter(query).values_list('id', flat=True))
#     if len(issues):
#         offset, max_result = 0, 500
#         search_issues = []
#         objs = []
#         while len(search_issues) < len(issues) and issues[offset: offset + max_result]:
#             jql = "id in %s" if len(issues[offset: offset + max_result]) > 1 else "id = %s"
#             search_issues.extend(
#                 jiraTool.jiraClient.search_issues(jql_str=jql, params=(tuple(issues[offset: offset + max_result]),),
#                                                   maxResults=max_result, expand='changelog'))
#             offset += max_result
#
#         for issue in search_issues:
#             objs.append(models.JiraIssue(id=issue.id, epic_key=issue.fields.customfield_10100))
#
#         models.JiraIssue.objects.bulk_update(objs, ['epic_key'], batch_size=2000)


@app.task()
def create_project_cycle():
    logging.info('---------计算项目交付周期task start-------------------------')
    # 列出所有项目
    projects = JiraProjectSerializer(models.JiraProject.objects.filter(), many=True).data
    for project in projects:
        cycle_dict = {}
        story_sum = 0
        story_num = 0
        sprint_num = 0
        sprint_sum = 0
        # 半年内的sprint
        query_sprint = Q(start_date__gte=get_date_any(n=-180), start_date__lte=get_date_any()) & ~Q(
            complete_date=None)
        sprint_arr = JiraSprintSerializer(models.JiraSprint.objects.filter(query_sprint, proj_id=project['id']),
                                          many=True).data
        if sprint_arr:
            for spr in sprint_arr:
                spr_story = JiraEpicSiri(models.JiraIssue.objects.filter(sprint_id__contains=f"\'{spr['id']}\']",
                                                                         type=JiraIssueType.STORY.chinese),
                                         many=True).data
                if spr_story:
                    complete_dt = spr['complete_date']
                    start_dt = spr['start_date']
                    sprint_num = sprint_num + 1
                    if complete_dt == start_dt:
                        dt_cycle = 1
                    else:
                        spr_cycle = parser.parse(complete_dt) - parser.parse(start_dt)
                        dt_cycle = str(spr_cycle).split(" ")[0]
                    sprint_sum = sprint_sum + (int(dt_cycle))
            if sprint_num != 0:
                develop_avg = round(sprint_sum / sprint_num, 2)
                cycle_dict.update({"develop_cycle": develop_avg})
        # 半年内已分配sprint的story
        base_qurey = Q(created__gte=get_date_any(n=-180), created__lte=get_date_any()) & ~Q(sprint_id='[]')
        story_arr = JiraEpicSiri(
            models.JiraIssue.objects.filter(base_qurey, proj_id=project['id'], type=JiraIssueType.STORY.chinese),
            many=True).data
        if story_arr:
            for story_sprint in story_arr:
                # 最新关联的sprint
                id = eval(story_sprint['sprint_id'])[-1]
                # 已完成的sprint
                sprint_query = Q(id=id) & ~Q(complete_date=None)
                sprint = JiraSprintSerializer(models.JiraSprint.objects.filter(sprint_query), many=True).data
                if sprint:
                    complete_date = sprint[0]['complete_date']
                    create_date = story_sprint['created'].split(" ")[0]
                    story_num = story_num + 1
                    if complete_date == create_date:
                        date_cycle = 1
                    else:
                        cycle = parser.parse(complete_date) - parser.parse(create_date)
                        date_cycle = str(cycle).split(" ")[0]
                    story_sum = story_sum + (int(date_cycle))
            if story_num != 0:
                delivery_avg = round(story_sum / story_num, 2)
                cycle_dict.update({"delivery_cycle": delivery_avg})
        if cycle_dict:
            cycle_dict.update({"project_id": project['id'], "project_name": project['name'],
                               "start_date": get_date_any(n=-180), "end_date": get_date_any()})
            models.JiraBusinessCycle.objects.create(**cycle_dict)


@app.task()
def create_month_resource_report():
    """同步技术部月度资源"""
    logging.info('---------同步技术部下部门月度资源等数据到测试平台task start-------------------------')
    month_str = datetime.datetime.now().strftime("%Y-%m")
    month = month_str.split('-')
    days = get_three_month_start_end(int(month[0]), int(month[1]))
    all_users = get_department_users()
    work_days = chinese_calendar.get_workdays(start=days["current_month_first_day"],
                                              end=days["current_month_last_day"])
    # 查询已存在的组织部门
    departs = models.DepartmentEstimate.objects.filter(month=month_str).values_list('depart_name')
    depart_list = []
    for users in all_users:
        pre_days = []
        current_days = []
        next_days = []
        for user in users['jira_users']:
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
            pre_datas = models.JiraIssue.objects.filter(pre_task_query).values('target_start', 'target_end', 'original_time_estimate')
            pre_work_days = 0
            for pre_data in pre_datas:
                pre_work_day = chinese_calendar.get_workdays(start=days['current_month_first_day'],
                                                             end=pre_data.get('target_end'))
                all_pre_work_day = chinese_calendar.get_workdays(start=pre_data.get('target_start'),
                                                                 end=pre_data.get('target_end'))
                # 按本月占所有时间的比例乘上估时
                pre_estimate = round(len(pre_work_day) / len(all_pre_work_day), 6) * pre_data.get(
                    'original_time_estimate')
                pre_work_days = pre_work_days + pre_estimate
            pre_days.append(pre_work_days)
            # 本月开始，本月完成的数据
            current_datas = models.JiraIssue.objects.filter(current_task_query).values('target_start', 'target_end', 'original_time_estimate')
            current_work_days = 0
            for current_data in current_datas:
                current_work_days = current_work_days + current_data.get('original_time_estimate')
            current_days.append(current_work_days)
            # 本月开始，下月完成的数据
            next_datas = models.JiraIssue.objects.filter(next_task_query).values('target_start', 'target_end', 'original_time_estimate')
            next_work_days = 0
            for next_data in next_datas:
                next_work_day = chinese_calendar.get_workdays(start=next_data.get('target_start'),
                                                              end=days['current_month_last_day'])
                all_next_work_day = chinese_calendar.get_workdays(start=next_data.get('target_start'),
                                                                  end=next_data.get('target_end'))
                next_estimate = round(len(next_work_day) / len(all_next_work_day), 6) * next_data.get(
                    'original_time_estimate')
                next_work_days = next_work_days + next_estimate
            next_days.append(next_work_days)
        pre_department_days = second_2_days(sum(pre_days))
        current_department_days = second_2_days(sum(current_days))
        next_department_days = second_2_days(sum(next_days))
        if users['jira_users']:
            depart_list.append(users['depart_name'])
            total_working_days = len(users['jira_users']) * len(work_days)
            target_days_diff = round(total_working_days - (
                    pre_department_days + current_department_days + next_department_days), 3)
            productivity = round((total_working_days - target_days_diff) / total_working_days, 2)
            models.DepartmentEstimate.base_upsert({'depart_name': users['depart_name'], 'month': month_str},
                                                  **{"depart_name": users['depart_name'], "leader": users['leader'],
                                                     "people_count": len(users['jira_users']),
                                                     "work_days": len(work_days),
                                                     "total_working_days": total_working_days, "edited": False,
                                                     "target_days_diff": target_days_diff,
                                                     "pre_department_days": pre_department_days,
                                                     "current_department_days": current_department_days,
                                                     "next_department_days": next_department_days,
                                                     "productivity": productivity})
    diff_depart = set(departs).difference(set(depart_list))
    if diff_depart:
        for diff in diff_depart:
            models.DepartmentEstimate.hard_delete(**{"depart_name": diff, "month": month_str})


@app.task()
def deactive_jira_user_by_ace():
    """根据ace的离职信息修改用户的jira信息"""
    logging.info('---------根据ace的离职信息修改用户的jira信息和密码task-------------------------')
    base_deactive_at = datetime.date(1970, 1, 2)
    now_date = datetime.datetime.now()
    deactive_user_query = Q(deactivated_at__gt=base_deactive_at, deactivated_at__lt=now_date)
    try:
        deactive_accounts = AceAccount.objects.filter(deactive_user_query)
        logging.info('离职人员数量%s', len(deactive_accounts))

        # logging.info('-------离职用户数大于20，先定位是否数据出现bug---------')
        for deactive_account in deactive_accounts:
            logging.info('离职人员姓名%s，邮箱%s', deactive_account.name, deactive_account.email)
            jira_account_query_set = models.CwdUser.objects.filter(email_address=deactive_account.email)
            if jira_account_query_set.count() > 0:
                logging.info(jira_account_query_set)
                jira_account = jira_account_query_set.values('user_name')[0].get('user_name')
                logging.info(jira_account)
                url = "http://jira.jiliguala.com/rest/api/2/user?username=" + jira_account
                headers = {"Authorization": "Basic YWNlX2JvdDpBZG1pbiFAIyQ=",
                           "Cookie": "JSESSIONID=F90C9F9A2A37CB58C5194D39D4EE0840; atlassian.xsrf.token=BH52-J78S-VUZG-WD5P_de3a018fcb2391f13c1000edfca38bacdab85f08_lin"}
                response = requests.delete(url, headers=headers)
                status_code = response.status_code
                if status_code == 204:
                    logging.info('离职人员删除成功%s', jira_account)
                else:
                    logging.info('删除失败姓名%s, 响应码%s',jira_account , status_code)
    except Exception:
        traceback.print_exc()


@app.task()
def push_delay_task(days=-7):
    """推送延期任务与当前需完成任务给经办人"""
    logging.info('---------推送延期任务与当前需完成任务给经办人-------------------------')
    early_dt = get_date_any(days)
    now_date = datetime.datetime.now()
    now_dt = datetime.date(now_date.year, now_date.month, now_date.day)
    try:
        # 延期子任务
        delay_query = Q(target_end__gte=early_dt) & Q(target_end__lt=now_dt) & Q(type="Sub-task") & Q(
            resolution="Unresolved") & Q(assignee__isnull=False)
        delay_tasks = models.JiraIssue.objects.filter(delay_query).values('assignee', 'key', 'summary').order_by('assignee')
        assignee_delay_tasks = [{'assignee': key, 'del_tasks': list(task_groups)} for key, task_groups in
                          groupby(JiraDelayTaskGroup(delay_tasks, many=True).data, itemgetter('assignee'))]
        # 今日需完成子任务
        current_query = Q(target_end=now_dt) & Q(type="Sub-task") & Q(resolution="Unresolved") & Q(
            assignee__isnull=False)
        current_tasks = models.JiraIssue.objects.filter(current_query).values('assignee', 'key', 'summary').order_by(
            'assignee')
        assignee_current_tasks = [{'assignee': key, 'cur_tasks': list(task_groups)} for key, task_groups in
                                  groupby(JiraDelayTaskGroup(current_tasks, many=True).data, itemgetter('assignee'))]
        delay_keys = [a['assignee'] for a in assignee_delay_tasks]
        cur_keys = [c['assignee'] for c in assignee_current_tasks]
        keys = set(delay_keys + cur_keys)
        # 合并通知的延期子任务与今日需完成子任务
        for k in keys:
            open_id = ''
            del_content = ''
            cur_content = ''
            project_key = ''
            rapid_view = ''
            for assignee_task in assignee_delay_tasks:
                if assignee_task['assignee'] == k:
                    for task in assignee_task['del_tasks']:
                        del_content = del_content + f"\n{task['key']}--{task['summary']}"
                        project_key = task['key'].split('-')[0]
                        open_id = task['open_id']
                    continue
            for cur in assignee_current_tasks:
                if cur['assignee'] == k:
                    for task in cur['cur_tasks']:
                        cur_content = cur_content + f"\n{task['key']}--{task['summary']}"
                        project_key = task['key'].split('-')[0]
                        open_id = task['open_id']
                    continue
            if project_key:
                rapid = models.JiraBoards.objects.filter(proj_key=project_key,
                                                         name__contains='需求').values('id')
                if not rapid:
                    rapid = models.JiraBoards.objects.filter(proj_key=project_key).values('id')
                if rapid:
                    rapid_view = rapid[0].get('id')
            ace_notify(open_id=open_id, proj_key=project_key, rapid_view=rapid_view,
                       content=del_content, cur_content=cur_content)
    except Exception:
        traceback.print_exc()


def ace_notify(open_id, proj_key, rapid_view, content=None, cur_content=None):
    """机器人通知各经办人延期任务"""
    if not content:
        body = {
            "event": {
                "type": "interactive",
                "card": {
                    "config": {
                        "wide_screen_mode": True,
                        "enable_forward": True,
                    },
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"**Jira任务提醒**"
                        },
                        "template": "red"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"您有以下Jira任务需关注，请查收！"
                            },
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**今日需完成子任务:**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"{cur_content}"
                                    }
                            }]
                        },
                        {
                            "tag": "action",
                            "actions": [
                                {
                                    "tag": "button",
                                    "text": {
                                        "tag": "plain_text",
                                        "content": "jira链接"
                                    },
                                    "URL": f"http://jira.jiliguala.com/secure/RapidBoard.jspa?rapidView={rapid_view}&projectKey={proj_key}",
                                    "type": "default"
                                }
                            ]
                        }
                    ]
                },
                "open_id": open_id
            },
            "uuid": shortuuid.uuid(),
            "token": "zero_jiliguala"
        }
    elif not cur_content:
        body = {
            "event": {
                "type": "interactive",
                "card": {
                    "config": {
                        "wide_screen_mode": True,
                        "enable_forward": True,
                    },
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"**Jira任务提醒**"
                        },
                        "template": "red"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"您有以下Jira任务需关注，请查收！"
                            },
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**延期子任务:**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"{content}"
                                    }
                            }]
                        },
                        {
                            "tag": "action",
                            "actions": [
                                {
                                    "tag": "button",
                                    "text": {
                                        "tag": "plain_text",
                                        "content": "jira链接"
                                    },
                                    "URL": f"http://jira.jiliguala.com/secure/RapidBoard.jspa?rapidView={rapid_view}&projectKey={proj_key}",
                                    "type": "default"
                                }
                            ]
                        }
                    ]
                },
                "open_id": open_id
            },
            "uuid": shortuuid.uuid(),
            "token": "zero_jiliguala"
        }
    else:
        body = {
            "event": {
                "type": "interactive",
                "card": {
                    "config": {
                        "wide_screen_mode": True,
                        "enable_forward": True,
                    },
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"**Jira任务提醒**"
                        },
                        "template": "red"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"您有以下Jira任务需关注，请查收！"
                            },
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**延期子任务:**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"{content}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**今日需完成子任务:**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"{cur_content}"
                                    }
                            }]
                        },
                        {
                            "tag": "action",
                            "actions": [
                                {
                                    "tag": "button",
                                    "text": {
                                        "tag": "plain_text",
                                        "content": "jira链接"
                                    },
                                    "URL": f"http://jira.jiliguala.com/secure/RapidBoard.jspa?rapidView={rapid_view}&projectKey={proj_key}",
                                    "type": "default"
                                }
                            ]
                        }
                    ]
                },
                "open_id": open_id
            },
            "uuid": shortuuid.uuid(),
            "token": "zero_jiliguala"
        }
    try:
        res = requests.post('https://ace.jiliguala.com/endpoints/lark/', json=body,
                            headers={'Content-Type': 'application/json'}, verify=False)
        res.raise_for_status()
    except Exception as e:
        raise e