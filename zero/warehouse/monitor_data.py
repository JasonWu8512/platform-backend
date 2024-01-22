# !/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time : 2021/1/6 21:46
# @Author : Wolf
# @File : monitor_data.py
# @Project : zero

import json
import pandas as pd
from itertools import chain
from zero.utils.DB.api_big_data import BackOffQuery, mock_data
from zero.warehouse.models import MonitorResult, MonitorTableConfig, MonitorRules

def field_df_check_shold(df, r_threshold=1, l_threshold=-1):
    """字段级校验是否符合期望
    :param df: DataFrame
    :param r_threshold:
    :param l_threshold:
    :return Bool False: 存在异常数据
    """

    for col in df.columns:
        if col.endswith('_ratio'):
            df[col] = df[col].astype(float)
            if not df[(df[col] > r_threshold) | (df[col] < l_threshold)].empty:
                return False
    return True
    # tdf = df.iloc[:, 2:].T  # 矩阵转置


def table_df_check_shold(df, r_threshold=1, l_threshold=-1):
    """表级校验是否符合期望 表级字段名是默认没有 _ratio 标识
    :param df: DataFrame
    :param r_threshold:
    :param l_threshold:
    :return Bool
    """
    df['posts_ratio'] = df['post_counts'] / (df['post_counts'] - df['post_counts'].diff()) - 1
    df.fillna(0, inplace=True)
    # not_rule_df = df[(df['posts_ratio'] > r_threshold) | (df['posts_ratio'] < l_threshold)]
    for col in df.columns:
        if col.endswith('_ratio'):
            df[col] = df[col].astype(float)
            if not df[(df[col] > r_threshold) | (df[col] < l_threshold)].empty:
                return False
    return True


def threshold_check(sql, params, r_threshold=1, l_threshold=-1, code_="RANGE_THRESHOLD"):
    """
    获取最新监控数据，并更新记录
    :param sql:
    :param old_data:
    :param params:
    :param r_threshold:
    :param l_threshold:
    :param code_: 检测对应的结果后缀
    :return:
    """
    res = BackOffQuery(sql=sql)
    current_monitor_data = res.api_get_data()
    # current_monitor_data = mock_data(sql).get("data")
    conf = MonitorTableConfig.objects.get(name=params.get("name"))
    columns = current_monitor_data[0]
    # 将数据插入到数据库并读取最近三天数据，校验数据环比结果
    print("当前查询数据", current_monitor_data)
    new_data = pd.DataFrame(data=current_monitor_data[1:], columns=columns)
    new_data.sort_values(by='stat_date', inplace=True)
    olds_monitor_data = MonitorResult.objects.filter(task_id=conf.id).order_by("-id")

    if olds_monitor_data:
        # 对比历史数据并更新
        obj = olds_monitor_data[0]

        concat_df = pd.concat([new_data, pd.DataFrame(data=json.loads(obj.data)['data'], columns=columns)])
        concat_df.sort_values(by='stat_date', inplace=True)
        obj.__dict__.update(data=concat_df.to_json(orient='split'))

        if params.get('field_name'): # 字段级数据检查
            res = field_df_check_shold(df=concat_df[-1:].copy().fillna(0), r_threshold=r_threshold, l_threshold=l_threshold)
        else:
            res = table_df_check_shold(df=concat_df[-2:].copy().fillna(0), r_threshold=r_threshold, l_threshold=l_threshold)
        if res:
            obj.__dict__.update(is_normal=False, term_value=f"NORMAL_{code_}")
        else:
            obj.__dict__.update(is_normal=True, term_value=f"EXCEPTION_{code_}", )

        obj.save()
    else:
        # 直接创建
        MonitorResult.objects.create(
            task_id=conf.id,
            data=new_data.to_json(orient='split'),
            term_value=f"NORMAL_{code_}",
            is_normal=True,
        )

def contrast_list(field, first, base):
    ans = {
        f'{field}_more': set(first).difference(base),
        f'{field}_less': set(base).difference(first),
    }
    return ans


def enums_check(sqls, params,):
    """
    :param sqls: 多条sql
    :param params:任务配置
    :return
    """
    enenum = params.get('rule_logic_monitor').get('field_rule')
    enfield = params.get('field_name')
    obj = MonitorRules.objects.get(pk=params.get('term_id'))
    for index, sql in enumerate(sqls):
        res = BackOffQuery(sql=sql)
        current_monitor_data = res.api_get_data()
        # current_monitor_data = mock_data(sql).get("data")
        current_enums, enums_list = chain.from_iterable(current_monitor_data[1:]), enenum[index]
        ans = contrast_list(field=enfield[index], first=current_enums, base=enums_list)
        if obj.code == 'enumEqualCheck':
            if ans.get(f'{enfield[index]}_more') or ans.get(f'{enfield[index]}_more'):
                MonitorResult.objects.create(
                    term_value='EXCEPTION_EQUAL_CONTENT_ENUM',
                    data=json.dumps(ans),
                    is_normal=False,
                    task_id=MonitorTableConfig.objects.get(name=params.get('name')).id
                )
            else:
                MonitorResult.objects.create(
                    term_value='NORMAL_EQUAL_CONTENT_ENUM',
                    data=json.dumps(ans),
                    is_normal=True,
                    task_id=MonitorTableConfig.objects.get(name=params.get('name')).id
                )
        elif obj.code == 'enumContainCheck':
            if ans.get(f'{enfield[index]}_more'):
                # 存在不在枚举值内数据
                MonitorResult.objects.create(
                    term_value='EXCEPTION_CONTAIN_CONTENT_ENUM',
                    data=json.dumps(ans),
                    is_normal=False,
                    task_id=MonitorTableConfig.objects.get(name=params.get('name')).id
                )
            else:
                MonitorResult.objects.create(
                    term_value='NORMAL_CONTAIN_CONTENT_ENUM',
                    data=json.dumps(ans),
                    is_normal=True,
                    task_id=MonitorTableConfig.objects.get(name=params.get('name')).id
                )


def count_null_length_check(sql, params, code_):
    """字段长度/空值"""
    res = BackOffQuery(sql=sql)
    current_monitor_data = res.api_get_data()
    # current_data = mock_data(sql)
    df = pd.DataFrame(data=current_monitor_data[1:], columns=current_monitor_data[0])
    ans = field_df_check_shold(df, r_threshold=0, l_threshold=0)
    if ans:
        MonitorResult.objects.create(
            term_value=f'NORMAL_{code_}',
            data=json.dumps(ans),
            is_normal=df.to_json(orient='split'),
            task_id=MonitorTableConfig.objects.get(name=params.get('name')).id
        )
    else:
        MonitorResult.objects.create(
            term_value=f'EXCEPTION_{code_}',
            data=json.dumps(ans),
            is_normal=False,
            task_id=MonitorTableConfig.objects.get(name=params.get('name')).id
        )

