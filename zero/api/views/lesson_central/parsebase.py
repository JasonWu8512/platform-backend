# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/18 6:56 下午
@Author  : Demon
@File    : parsebase.py
"""
from numpy import int32
import math

def hashCode(val):
    h = 0
    if h == 0 and len(val) > 0:
        for i in range(len(val)):
            h = int32(31*h) + ord(val[i])
    return abs(h)

def get_db_rules_by_uid(uid, env='dev'):
    '''db取库规则'''
    pre = 'eduplatform'
    if env in ('rc', 'prod'):
        return pre + str(int(hashCode(val=uid, ) % 8 + 1))
    elif env in ('dev', 'local', 'fat'):
        return pre + str(int(hashCode(val=uid, ) % 2))


def get_tb_rules_by_uid(table, uid, env='dev'):
    '''tb后缀取表规则'''
    if env in ('rc', 'prod'):
        return table + str(int((hashCode(val=uid)/8) % 16))
    elif env in ('dev', 'local', 'fat'):
        print(hashCode(val=uid))
        return table + str(int(math.floor(hashCode(val=uid) / 2) % 2))


def parse_db_tb(uid, table='', env='dev'):
    '''
    :param :uid bid/uid
    :param :table 表前缀
    :param :env 环境 prod/rc/local/dev/fat
    :return
    '''
    if not uid:
        raise Exception('请输入uid')
    dbs = get_db_rules_by_uid(uid, env=env)
    tbs = get_tb_rules_by_uid(table=table, uid=uid, env=env)
    return dbs, tbs

