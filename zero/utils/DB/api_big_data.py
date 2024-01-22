# !/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time : 2021/1/5 23:24
# @Author : Wolf
# @File : api_big_data.py
# @Project : zero

import backoff
import requests
from urllib import parse

class ApiAdhoc(object):
    def __init__(self):
        """
        通过api查询hive数据
        """
        self.host = "http://givendata.jiliguala.com"
        self.headers = {
            "ContentType": "application/json;charset=UTF-8",
            "Authorization": "Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJkZW1vbl9qaWFvQGppbGlndWFsYS5jb20iLCJleHAiOjE2MTExMzY0NzksImlhdCI6MTYxMTA1MDA3OX0.GrKnLwABsBP3uWEYwoZTVW7GivRI5RGEOD3QumAdHQzeQlz438tDWfVx7nriVUBThABcV_1B9to7NxZPJarloA"
        }
        self.session = requests.Session()
        self.session.request(
            method="post",
            url=parse.urljoin(self.host, '/api_basic/auth/login'),
            json={
                "email_address": "demon_jiao@jiliguala.com",
                "pwd": "zpimvd7w2s",
                "vcode": "apwy",
                "uuid": "1083c85717804d179a6eda289cdefc61"
            },
            headers=self.headers
        )
        self.token = ""

    def api_adhoc_query_list(self, sql, user_name='demon_jiao', lmt="5001", typ="Hive"):
        """生成数据查询的sql—log,单语句查询"""
        url = parse.urljoin(self.host, '/api_adhoc/adhoc/queryList')

        body = {
            "user": user_name,
            "queryList": [sql],
            "type": typ,
            "limit": lmt
        }

        return requests.request(method='post', url=url, json=body, headers=self.headers)

    def api_adhoc_check_status(self, task_id: str):
        """日志状态轮询"""
        url = parse.urljoin(self.host, '/api_adhoc/adhoc/checkStatus')
        body = {"id": [task_id]}

        return requests.request(method='post', url=url, json=body, headers=self.headers)

    def api_adhoc_sql_result(self, task_id: str):
        """获取sql查询结果"""
        url = parse.urljoin(self.host, '/api_adhoc/adhoc/sqlResult')
        body = {"id": [task_id]}

        return requests.request(method='post', url=url, json=body, headers=self.headers)


class BackOffQuery(object):
    def __init__(self, sql):
        self.asr = ApiAdhoc()
        self.sql = sql
        self.taskid = self.asr.api_adhoc_query_list(sql=self.sql).json().get("data")[0]
        print(self.taskid)

    @backoff.on_predicate(backoff.constant, interval=5)
    def back_off_query(self, *args, **kwargs):
        """
        :param taskid :查询ID
        :return
        """
        res = self.asr.api_adhoc_check_status(task_id=self.taskid, ).json()

        for dat in res['data'][self.taskid]:
            # print(dat)
            assert dat['id'] == self.taskid
            if dat['status'] == '2':
                # 查询完成
                return True
            elif dat['status'] == '3':
                raise dat['exception']

    def api_get_data(self):
        try:
            if self.back_off_query():
                return self.asr.api_adhoc_sql_result(task_id=self.taskid).json().get('data')[self.taskid]
        except Exception as e:
            print(e)

def mock_data(sql):
    return {"data": [
        ["stat_date", "stat_date_repeat_ratio"],
        ["2021-01-07", "2001"],
        # ["2021-01-04", "0.3"],
        # ["2021-01-05", "0.528272"],
        # ["2021-01-06", "100"],
    ]}

def enum_data(sql):
    return {"data": [
        ["name"],
        ["2021-01-07"],
        ["2021-01-04"],
        ["2021-01-05"],
        ["2021-01-06"],
    ]}


debug = True
def get_data(sql):
    if debug:
        return mock_data(sql)
    else:
        res = BackOffQuery(sql=sql)
        current_monitor_data = res.api_get_data().get("data")
        return current_monitor_data

if __name__ == '__main__':
    sql = """
    select * 
    from jlgl_rpt.rpt_traffic_reading_new_user_add_d as d 
    where d.dt = '20201011'
    """
    res = BackOffQuery(sql=sql)
    print(res.api_get_data())
    # aadc = ApiAdhoc()
    # dsd = aadc.api_adhoc_query_list(sql="show tables")
    # print(dsd)