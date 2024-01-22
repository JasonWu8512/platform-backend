# -*- coding: utf-8 -*-
"""
@Time    : 2020/12/27 8:39 下午
@Author  : Demon
@File    : tasks.py
"""


import logging
from zero.celery import app

from zero.warehouse.monitor_data import *
from zero.utils.enums.CheckTypeEnums import CheckTypeEnums
from zero.warehouse.sql_helper import SQLCommonConfig, DBSqlFunction


@app.task(bind=True)
def count_chain_ratio_by_date(self, params):
    """计算环比：按天/月
    params :{
        "dbname": "", "tbname": "", "part_flag": 1, "part_field": "dt",
        "rule_logic_monitor": { whereby: "stat_date", chain_ratio: "day/month/year" , lowerLimit: -0.5, upperLimit: 0.5}
    }
    SELECT
            "2021-01-07" AS stat_date,
             COUNT(*)  AS post_counts
         FROM jlgl_rpt.rpt_traffic_reading_new_user_add_d AS t
         WHERE dt = "20210107" AND stat_date = "2021-01-07"
    """
    sql = SQLCommonConfig(params=params, field_clause='COUNT(*) AS post_counts')
    # print(sqls.where_clause)
    print(sql.get_sql)
    r_threshold = params.get('rule_logic_monitor').get('upperLimit')
    l_threshold = params.get('rule_logic_monitor').get('lowerLimit')
    threshold_check(sql=sql.get_sql, params=params,
                    r_threshold=r_threshold if r_threshold else 0.5,
                    l_threshold=l_threshold if l_threshold else -0.5, )


@app.task(bind=True)
def count_repeat_ratio_by_date(self, params):
    """计算字段UNIQUE: 100-100 不能重复
    params :{
        "dbname": "db", "tbname": "tb", "part_flag": 1, "part_field": "dt",
        "rule_logic_monitor": { "whereby": "stat_date", "chain_ratio": "day/month/year" , "lowerLimit": -0.5, "upperLimit": 0.5},
        "field_name": ["register_from", "platform"]
    }
    """
    com = DBSqlFunction()
    field = ' , '.join([f'{com.distinct_count(_)} / {com.count()} AS {_}_ratio' for _ in params.get('field_name')])
    sql = SQLCommonConfig(params=params, field_clause=field)
    # 从数据获取数据
    r_threshold = params.get('rule_logic_monitor').get('upperLimit')
    l_threshold = params.get('rule_logic_monitor').get('lowerLimit')
    threshold_check(sql=sql.get_sql, params=params,
                    r_threshold=r_threshold if r_threshold else 0.5,
                    l_threshold=l_threshold if l_threshold else -0.5, )


@app.task()
def content_effective_by_date(params):
    """计算字段是否符合业务定义有效占比  100-100：全部有效
    SELECT
            "2021-01-07" AS stat_date,
            SUM(IF( stat_date REGEXP("abwe21342") , 1, 0)) / COUNT(*) AS stat_date_effective_ratio
         FROM jlgl_rpt.rpt_traffic_reading_new_user_add_d AS t
         WHERE dt = "20210107" AND stat_date = "2021-01-07"
    """
    com = DBSqlFunction()
    effective_field = [f"SUM(IF({com.regex(_[0], _[1])}, 1, 0)) / COUNT(*) AS {_[0]}_effective_ratio"
                       for _ in zip(params.get("field_name"), params.get('rule_logic_monitor').get("field_rule"))]
    sql = SQLCommonConfig(params=params, field_clause=effective_field)
    # 从数据获取数据
    r_threshold = params.get('rule_logic_monitor').get('upperLimit')
    l_threshold = params.get('rule_logic_monitor').get('lowerLimit')
    threshold_check(sql=sql.get_sql, params=params,
                    r_threshold=r_threshold if r_threshold else 0.5,
                    l_threshold=l_threshold if l_threshold else -0.5, )
    # SUM(IF(register_source REGEXP("呱呱"), 0, 1)) AS not_regexp_count


@app.task()
def enum_check_by_date(params):
    """
    判断表中字段数据 是否等于枚举值集合
    """
    sqls = []
    for field in params.get("field_name"):
        effective_field = f" DISTINCT {field} AS {0}_enums"
        sql = SQLCommonConfig(params=params, field_clause=effective_field)
        sqls.append(sql)
    enums_check(sqls=sqls, params=params,)


@app.task()
def count_field_length_by_date(params):
    """检验数据字段长度限制问题"""
    '''
    select sum(if(length(rule_name) > 0 and length(rule_name) < 3, 0, 1))
    '''
    field_name = params.get("field_name")
    field_rule = params.get('rule_logic_monitor').get("field_rule")
    _fil = [f'SUM(IF(LENGTH({_[0]})<={int(_[1][1])} AND LENGTH({_[0]})>{int(_[1][0])})) AS {_[1][0]}_length_count_ratio'
              for _ in zip(field_name, field_rule)]
    sql = SQLCommonConfig(params=params, field_clause=' , '.join(_fil))
    print(sql.get_sql)
    count_null_length_check(sql=sql.get_sql, params=params, code_='LENGTH_CHECK')


@app.task()
def count_is_null_by_date(params):
    """检验数据字段是否为空问题"""
    '''
    select sum(isnull(field))
    '''
    field_name = params.get("field_name")
    # field_rule = params.get('rule_logic_monitor').get("field_rule")
    _fil = [f'SUM(ISNULL({_})) AS {_[1][0]}_is_null_ratio' for _ in field_name]
    sql = SQLCommonConfig(params=params, field_clause=' , '.join(_fil))
    print(sql.get_sql)
    count_null_length_check(sql=sql.get_sql, params=params, code_='NOT_NULL_CHECK')


def user_defined_check_func(params):
    pass


def dispatch(monitor_type):
    # 注册监控方法
    mapping = {
        # "yearOnyear": count_chain_ratio_by_date, # 计算同比
        "chainRatio": count_chain_ratio_by_date, # 计算环比
        "enumContainCheck": enum_check_by_date, # 枚举包含关系
        "enumEqualCheck": enum_check_by_date, # 枚举相等关系
        # "logicCheck": count_chain_ratio_by_date, # 业务逻辑
        # "crossCheck": count_chain_ratio_by_date, # 数据冲突等
        "repeat": count_repeat_ratio_by_date, # 主键/等字段重复检查
        "existNull": count_is_null_by_date, # 字段是否为空
        "lengthOfValidity": count_field_length_by_date, # 字段长度有效
        "contentOfValidity": content_effective_by_date, # 内容检查，正则
        # "rangeOfValidity": count_chain_ratio_by_date, # 指定值的有效范围，最大最小等
        "userDefinedFunction": user_defined_check_func, # udf
        # 枚举值校验
    }
    if not mapping.get(monitor_type):
        raise Exception("Error monitor type")
    return mapping.get(monitor_type)