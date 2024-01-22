# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/8 5:07 下午
@Author  : Demon
@File    : sql_helper.py
"""

import arrow


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


class DBSqlFunction():
    def distinct_count(self, field):
        return f' COUNT(DISTINCT {field}) '

    def count(self, field='*'):
        return f' COUNT({field}) '

    def regex(self, field, rex):
        return f' {field} REGEXP(\"{rex}\") '


class SQLCommonConfig:
    def __init__(self, params, field_clause):
        self.params = params
        self.field_clause = field_clause
        self.dbname, self.tbname = params.get("dbname"), params.get("tbname")
        self.rule_logic_monitor = params.get("rule_logic_monitor")

    @property
    def part_field(self):
        # 是否分区
        return self.params.get("part_field")

    @property
    def from_clause(self):

        return f' FROM {self.dbname}.{self.tbname} AS t '

    @property
    def stat_date(self):
        return get_monitor_date(typ=self.rule_logic_monitor.get("chain_ratio"))

    @property
    def where_clause(self):
        where_dates = f'{self.rule_logic_monitor.get("whereby")} = "{self.stat_date}"'

        # 分区字段
        part_dates = ''
        if self.part_field:
            part_fmt = self.params.get('part_fmt')
            part_dates = f'{self.part_field} = "{get_any_offset_date(day=-1, fmt=part_fmt.upper())}"'
        where_by_sql = " WHERE " + " AND ".join(filter(lambda x: x, [part_dates, where_dates]))
        return where_by_sql

    # @property
    # def field_conf(self):
    #     distinct_field = [f"COUNT(DISTINCT {_}) / COUNT(*) AS {_}_repeat_ratio" for _ in self.params.get("field_name")]
    #     self.params.get("field_name")
    #     return

    @property
    def get_sql(self):
        sql = """
        SELECT 
            "{monitor_date}" AS stat_date,
            {field_clause}
        {from_clause}
        {where_clause} 
        {group_clause}
        """
        confs = dict(
            field_clause=self.field_clause,
            where_clause=self.where_clause,
            from_clause=self.from_clause,
            group_clause='',
            monitor_date=self.stat_date,
        )
        sql = sql.format(**confs)
        # sql = """
        # SELECT
        #     "{monitor_date}" AS stat_date,
        #     COUNT(*) AS post_counts,
        #     {distinct_field}
        # FROM {dbname}.{tbname} AS t
        # {whereby}
        # """.format(**dict(
        #     dbname=self.dbname,
        #     tbname=self.tbname,
        #     whereby=self.where_clause(),
        #     monitor_date=get_monitor_date(typ=self.rule_logic_monitor.get("chain_ratio")),
        #     distinct_field=" , ".join(distinct_field),
        # ))
        return sql


def count_chain_ratio_by_date(params):
    """计算环比：按天/月
    params :{
        "dbname": "", "tbname": "", "part_flag": 1, "part_field": "dt",
        "rule_logic_monitor": { whereby: "stat_date", chain_ratio: "day/month/year" , lowerLimit: -0.5, upperLimit: 0.5}
    }
    """
    com = DBSqlFunction()
    effective_field = [f"SUM(IF({com.regex(_[0], _[1])}, 1, 0)) / COUNT(*) AS {_[0]}_effective_ratio"
                       for _ in zip(params.get("field_name"), params.get('rule_logic_monitor').get("field_rule"))]
    sql = SQLCommonConfig(params=params, field_clause=' , '.join(effective_field))
    # print(sqls.where_clause)
    print(sql.get_sql)

def enum_data():
    return {"data": [
        ["name"],
        ["2021-01-07"],
        ["2021-01-04"],
        ["2021-01-05"],
        ["2021-01-06"],
    ]}


params = {
        "name": "jlgl_rpt_name145",
        "pre_table": "",
        "dbname": "jlgl_rpt",
        "tbname": "rpt_traffic_reading_new_user_add_d",
        "field_name": [],
        "rule_logic_monitor": {
            "whereby": "stat_date", "chain_ratio": "day", "lowerLimit": -0.5, "upperLimit": 0.5,
            # "field_rule": [['2021-01-07', '2021-01-04'], ['jsajsd', '312']]
            # "field_rule": ["abwe21342", "134314dasd"],
            "field_rule": [[0, 34], [0, 12]],
        },
        "part_field": "dt",
        "part_fmt": "yyyyMMDD",
        "task_desc": "",
        "warn_grad": 0,
        "is_active": 1,
        "term_id": "5",
        "cron_rule_id": 2,
        "one_off": False
    }


if __name__ == '__main__':
    com = DBSqlFunction()
    field = ' , '.join([f'{com.distinct_count(_)} / {com.count()} AS {_}_ratio' for _ in params.get('field_name')])
    sql = SQLCommonConfig(params=params, field_clause=field)