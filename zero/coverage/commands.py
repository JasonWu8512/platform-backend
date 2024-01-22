# -*- coding: utf-8 -*-
# @Time    : 2021/2/23 11:10 上午
# @Author  : zoey
# @File    : command.py
# @Software: PyCharm
import json
import re
import time
from string import Template

import requests
# from gevent.threadpool import ThreadPool
from collections import Counter
from jenkinsapi.build import Build
from jenkinsapi.jenkins import Jenkins
from jenkinsapi.custom_exceptions import (
    NoBuildData,
    NotConfiguredSCM,
    NotFound,
    NotInQueue,
    NotSupportSCM,
    UnknownQueueItem,
    BadParams,
)

from zero import settings
from zero.settings import BASE_JENKINS_URL, JENKINS_USER, JENKINS_APITOKEN
from zero.utils.enums.jlgl_enum import ChineseEnum, ChineseTuple
from retry import retry
import random

sonar_page_list_template = Template('http://sonar.jlgltech.com/api/components/search_projects?'
                                    'ps=$per&facets=&f=analysisDate%2CleakPeriodDate&p=$cur_page')
cmdb_url = "http://ops.jlgltech.com/api/cmdb/service/info/all"


class JenkinsTaskStatus(ChineseEnum):
    '''任务状态'''
    PENDING = ChineseTuple(("pending", "待执行"))
    RUNNING = ChineseTuple(("running", "执行中"))
    SUCCESS = ChineseTuple(("success", "成功"))
    FAIL = ChineseTuple(("fail", "失败"))


class PipelineBusiness(ChineseEnum):
    '''流水线所属业务线'''
    TRADE = ChineseTuple(('trade', "交易中台"))
    OMO = ChineseTuple(('omo', '增长中台'))
    READING = ChineseTuple(('reading', '呱呱阅读'))
    CRM = ChineseTuple(('crm', 'Crm'))
    JLGL = ChineseTuple(('jlgl', '叽里呱啦'))
    DATA = ChineseTuple(('data', '数仓/AI'))
    COURSE = ChineseTuple(('course', '课程中台'))



class Terminal(ChineseEnum):
    '''流水线所属端'''
    BE = ChineseTuple(('BE', '后端'))
    FE = ChineseTuple(('FE', '前端'))
    ME = ChineseTuple(('ME', '移动端'))


class JenkinsClient:
    CoverageJobNames = ['test/coverage', 'test/coverage1', 'test/coverage2']
    jenkinsClient = Jenkins(BASE_JENKINS_URL, username=JENKINS_USER, password=JENKINS_APITOKEN)

    def get_build_number(self, job_name):
        job_before = self.jenkinsClient.get_job(job_name)
        nextBuildNumber = job_before.__dict__['_data']['nextBuildNumber']
        return nextBuildNumber

    def get_free_job(self, target_jobs=[]):
        '''获取test下空闲的job'''
        target_jobs = map(lambda x: x.split('/')[-1], target_jobs)
        que = self.jenkinsClient.get_queue()
        items = que.__dict__['_data']['items']
        biz_jobs = [item['task']['name'] for item in items]
        free_jobs = set(target_jobs).difference(set(biz_jobs))
        free_jobs = [f'test/{job}' for job in free_jobs]
        if free_jobs:
            job_name = random.choice(free_jobs)
        else:
            raise ValueError('job列表中已有正在等待的任务，不能构建新的任务，请到jenkins确认是否要停掉已有任务，再重试')
        return job_name

    def build_job(self, job_name, params):
        '''触发构建'''
        try:
            # 参数化构建job
            self.jenkinsClient.build_job(job_name, params=params)
        except Exception as e:
            raise e
        return JenkinsTaskStatus.RUNNING.value

    # @retry(NotFound, tries=3, delay=2)
    def get_job_build_result(self, job_name, build_number):
        '''获取构建结果'''
        job = self.jenkinsClient.get_job(job_name)
        try:
            build_info = job.get_build(build_number)
        except NotFound as e:
            raise e
        result = build_info.__dict__['_data']['result']
        if not result:
            return JenkinsTaskStatus.RUNNING.value
        elif result == 'SUCCESS':
            return JenkinsTaskStatus.SUCCESS.value
        else:
            return JenkinsTaskStatus.FAIL.value

    def get_job_build_duration(self, job_name, build_number):
        '''获取构建时长, 未结束的build没有duration值，取当前时间ts-任务开始时间ts'''
        job = self.jenkinsClient.get_job(job_name)
        try:
            build_info = job.get_build(build_number)
        except NotFound as e:
            raise e
        if not build_info.__dict__['_data']['duration']:
            duration = int(time.time()) * 1000 - build_info.__dict__['_data']['timestamp']
        else:
            duration = build_info.__dict__['_data']['duration']
        print(build_info.__dict__['_data'])
        return duration/1000

    def get_build_console_output(self, job_name, build_id):
        """获取job的执行日志"""
        job = self.jenkinsClient.get_job(job_name)
        url = job.__dict__['_data']['lastBuild']['url']
        url = url.replace('http://', f'http://{JENKINS_USER}:{JENKINS_APITOKEN}@')
        url = url.replace(re.findall('/(\d+)/', url)[-1], f'{build_id}')
        res = requests.get(url=f'{url}/consoleText')
        result = res.text
        return result

    def get_is_building(self, job_name, build_id):
        # 获取job是否还在运行
        job = self.jenkinsClient.get_job(job_name)
        url = job.__dict__['_data']['lastBuild']['url']
        obj = Build(url, build_id, job)
        # 判断job名为job_name的job的number构建是否还在构建中
        is_running = obj.is_running()
        return is_running

    def get_allure_suites_summary(self, job_name, build_id):
        job = self.jenkinsClient.get_job(job_name)
        url = job.__dict__['_data']['lastBuild']['url']
        url = url.replace('http://', f'http://{JENKINS_USER}:{JENKINS_APITOKEN}@').replace(
            re.findall('/(\d+)/', url)[-1], f'{build_id}')
        res = requests.get(url=f'{url}/allure/widgets/summary.json')
        items = requests.get(url=f'{url}/allure/widgets/suites.json')
        res.raise_for_status()
        items.raise_for_status()
        result = res.json()
        suites = items.json()
        result['suites'] = suites
        return result

    def get_allure_result_data_suites(self, job_name, build_id):
        """allure获取指定构建的suites
        """
        job = self.jenkinsClient.get_job(job_name)
        url = job.__dict__['_data']['lastBuild']['url']
        url = url.replace('http://', f'http://{JENKINS_USER}:{JENKINS_APITOKEN}@').replace(
            re.findall('/(\d+)/', url)[-1], f'{build_id}')
        res = requests.get(url=f'{url}/allure/data/suites.json')
        res.raise_for_status()
        result = res.json()
        children = [result]
        details = []
        while children:
            cur = children.pop()
            if cur.get('status'):
                details.append(self.get_allure_result_data_suites_details(job_name, build_id, cur['uid']))
            else:
                children.extend(cur['children'])
        return result, details

    def get_allure_result_data_suites_details(self, job_name, build_id, case_id):
        """allure获取每个用例的执行结果
        """
        job = self.jenkinsClient.get_job(job_name)
        url = job.__dict__['_data']['lastBuild']['url']
        url = url.replace('http://', f'http://{JENKINS_USER}:{JENKINS_APITOKEN}@')
        url = url.replace(re.findall('/(\d+)/', url)[-1], f'{build_id}')
        res = requests.get(url=f'{url}/allure/data/test-cases/{case_id}.json')
        res.raise_for_status()
        result = res.json()
        if result.get('statusTrace'):
            result['statusTrace'] = result['statusTrace'].replace('\\n', '\n')
        return result


class SonarClient:
    @staticmethod
    def get_sonar_gate_results_by_app_name(project_name_query_set):
        query_keys = ""
        for project_name_query in project_name_query_set:
            if query_keys == "":
                query_keys = project_name_query
            else:
                query_keys = query_keys + "%2C" + project_name_query
        measure_url = f"{settings.SONAR_URL}/api/measures/search?projectKeys={query_keys}&metricKeys=quality_gate_details"
        cmdb_list = get_cmdb_info()
        cmdb_dict = {}
        for cmdb_one in cmdb_list:
            cmdb_git_name = get_git_name(cmdb_one['gitpath'])
            cmdb_dict[cmdb_git_name] = [cmdb_one['owner']['nickname'], cmdb_one['description']]
        response = requests.get(measure_url)
        response_json = response.json()
        result_set = []
        for measure in response_json["measures"]:
            result = {}
            temp = measure["value"]
            condition_json = json.loads(temp)
            result["app_name"] = measure["component"]
            if measure["component"] in cmdb_dict:
                result["owner"] = cmdb_dict[measure["component"]][0]
            for condition in condition_json["conditions"]:
                if condition["metric"] == "blocker_violations":
                    result["blocker"] = condition["actual"]
                if condition["metric"] == "new_critical_violations":
                    result["critical"] = condition["actual"]
            app_name = result["app_name"]
            single_component_url = f"{settings.SONAR_URL}/api/navigation/component?component={app_name}"
            single_component_response = requests.get(single_component_url)
            single_component_response_json = single_component_response.json()
            for qualityProfile in single_component_response_json["qualityProfiles"]:
                if qualityProfile["language"] != "xml":
                    result["lang"] = qualityProfile["language"]
            blocker_num = 0
            critical_num = 0
            if "blocker" in result:
                blocker_num = int(result["blocker"])
            if "critical" in result:
                critical_num = int(result["critical"])
            if blocker_num + critical_num > 0:
                result[
                    "sonar_url"] = f"http://sonar.jlgltech.com/project/issues?id={app_name}&resolved=false&sinceLeakPeriod=true"
                result["check_result"] = "不通过"
                result_set.append(result)
            else:
                result["check_result"] = "通过"
                result_set.append(result)
        return result_set

    @classmethod
    def get_project_list(cls, per, cur_page):
        actual_sonar_page_list_url = sonar_page_list_template.substitute(per=per, cur_page=cur_page)
        response = requests.get(actual_sonar_page_list_url)
        if response.status_code == 200:
            response_json = response.json()
            project_name_query_set = []
            paging = response_json.get("paging", {})
            total = paging.get("total", 0)
            for component in response_json['components']:
                project_name_query_set.append(component["key"])
            return cls.get_sonar_gate_results_by_app_name(project_name_query_set), total


def get_cmdb_info():
    response = requests.get(cmdb_url)
    response_json = response.json()
    return response_json['data']


def get_git_name(git_path):
    return git_path.split('/')[-1][0:-4]


jenkinsTool = JenkinsClient()
# jenkinsTool.get_build_console_output('test/coverage1', 52)
# jenkinsTool.get_job_build_result(job_name='test/coverage', build_number=700)
# que = jenkinsTool.jenkinsClient.get_queue()
# print(que)
# jenkinsTool.get_allure_suites_summary(job_name='test/tiga', build_id=122)
# jenkinsTool.get_allure_result_data_suites_details('test/tiga', 86, 'ebfc7b5a9e057619')
# jenkinsTool.get_build_console_output('test/coverage', 87)
