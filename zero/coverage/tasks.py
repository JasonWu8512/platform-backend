# -*- coding: utf-8 -*-
# @Time    : 2021/2/25 5:21 下午
# @Author  : zoey
# @File    : tasks.py
# @Software: PyCharm
import datetime
import json
import re
import time

import requests
import shortuuid

import socket
import os

from zero.celery import app
from zero.coverage.commands import jenkinsTool, JenkinsTaskStatus
from zero.settings import BASE_COVER_URL
from zero.coverage.models import CoveragePipeline, CoverageServerDeployHistory, FullCoverage, DiffCoverage, GitProject, \
    JenkinsProjectCommit, JenkinsBuildTask
from django.contrib.auth import get_user_model
from zero.organization.models import AceAccount
from zero.utils.format import mode_number
from django.db import transaction
from retry import retry
from jenkinsapi.custom_exceptions import (
    NotFound, UnknownJob
)
import logging

UserModel = get_user_model()


@app.task()
def recovery_deploy_server():
    logging.info('------------更新jenkins任务状态-----------')
    historys = CoverageServerDeployHistory.objects.filter(status=JenkinsTaskStatus.RUNNING.value,
                                                          build_id__isnull=False)
    coverage_historys = JenkinsBuildTask.objects.filter(build_status=JenkinsTaskStatus.RUNNING.value,
                                                        build_number__isnull=False)
    for history in historys:
        try:
            pipeline = CoveragePipeline.objects.filter(id=history.pipeline_id)
            pipe = pipeline.first()
            mark = json.loads(pipe.mark)
            result = jenkinsTool.get_job_build_result(history.job_name, history.build_id)
            if result == JenkinsTaskStatus.FAIL.value:
                mark['deploy'] = 'jenkins 构建失败，请查看日志'
        except NotFound as e:
            result = JenkinsTaskStatus.FAIL.value
            mark['deploy'] = e.args[0] if e.args else 'jenkins构建触发失败'
            if history.recover_times < 30:
                result = JenkinsTaskStatus.RUNNING.value
                mark['deploy'] = ''
                CoverageServerDeployHistory.objects.filter(id=history.id).update(
                    recover_times=history.recover_times + 1, updated_at=datetime.datetime.now())
        except Exception as e:
            result = JenkinsTaskStatus.FAIL.value
            mark['deploy'] = e.args[0] if e.args else 'jenkins构建触发失败'
            logging.error(f'获取{history.job_name}执行结果失败：{e}')
        finally:
            if result != JenkinsTaskStatus.RUNNING.value:
                pipeline.update(deploy_status=result, mark=json.dumps(mark))
                CoverageServerDeployHistory.objects.filter(id=history.id).update(status=result,
                                                                                 updated_at=datetime.datetime.now())
                try:
                    notify_chat_ids = pipe.notify_chat_ids.split(',') if pipe.notify_chat_ids else []
                    user = UserModel.objects.get(username=history.username)
                    open_id = AceAccount.objects.get(email=user.email).lark_open_id
                    ace_larkhooks(open_id=open_id, pipeline_name=pipe.name, pipeline_id=pipe.id, step=pipe.step1,
                                  commit_id=history.commit_id,
                                  status=result, chat_ids=notify_chat_ids)
                except Exception as e:
                    logging.error(f"流水线执行结果通知异常: {e}")
    # 更新状态为正在执行的覆盖率收集状态
    for history in coverage_historys:
        try:
            pipeline = CoveragePipeline.objects.filter(id=history.pipeline_id)
            pipe = pipeline.first()
            mark = json.loads(pipe.mark)
            result = jenkinsTool.get_job_build_result(history.coverage_job_name, history.build_number)
            if result == JenkinsTaskStatus.FAIL.value:
                mark['coverage'] = 'jenkins 构建失败，请查看日志'
        except NotFound as e:
            result = JenkinsTaskStatus.FAIL.value
            mark['coverage'] = e.args[0] if e.args else 'jenkins构建触发失败'
            if history.recover_times < 30:
                result = JenkinsTaskStatus.RUNNING.value
                mark['coverage'] = ''
                JenkinsBuildTask.objects.filter(id=history.id).update(
                    recover_times=history.recover_times + 1, updated_at=datetime.datetime.now())
        except Exception as e:
            result = JenkinsTaskStatus.FAIL.value
            mark['coverage'] = e.args[0] if e.args else 'jenkins构建触发失败'
        finally:
            if result != JenkinsTaskStatus.RUNNING.value:
                pipeline.update(coverage_status=result, mark=json.dumps(mark))
                JenkinsBuildTask.objects.filter(id=history.id).update(build_status=result,
                                                                      diff_coverage_report=f'http://qacover.jlgltech.com/{history.id}/diff-report.html',
                                                                      full_coverage_report=f'http://qacover.jlgltech.com/{history.id}/Check_Order_related/index.html')
                write_coverage_data_2_db.apply_async(kwargs={'coverage_id': history.id,
                                                             'project_id': pipe.project_id,
                                                             'project_name': history.project_git.split('/')[-1][:-4]},
                                                     countdown=1)
                try:
                    notify_chat_ids = pipe.notify_chat_ids.split(',') if pipe.notify_chat_ids else []
                    user = UserModel.objects.get(username=history.username)
                    open_id = AceAccount.objects.get(email=user.email).lark_open_id
                    ace_larkhooks(open_id=open_id, pipeline_name=pipe.name, pipeline_id=pipe.id, step=pipe.step2,
                                  status=result, chat_ids=notify_chat_ids, commit_id=history.end_commit)
                except Exception as e:
                    logging.error(f"流水线执行结果通知异常: {e}")
    sonar_historys = CoveragePipeline.objects.filter(sonar_status=JenkinsTaskStatus.RUNNING.value)
    for history in sonar_historys:
        try:
            result = jenkinsTool.get_job_build_result(history.sonar_job, history.sonar_id)
        except NotFound:
            result = JenkinsTaskStatus.FAIL.value
            if history.recover_times < 30:
                result = JenkinsTaskStatus.RUNNING.value
                CoveragePipeline.objects.filter(id=history.id).update(recover_times=history.recover_times + 1)
        except Exception as e:
            result = JenkinsTaskStatus.FAIL.value
        finally:
            CoveragePipeline.objects.filter(id=history.id).update(sonar_status=result)


@app.task(time_limit=10)
def trigger_deploy_job():
    """查询状态为pending且关联流水线的覆盖率收集状态不为running的deploy job并触发jenkins执行"""
    not_running_pipelines = CoveragePipeline.objects.exclude(
        coverage_status=JenkinsTaskStatus.RUNNING.value).values_list('id', flat=True)
    histories = CoverageServerDeployHistory.objects.filter(status=JenkinsTaskStatus.PENDING.value,
                                                           pipeline_id__in=not_running_pipelines)
    for history in histories:
        try:
            pipeline = CoveragePipeline.objects.get(id=history.pipeline_id)
            mark = json.loads(pipeline.mark)
            build_number = jenkinsTool.get_build_number(history.job_name)
            pipeline.deploy_id = build_number
            pipeline.save()
            result = jenkinsTool.build_job(job_name=history.job_name, params={'CommitID': history.commit_id})
        except UnknownJob as e:
            pipeline.deploy_status = JenkinsTaskStatus.FAIL.value
            mark['deploy'] = e.args[0] if e.args else '服务发版失败，请到jenkins查看发版日志'
            pipeline.mark = json.dumps(mark)
            pipeline.save()
            CoverageServerDeployHistory.objects.filter(id=history.id).update(status=JenkinsTaskStatus.FAIL.value)
            logging.error(e)
            continue
        except Exception as e:
            logging.error(f'服务端发版异步任务执行失败{e}')
            result = JenkinsTaskStatus.FAIL.value
            mark['deploy'] = e.args[0] if e.args else '服务发版失败，请到jenkins查看发版日志'
        finally:
            pipeline.deploy_status = result
            pipeline.mark = json.dumps(mark)
            pipeline.save()
            CoverageServerDeployHistory.objects.filter(id=history.id).update(status=result, build_id=build_number)
            if result == JenkinsTaskStatus.FAIL.value:
                user = UserModel.objects.get(username=history.username)
                open_id = AceAccount.objects.get(email=user.email).lark_open_id
                notify_chat_ids = pipeline.notify_chat_ids.split(',') if pipeline.notify_chat_ids else []
                ace_larkhooks(open_id=open_id, pipeline_name=pipeline.name, pipeline_id=pipeline.id,
                              step=pipeline.step1,
                              status=result, chat_ids=notify_chat_ids, commit_id=history.commit_id)


@app.task()
# def trigger_coverage_job(task_id, project_id, open_id):
#     '''执行jenkins 覆盖率收集job'''
#     logging.info(
#         f'--------------------开始执行覆盖率报告生成{task_id} {project_id} {open_id}---------------------------------')
#     try:
#         job = JenkinsBuildTask.objects.get(id=task_id)
#         query = CoveragePipeline.objects.filter(id=job.pipeline_id)
#         pipeline = query.first()
#         mark = json.loads(pipeline.mark)
#         gitProject = GitProject.objects.get(id=project_id)
#         build_params = {
#             'project_git': job.project_git,
#             'CoverageUid': job.id,
#             'end_commit': job.end_commit,
#             'start_commit': job.compare_branch,
#             'server_ip': gitProject.server_ip,
#             'server_port': gitProject.server_port
#         }
#         free_job = jenkinsTool.get_free_job(jenkinsTool.CoverageJobNames)
#         build_number = jenkinsTool.get_build_number(free_job)
#         job.build_number = build_number
#         job.coverage_job_name = free_job
#         job.save()
#         # 触发报告收集job
#         result = jenkinsTool.build_job(free_job, params=build_params)
#         query.update(coverage_status=result)
#         job.build_status = result
#         job.save()
#     except Exception as e:
#         result = JenkinsTaskStatus.FAIL.value
#         mark['coverage'] = e.args[0] if e.args else 'jenkins构建失败，请查看日志'
#         logging.error(f'覆盖率异步任务执行失败{e}')
#     finally:
#         query.update(coverage_status=result, mark=json.dumps(mark))
#         JenkinsBuildTask.objects.filter(id=job.id).update(build_status=result)
#         if result == JenkinsTaskStatus.FAIL.value:
#             notify_chat_ids = pipeline.notify_chat_ids.split(',') if pipeline.notify_chat_ids else []
#             ace_larkhooks(open_id=open_id, pipeline_name=pipeline.name, pipeline_id=pipeline.id, step=pipeline.step2,
#                           commit_id=job.end_commit, status=result, chat_ids=notify_chat_ids)

def get_container_ip():
    # 获取容器的主机名
    hostname = os.environ.get('HOSTNAME')

    # 解析主机名获取 IP 地址
    ip_address = socket.gethostbyname(hostname)

    return ip_address


def trigger_coverage_job(task_id, project_id, open_id):
    '''执行jenkins 覆盖率收集job'''
    logging.info('--------------------开始执行覆盖率报告生成---------------------------------')
    try:
        job = JenkinsBuildTask.objects.get(id=task_id)
        query = CoveragePipeline.objects.filter(id=job.pipeline_id)
        pipeline = query.first()
        mark = json.loads(pipeline.mark)
        gitProject = GitProject.objects.get(id=project_id)
        build_params = {
            'project_git': job.project_git,
            'CoverageUid': job.id,
            'end_commit': job.end_commit,
            'start_commit': job.compare_branch,
            'server_ip': get_container_ip(),  # 获取容器的 IP 地址
            'server_port': gitProject.server_port
        }
        free_job = jenkinsTool.get_free_job(jenkinsTool.CoverageJobNames)
        build_number = jenkinsTool.get_build_number(free_job)
        job.build_number = build_number
        job.coverage_job_name = free_job
        job.save()
        # 触发报告收集job
        result = jenkinsTool.build_job(free_job, params=build_params)
        query.update(coverage_status=result)
        job.build_status = result
        job.save()
    except Exception as e:
        result = JenkinsTaskStatus.FAIL.value
        mark['coverage'] = e.args[0] if e.args else 'jenkins构建失败，请查看日志'
        logging.error(f'覆盖率异步任务执行失败{e}')
    finally:
        query.update(coverage_status=result, mark=json.dumps(mark))
        JenkinsBuildTask.objects.filter(id=job.id).update(build_status=result)
        if result == JenkinsTaskStatus.FAIL.value:
            notify_chat_ids = pipeline.notify_chat_ids.split(',') if pipeline.notify_chat_ids else []
            ace_larkhooks(open_id=open_id, pipeline_name=pipeline.name, pipeline_id=pipeline.id, step=pipeline.step2,
                          commit_id=job.end_commit, status=result, chat_ids=notify_chat_ids)


@app.task(bind=True, max_retries=3, default_retry_delay=2)
def write_coverage_data_2_db(self, coverage_id, project_name, project_id):
    '''解析覆盖率数据落库'''
    try:
        # 解析全量覆盖率
        pipeline = CoveragePipeline.objects.get(project_id=project_id)
        with open(f'/data/jacoco/report/{coverage_id}/Check_Order_related/index.html', 'r') as html:
            text = html.read()
            pattern = re.compile(
                'Total</td><td class="bar">(.*?) of (.*?)</td><td class="ctr2">(.*?)%</td><td class="bar">(.*) of (.*?)</td><td class="ctr2">')
            result = pattern.findall(text)[0]
            line_all = int(result[1].replace(',', ''))
            line_cover = line_all - int(result[0].replace(',', ''))
            branch_all = int(result[4].replace(',', ''))
            branch_cover = branch_all - int(result[3].replace(',', ''))
            pattern2 = re.compile('<p><font size="5" color="Green">接口覆盖率:(.*?)</font></p>')
            api_coverage = pattern2.findall(text)
            if len(api_coverage) == 0:
                api_coverage = 0.0
            else:
                api_coverage = float(api_coverage[0].split('(')[1].split('%')[0]) / 100
            FullCoverage.objects.update_or_create(coverage_id=coverage_id,
                                                  defaults={'project_name': project_name,
                                                            'project_id': project_id,
                                                            'line_rate': mode_number(line_cover, line_all, 2),
                                                            'line_cover': line_cover,
                                                            'line_all': line_all,
                                                            'branch_rate': mode_number(branch_cover, branch_all, 2),
                                                            'branch_cover': branch_cover,
                                                            'branch_all': branch_all,
                                                            'api_coverage': api_coverage})

            # 解析增量覆盖率
            with open(f'/data/jacoco/report/{coverage_id}/diff-report.html', 'r') as f:
                text = f.read()
                total = re.compile(
                    r'<li><b>Total</b>: (\d+) lines</li>')
                total_lines = int(total.findall(text)[0])
                missing = re.compile(
                    r'<li><b>Missing</b>: (\d+) lines</li>')
                missling_lines = int(missing.findall(text)[0])
                cover_lines = total_lines - missling_lines
                DiffCoverage.objects.update_or_create(coverage_id=coverage_id,
                                                      defaults={'project_name': project_name,
                                                                'project_id': project_id,
                                                                'line_rate': mode_number(cover_lines, total_lines, 2),
                                                                'line_cover': cover_lines,
                                                                'line_all': total_lines,
                                                                })
    except Exception as e:
        logging.error(e)
        raise self.retry(exc=e)


@retry(tries=3)
def ace_larkhooks(open_id, pipeline_name, pipeline_id, step, status, commit_id,
                  chat_ids=['oc_1414fc667fca8a6875400ee1e5f2abd6']):
    for chat_id in chat_ids:
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
                            "content": f"【流水线:{pipeline_name}】{JenkinsTaskStatus.get_chinese(status)}"
                        },
                        "template": "green" if status == JenkinsTaskStatus.SUCCESS.value else "red"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**主题**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n{pipeline_name}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**步骤**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n{step}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**分支/commitId**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n{commit_id}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**执行结果**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n{JenkinsTaskStatus.get_chinese(status)}"
                                    }
                            }]
                        },
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**触发人**"
                            },
                            "fields": [{
                                "is_short": False,
                                "text":
                                    {
                                        "tag": "lark_md",
                                        "content": f"\n<at id={open_id}></at>" if open_id else "system"
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
                                        "content": "查看详情"
                                    },
                                    "URL": f"http://qa.jiliguala.com/coverage/pipeline/build/record/{pipeline_id}" if step == '覆盖率收集' else f"http://qa.jiliguala.com/coverage/pipeline/server/build/record/{pipeline_id}",
                                    "type": "default"
                                }
                            ]
                        }
                    ]
                },
                "open_id": open_id,
                "open_chat_id": chat_id,
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
