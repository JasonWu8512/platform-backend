# -*- coding: utf-8 -*-
# @Time    : 2020/12/1 4:56 下午
# @Author  : zoey
# @File    : fabfile_mock.py
# @Software: PyCharm
from fabric.api import *

ip_dict = {
    'dev': {
        'payatom': ['10.100.112.201', '10.100.160.10'],
        '交易中台': ['10.100.160.17', '10.100.112.113']
    },
    'fat': {
        'payatom': ['10.100.128.49'],
        '交易中台': ['10.100.128.44']
    }
}


def get_mock_status(env):
    datas = []
    if env not in ['dev', 'fat']:
        raise (f'环境{env}不在可选范围内')
    try:
        for key, values in ip_dict[env].items():
            for ip in values:
                data = local(f'ssh root@{ip} cat /etc/hosts', capture=True)
                datas.append({f'{key}-{ip}': data})
        return datas

    except Exception as e:
        raise e


def switch_mock_host(env, status, server: list = ['payatom']):
    if env not in ['dev', 'fat']:
        raise (f'环境{env}不在可选范围内')
    try:

        for key, values in ip_dict[env].items():
            if key in server:
                for ip in values:
                    local(f'ssh root@{ip} "sed -i \'/api.pingxx.com/d\' /etc/hosts"')
                    if status:
                        local(f'ssh root@{ip} "echo 10.100.128.143 api.pingxx.com >> /etc/hosts"')
                    if key == 'payatom':
                        local(f'ssh root@{ip} "supervisorctl restart jlgl-payatom-server"')
                    elif key == '交易中台':
                        local(f'ssh root@{ip} "supervisorctl restart trade-order-server"')
    except Exception as e:
        raise e
