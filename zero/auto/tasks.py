# -*- coding: utf-8 -*-
# @Time    : 2021/3/15 10:10 上午
# @Author  : zoey
# @File    : tasks.py
# @Software: PyCharm
import time
import zero.utils.alert_robot as alert_robot
from zero.celery import app
from zero.auto.models import AutoCaseConfig, AutoCaseRunHistory, AutoCaseAllureReport, AutoCaseAllureDetail
from zero.coverage.commands import jenkinsTool, JenkinsTaskStatus
from retry import retry
from zero.coverage.tasks import trigger_coverage_job
from zero.coverage.models import JenkinsBuildTask, CoveragePipeline, GitProject, JenkinsProjectCommit
from jenkinsapi.custom_exceptions import (
    NotFound, NotBuiltYet
)
import logging
import shortuuid
import requests
import json

trace = logging.getLogger('trace')


@app.task(time_limit=20)
def check_auto_case_status():
    """更新自动化用例执行状态，以及执行结束后的步骤"""
    histories = AutoCaseRunHistory.objects.filter(status=JenkinsTaskStatus.RUNNING.value)
    mark = ''
    for history in histories:
        try:
            status = jenkinsTool.get_job_build_result('test/tiga', history.build_number)
        except NotFound as e:
            status = JenkinsTaskStatus.FAIL.value
            mark = e.args[0]
            if history.recover_times < 30:
                status = JenkinsTaskStatus.RUNNING.value
                AutoCaseRunHistory.objects.filter(id=history.id).update(recover_times=history.recover_times + 1)
        except Exception as e:
            mark = str(e)
            status = JenkinsTaskStatus.FAIL.value
        finally:
            AutoCaseRunHistory.objects.filter(id=history.id).update(status=status, mark=mark)
            AutoCaseConfig.base_upsert({'id': history.auto_config_id}, **{'status': status})
            if status != JenkinsTaskStatus.RUNNING.value:
                config_set = AutoCaseConfig.objects.get(id=history.auto_config_id)
                for chat_id in config_set.notify_chat_ids:
                    ace_larkhooks(config_name=config_set.name, status=status, chat_id=chat_id,
                                  username=history.username)
                if status == JenkinsTaskStatus.SUCCESS.value:
                    for pipeline_id in config_set.pipeline_ids:
                        continue_run_coverage(pipeline_id=pipeline_id, username=config_set.creator)
                generate_allure_report.apply_async(kwargs={'history_id': history.id, 'build_number': history.build_number,
                                                       'job_name': 'test/tiga'}, countdown=1)


def check_single_auto_case_status(build_number: int):
    history = AutoCaseRunHistory.objects.filter(build_number=build_number).first()
    if not history:
        trace.error(f'构建id {build_number}不存在')
        alert_robot.alert_ops_robot(f'构建id {build_number}不存在')
        return
    try:
        trace.info(f'构建id {build_number}正在执行中， 尝试获取执行状态')
        status = get_job_build_final_result(build_number)
    except NotBuiltYet as e:
        alert_robot.alert_ops_robot(str(e))
        status = JenkinsTaskStatus.RUNNING.value

    trace.info(f'构建id {build_number}执行状态为{status}')

    if status == JenkinsTaskStatus.FAIL.value:
        alert_robot.alert_ops_robot(f'自动化回归用例集 {history.auto_config_name} 执行失败，查看报告：http://qa.jiliguala.com/auto/build/report/{history.id}')
    elif status == JenkinsTaskStatus.RUNNING.value:
        alert_robot.alert_ops_robot(f'自动化回归用例集 {history.auto_config_name} 执行中，执行记录列表：http://qa.jiliguala.com/auto/config/build/record \n查看报告：http://qa.jiliguala.com/auto/build/report/{history.id}')
    elif status == JenkinsTaskStatus.SUCCESS.value:
        alert_robot.alert_ops_robot(f'自动化回归用例集 {history.auto_config_name} 执行成功，查看报告：http://qa.jiliguala.com/auto/build/report/{history.id}')
    else:
        trace.error(f'构建id {build_number}执行状态为{status}， 未知状态')


@retry(tries=10, delay=5)
def get_job_build_final_result(build_number: int) -> str:
    """获取构建终态结果"""
    try:
        status = jenkinsTool.get_job_build_result('test/tiga', build_number)
    except NotFound as e:
        raise e
    if status == JenkinsTaskStatus.RUNNING.value:
        duration = jenkinsTool.get_job_build_duration('test/tiga', build_number)
        raise NotBuiltYet('构建id {}还未结束, 已耗时{}s'.format(build_number, duration))
    return status


@app.task()
def trigger_auto_case_run(config_id, username=None, job_name='test/tiga', alert_when_fail=False):
    logging.info("""-----------------------开始执行自动化用例--------------------------------""")
    """
    :param config_id:
    :param username:
    :return:
    """
    config_set = AutoCaseConfig.objects.get(id=config_id)
    AutoCaseConfig.base_upsert({'id': config_id}, **{'status': JenkinsTaskStatus.RUNNING.value})
    body = {
        'auto_config_id': config_id,
        'auto_config_name': config_set.name,
        'status': JenkinsTaskStatus.RUNNING.value,
    }
    if username:
        body.update({'username': username})
    history = AutoCaseRunHistory.objects.create(**body)
    try:
        build_params = {
            "branch": 'develop',
            'env': getattr(config_set, 'exec_env', 'fat') or 'fat',
            'caseString': ' '.join(config_set.cases),
            'mark': config_set.tags,
            'gitRemote': 'qa'
        }
        mark = ''
        free_job = jenkinsTool.get_free_job(target_jobs=[job_name])
        build_number = jenkinsTool.get_build_number(free_job)
        history.build_number = build_number
        history.save()
        result = jenkinsTool.build_job(free_job, build_params)
    except Exception as e:
        result = JenkinsTaskStatus.FAIL.value
        mark = str(e)
    finally:
        history.mark = mark
        history.status = result
        history.save()
        AutoCaseConfig.base_upsert({'id': config_id}, **{'status': result})
        if alert_when_fail:
            trace.info(f'执行测试用例集{config_set.name}, 执行结果将通过企微群机器人通知')
            # 已经失败，直接告警
            if result == JenkinsTaskStatus.FAIL.value:
                trace.error(f'自动化回归用例集 {config_set.name} 执行失败, 原因: {mark}')
                alert_robot.alert_ops_robot(f'自动化回归用例集 {config_set.name} 执行失败, 查看报告：http://qa.jiliguala.com/auto/build/report/{history.id}')
            else:
                trace.info(f'自动化回归用例集 {config_set.name} 开始执行')
                check_single_auto_case_status(build_number=history.build_number)

@app.task(bind=True, max_retries=3, default_retry_delay=1)
def generate_allure_report(self, history_id, build_number, job_name):
    logging.info(f'---------------------------开始执行生成allure报告{history_id}{build_number}{job_name}--------------------------')
    try:
        summary = jenkinsTool.get_allure_suites_summary(job_name, build_number)
        suites, details = jenkinsTool.get_allure_result_data_suites(job_name, build_number)
        AutoCaseAllureReport.base_upsert({'id': history_id}, **{'suites': suites, 'summary': summary})
        for detail in details:
            AutoCaseAllureDetail.base_upsert({'id': detail['uid']}, **{'detail': detail})
    except Exception as e:
        logging.error(e)
        raise self.retry(exc=e)


def continue_run_coverage(pipeline_id, username):
    logging.info(f"""-----------------开始执行{username}关联的覆盖率报告生成-----------------------------------""")
    if pipeline_id:
        try:
            # 创建一个覆盖率task
            pipeline = CoveragePipeline.objects.get(id=pipeline_id)
            build_number = jenkinsTool.get_build_number(jenkinsTool.CoverageJobName)
            end_commit = JenkinsProjectCommit.objects.filter(project_name=pipeline.project_name).order_by('-id').first()
            task = JenkinsBuildTask.objects.create(project_git=json.loads(pipeline.coverage_params)['project_git'],
                                                   end_commit=end_commit.short_commit,
                                                   build_number=build_number, username=username,
                                                   pipeline_id=pipeline_id, pipeline_name=pipeline.name)
        except CoveragePipeline.DoesNotExist:
            logging.error('该自动化用例关联的流水线不存在/已被删除')
            return
        except Exception as e:
            logging.error(e.args[0])
            return
        # 抛出一个异步任务触发覆盖率job
        trigger_coverage_job(task_id=task.id, project_id=pipeline.project_id, open_id=None)


@retry(tries=3)
def ace_larkhooks(config_name, status, chat_id, username):
    """通过机器人通知自动化执行结果"""
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
                        "content": f"【接口自动化:{config_name}】{JenkinsTaskStatus.get_chinese(status)}"
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
                                    "content": f"{config_name}"
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
                                    "content": f"{JenkinsTaskStatus.get_chinese(status)}"
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
                                    "content": f"{username}"
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
                                "URL": "http://qa.jiliguala.com/auto/config/build/record",
                                "type": "default"
                            }
                        ]
                    }
                ]
            },
            "open_chat_id": chat_id
        },
        "uuid": shortuuid.uuid(),
        "token": "zero_jiliguala"
    }
    try:
        res = requests.post('https://ace.jiliguala.com/endpoints/lark/', json=body, headers={'Content-Type': 'application/json'}, verify=False)
        res.raise_for_status()
    except Exception as e:
        raise e