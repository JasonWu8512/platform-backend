# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/16 12:48 上午
@Author  : Demon
@File    : rpc_lesson_score.py
"""

import requests
from json import dumps

headers = {'Connection': 'close'}

def params_to_string(request_data):
    '''格式化参数'''
    print(request_data)
    if not isinstance(request_data, list):
        raise Exception('please input array object!')
    _str = '`z8&-A@0'
    ans = []
    def inner_params(data, n=0):
        for arr in data:
            if isinstance(arr, str):
                ans.append(dumps(arr) + _str)
            elif isinstance(arr, dict):
                ans.append(dumps(arr, separators=(',', ':')) + _str)
            elif isinstance(arr, list):
                inner_params(arr, n + 1)

    inner_params(request_data, n=0)
    return ''.join(ans)

def get_domain(env):
    '''解析域名'''
    config = {
        'dev': 'http://nacos-dev.jlgltech.com',
        'rc': 'http://nacos-rc.jlgltech.com',
        'prod': 'http://nacos.jlgltech.com'
    }
    return config.get(env) if config.get(env) else config.get('dev')


def get_nacos_url(server_name, env):
    '''解析nacos URL'''
    _path = '/nacos/v1/ns/instance/list?serviceName='
    return get_domain(env=env) + _path + server_name.strip()

def get_rpc_url(server_name, uri, env='dev'):
    '''远程接口获取数据'''
    nacos_url = get_nacos_url(server_name, env)
    response = requests.get(url=nacos_url, headers=headers)
    try:
        hosts = response.json().get('hosts')[0]

        if all([hosts.get('enabled'), hosts.get('healthy')]):
            iurl = f'http://{hosts.get("ip")}:{hosts.get("port")}/feign-inner/{uri}'
            return iurl
    except Exception as e:
        print(e)


def get_lesson_score(server_name, uri, params, env):
    url = get_rpc_url(server_name, uri=uri, env=env)

    data = requests.post(url=url, data=params_to_string(params), )
    # print(data.json())
    try:
        return data.json().get('data')
    except Exception as e:
        raise Exception('RPC-API-ERROR')


if __name__ == '__main__':
    serverName = 'course.course.atom'
    nacos = get_nacos_url(serverName, env='dev')
    uri = 'com.jiliguala.phoenix.course.courseatom.feign.LessonFeignClient/getBabyLessonInfo/StringString'
    url = get_rpc_url(serverName, uri=uri, env='dev')
    print(nacos, )
    print(url, )