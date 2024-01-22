# -*- coding: utf-8 -*-
"""
@Time    : 2020/12/27 8:39 下午
@Author  : Demon
@File    : test.py
"""
#
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zero.settings")
import django
django.setup()
from zero.warehouse.models import MonitorTableConfig, MonitorRules
from zero.warehouse import tasks


from celery import task, Celery

import json
import arrow
import time
import datetime
import logging
# from zero.celery import app
# from zero.warehouse.models import MonitorTableConfig, MonitorResultCode
# from django_celery_beat.models import PeriodicTask
# from zero.utils.DB.api_big_data import BackOffQuery
import pandas as pd
import calendar
import datetime
from dateutil.parser import parse




def get_any_offset_date(base_date="", base_date_type="YYYY-MM-DD", month=0, day=0, hour=0, week=0, year=0, fmt=""):
    """获取偏移时间"""
    """ 
    :param base_date: 基准时间，str，默认当前时间，
    :param month: 偏移月，
    :param hour: 偏移小时，
    :param day: 偏移天数
    :param fmt: 偏移后时间的格式，"YYYY-MM-DD HH:mm:ss"
    :return: str
    """
    base = arrow.get(base_date, base_date_type) if base_date else arrow.now()
    fmt = fmt if fmt else "YYYY-MM-DD HH:mm:ss"
    return base.shift(days=day, hours=hour, months=month, weeks=week, years=year).format(fmt)


def get_monitor_date(typ="DAY"):
    """获取监控时间：昨天/上个月/去年"""
    if typ.upper() == "MONTH":
        return get_any_offset_date(month=-1, fmt="YYYY-MM")
    elif typ.upper() == "YEAR":
        return get_any_offset_date(year=-1, fmt="YYYY")
    elif typ.upper() == "WEEK":  # 时间区间，，，暂不支持
        return get_any_offset_date(week=-1)
    else:
        return get_any_offset_date(day=-1, fmt="YYYY-MM-DD")


# @app.task(name="zero.warehouse.tasks.count_chain_ratio_by_date")
def count_chain_ratio_by_date(params):
    """计算环比：按天/月
    params :{
        "dbname": "", "tbname": "", "part_flag": 1, "part_field": "dt",
        "rule_logic_monitor": { whereby: "stat_date", chain_ratio: "day/month/year" , lowerLimit: -0.5, upperLimit: 0.5}
    }
    """
    dbname, tbname = params.get("dbname"), params.get("tbname")
    rule_logic_monitor = params.get("rule_logic_monitor")
    r_threshold = rule_logic_monitor['upperLimit'] if rule_logic_monitor.get("upperLimit") else 0.5
    l_threshold = rule_logic_monitor['lowerLimit'] if rule_logic_monitor.get("lowerLimit") else -0.5
    # 根据传递的chain_date=day/month，分区拼接where条件
    # fmt = "%Y-%m" if rule_logic_monitor.get("rule_logic_monitor").upper() == "MONTH" else "%Y-%m-%d"
    where_dates = f'{rule_logic_monitor.get("whereby")} = "{get_monitor_date(typ=rule_logic_monitor.get("chain_ratio"))}"'
    part_dates = f'{params.get("part_field")} = "{get_any_offset_date(day=-1, fmt="YYYY-MM-DD")}"' if params.get("part_flag") else ""
    where_by_sql = " WHERE " + " AND ".join(filter(lambda x: x, [part_dates, where_dates]))
    print(where_by_sql)

    sql = """
    SELECT 
        "{monitor_date}" AS stat_date,
        COUNT(*) AS post_counts
    FROM {dbname}.{tbname} AS t
    {whereby} 
    """.format(**dict(
        dbname=dbname,
        tbname=tbname,
        whereby=where_by_sql,
        monitor_date=get_monitor_date(typ=rule_logic_monitor.get("chain_ratio")),
    ))
    print(sql)
    # 从数据获取数据
    # res = BackOffQuery(sql=sql)
    # current_monitor_data = res.api_get_data()
    # 将数据插入到数据库并读取最近三天数据，校验数据环比结果
    current_monitor_data = [["stat_date", "post_counts"], ["2021-01-05", 34]]

    # olds_monitor_data = MonitorResult.objects.get(name=params.get("name"))
    olds_monitor_data = '{"columns":["stat_date","post_counts"],"index":[1,0],"data":[["2021-01-02",88], ["2021-01-03",88],["2021-01-04",34]]}'
    # if olds_monitor_data
    concat_df = pd.concat([pd.DataFrame(data=current_monitor_data[1:], columns=current_monitor_data[0]),
                    pd.DataFrame(data=json.loads(olds_monitor_data)['data'],
                                 columns=current_monitor_data[0])]
                   )
    concat_df.sort_values(by='stat_date', inplace=True)
    df = concat_df[-2:].copy()

    df['posts_ratio'] = df['post_counts'] / (df['post_counts'] - df['post_counts'].diff()) - 1
    df.fillna(0, inplace=True)
    not_rule_df = df[(df['posts_ratio'] > r_threshold) | (df['posts_ratio'] < l_threshold)]
    print(df)
    if not not_rule_df.empty:  # 不符合正常轨迹
        # 0 ratio，代表为首个周期缺省
        print('not_rule_df不符合阈值', not_rule_df)
    #     olds_monitor_data.update(
    #         out_of_limits=olds_monitor_data.out_of_limits + 1,
    #         term_value="EXCEPTION_ROWCOUNT_CHAINRATE",
    #     )
    # else:
    #     olds_monitor_data.update(term_value="NORMAL_ROWCOUNT_CHAINRATE",)
    #
    # olds_monitor_data.update(data=concat_df.to_json(orient='split'))

if __name__ == '__main__':
    from zero.coverage.commands import jenkinsTool
    from zero.coverage.models import GitProject
    # GitProject.objects.create(
    #     name='jlgl-payatom',
    #     ssh_url = 'git@gitlab.jiliguala.com:backend/jlgl-payatom.git',
    #     server_ip = '10.10.69.25',
    #     server_port = '8890',
    #     fat_job_name = 'fat-backend/fat-backend-jlgl-payatom-server'
    # )
    jen = jenkinsTool.build_job("fat-backend/fat-backend-jlgl-payatom-server", params={})
    print(jen)

if __name__ == '__main__' or 1 == 1:
    params = {
        "name": "jlgl_rpt_name145",
        "pre_table": "",
        "dbname": "jlgl_rpt",
        "tbname": "rpt_traffic_reading_new_user_add_d",
        "field_name": ["stat_date"],
        "rule_logic_monitor": {
            "whereby": "stat_date", "chain_ratio": "day", "lowerLimit": -0.5, "upperLimit": 0.5,
            "field_rule": ["abwe21342", "134314dasd"]
        },
        "part_field": "dt",
        "part_fmt": "yyyyMMdd",
        "task_desc": "",
        "warn_grad": 0,
        "is_active": 1,
        "term_id": "5",
        "cron_rule_id": 2,
        "one_off": False
    }

    tasks.count_chain_ratio_by_date(params)

    # obj = MonitorRules.objects.get(task="name")

    # effective_field = [f"SUM(IF({_[0]} REGEXP(\"{_[1]}\"), 0, 1)) / COUNT(*) AS {_[0]}_effective_count" for _ in zip(params.get("field_name"), params.get("field_rule"))]
    #
    # print(" , ".join(effective_field))

    # df = pd.DataFrame(data=[['0102', 12, 1.0, 21], ], columns=['date', 'all', 'ab', 'ac'])
    # tdf = df.iloc[:, 2:].T
    # s = tdf[tdf[0] != 1]
    # if not s.empty:
    #     print("sdas")

    def mock_data():
        return {"data": [
            ["stat_date", "stat_date_repeat_ratio"],
            ["2021-01-07", "400"],
            # ["2021-01-04", "100"],
            # ["2021-01-05", "100"],
            # ["2021-01-06", "100"],
        ]}

    def df_check_shold(df, r_threshold=1, l_threshold=-1):
        """是否符合期望
        :param df: DataFrame
        :param r_threshold:
        :param l_threshold:
        :return Bool
        """
        print(df)
        for col in df.columns:
            if col.endswith('_ratio'):
                df[col] = df[col].astype(float)
                print(df.columns)
                if not df[(df[col] > r_threshold) | (df[col] < l_threshold)].empty:
                    return False
        return True


    df_check_shold(pd.DataFrame(data=mock_data()['data'][1:], columns=mock_data()['data'][0]))
