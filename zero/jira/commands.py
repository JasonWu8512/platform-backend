# -*- coding: utf-8 -*-
# @Time    : 2020/11/2 6:30 下午
# @Author  : zoey
# @File    : commands.py
# @Software: PyCharm
from jira import JIRA
import requests
from functools import wraps
from zero.settings import BASE_JIRA_URL, JIRA_USER, JIRA_PASSWORD
from zero.utils.enums.jlgl_enum import ChineseEnum, ChineseTuple

'''jira会用到的一些枚举'''

class JiraStoryTestStatus(ChineseEnum):
    '''story提测状态'''
    Normal = ChineseTuple(('normal', '正常'))
    Delay = ChineseTuple(('delay', '延期'))
    InProgress = ChineseTuple(('inProgress', '未提测'))
    Today = ChineseTuple(('today', '今日'))


class JiraIssueType(ChineseEnum):
    '''任务类型'''
    SUBTASK = ChineseTuple(("子任务", 'Sub-task'))
    TASK = ChineseTuple(("任务", 'Task'))
    STORY = ChineseTuple(('故事', 'Story'))
    EPIC = ChineseTuple(("Epic", 'Epic'))
    BUG = ChineseTuple(('故障', 'Bug'))


class JiraIssueStatus(ChineseEnum):
    '''任务状态'''
    DONE = ChineseTuple(("完成", "Done"))
    TODO = ChineseTuple(("待办", "ToDo"))
    FIXED = ChineseTuple(("Fixed", "Fixed"))
    CLOSED = ChineseTuple(("已关闭", "Closed"))
    REOPENED = ChineseTuple(("重新打开", "Reopened"))
    INPROGRESS = ChineseTuple(("处理中", "In Progress"))


class JiraBugPoint(ChineseEnum):
    '''bug分数'''
    P0 = ChineseTuple(("P0", 20))
    P1 = ChineseTuple(("P1", 5))
    P2 = ChineseTuple(("P2", 3))
    P3 = ChineseTuple(("P3", 1))
    P4 = ChineseTuple(("P4", 1))
    S0 = ChineseTuple(("S0", 20))
    S1 = ChineseTuple(("S1", 5))
    S2 = ChineseTuple(("S2", 3))
    S3 = ChineseTuple(("S3", 1))


class JiraTerminalId(ChineseEnum):
    """terminal排序ID"""
    BE = ChineseTuple(("BE", 0))
    FE = ChineseTuple(("FE", 1))
    ANDROID = ChineseTuple(("ANDROID", 2))
    IOS = ChineseTuple(("IOS", 3))
    COCOS = ChineseTuple(("COCOS", 4))
    BIGDATA = ChineseTuple(("BIGDATA", 5))
    AI = ChineseTuple(("AI", 6))
    QA = ChineseTuple(("QA", 7))


class JiraTerminalName(ChineseEnum):
    """terminal映射版本名"""
    BE = ChineseTuple(("BE", "Server"))
    FE = ChineseTuple(("FE", "H5"))
    ANDROID = ChineseTuple(("ANDROID", "Android"))
    IOS = ChineseTuple(("IOS", "IOS"))
    COCOS = ChineseTuple(("COCOS", "Cocos"))
    BIGDATA = ChineseTuple(("BIGDATA", "Bigdata"))
    AI = ChineseTuple(("AI", "AI"))
    QA = ChineseTuple(("QA", "QA"))


class DepartmentLeader(ChineseEnum):
    """部门负责人"""
    IT = ChineseTuple(("IT", "李冀"))
    QC = ChineseTuple(("质量效能部", "李冀"))
    YW = ChineseTuple(("运维部", "王季荣"))
    JCYFPT = ChineseTuple(("基础研发平台部", "骆仕恺"))
    JLGLJS = ChineseTuple(("叽里呱啦技术部", ""))
    # JYZT = ChineseTuple(("交易中台部", "王伟锋"))
    SJZN = ChineseTuple(("数据智能部", "王季荣"))
    YWYF = ChineseTuple(("业务研发部", "王伟锋"))
    QDJS = ChineseTuple(("前端技术部", "王善成"))
    ZTJS = ChineseTuple(("中台技术部", "王季荣"))
    YDJS = ChineseTuple(("移动技术部", "覃少强"))

'''jir http登录的装饰器'''


def http_login():
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except:
                api_url = f'{BASE_JIRA_URL}/login.jsp'
                self.session = requests.Session()
                self.session.post(url=api_url,
                                  data={"os_username": JIRA_USER, "os_password": JIRA_PASSWORD, "login": "LOG IN"},
                                  verify=False,
                                  headers={"Content-Type": "application/x-www-form-urlencoded"})
                return func(self, *args, **kwargs)

        return wrapper

    return decorator


class JiraClient:
    jiraClient = JIRA(server=BASE_JIRA_URL, auth=(JIRA_USER, JIRA_PASSWORD), get_server_info=False,
                      options={'aglie_rest_path': 'aglie'})

    def __init__(self):
        api_url = f'{BASE_JIRA_URL}/login.jsp'
        self.session = requests.Session()
        self.session.post(url=api_url,
                          data={"os_username": "zoey", "os_password": "123456", "login": "LOG IN"},
                          verify=False,
                          headers={"Content-Type": "application/x-www-form-urlencoded"})

    def search_issue(self):
        jql = 'id=XSHARE-579'
        issues = self.jiraClient.search_issues(jql, expand='changelog')
        return issues

    @http_login()
    def get_project_all_data(self, board_id):
        jira_url = f"{BASE_JIRA_URL}/rest/greenhopper/1.0/xboard/work/allData.json?rapidViewId={board_id}&selectedProjectKey=READING"
        data = self.session.get(jira_url).json()
        return data

    @http_login()
    def get_project_rapidviews(self, projectKeyOrId):
        jira_url = f'{BASE_JIRA_URL}/rest/agile/1.0/board?projectKeyOrId={projectKeyOrId}'
        data = self.session.get(jira_url).json()
        return data

    @http_login()
    def get_user_info(self, user_name):
        jira_url = f'{BASE_JIRA_URL}/rest/api/2/user?username={user_name}'
        data = self.session.get(jira_url).json()
        return data

    @http_login()
    def create_jira_user(self, username, email, full_name):
        jira_url = f'{BASE_JIRA_URL}/rest/api/latest/user'
        body = {
            "email": email,
            "username": username,
            "fullname": full_name,
            "selectedApplications": "jira-software",
            "Create": "创建用户"
        }
        res = self.session.post(url=jira_url, json=body)
        # res = self.jiraClient.add_user(username=username, email=email, password='niuniuniu168', fullname=full_name)
        return res

    # def create_issue(self):
    #     issue_dict = {
    #         'project': {'id': 10105},
    #         'summary': 'New issue from jira-python',
    #         'description': 'Look into this one',
    #         'issuetype': {'name': 'Bug'},
    #     }
    #     res = self.jiraClient.create_issue(fields=issue_dict)
    #     return res

    # def get_task(self):
    #     tasks = self.jiraClient.


jiraTool = JiraClient()
# boards = jiraTool.get_project_rapidviews(10223)
# print(boards)
# jiraTool.create_issue()

# jiraTool.get_user_info('keith')
# user = jiraTool.jiraClient.user('admin')
# print(user)
# jiraTool.search_issue()
# datas = jiraTool.jiraClient.version(id=10158)
# print(datas)
# file_path = '/Users/zoey/Downloads/openshare.xlsx'
# data = openpyxl.load_workbook(file_path)
# ws = data.worksheets[0]
# rows = ws.max_row
# for i in range(1, rows+1):
#     fullname = ws.cell(row=i, column=1).value
#     email = ws.cell(row=i, column=2).value
#     name = ws.cell(row=i, column=2).value.split('@')[0]
#     jiraTool.create_jira_user(username=name, email=email, full_name=fullname)
