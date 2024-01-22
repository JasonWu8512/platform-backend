# -*- coding: utf-8 -*-
# @Time    : 2020/11/9 1:08 下午
# @Author  : zoey
# @File    : format.py
# @Software: PyCharm
import re
import time
import datetime
import calendar
import base64
from datetime import timedelta
from zero.jira.commands import JiraBugPoint


def get_default_value_by_type(instance):
    type_value = {
        'dict': {},
        'str': '',
        'list': [],
        'NoneType': None
    }
    type_str = type(instance).__name__
    print(type)
    return type_value.get(type_str)

def mode_number(a, b, decimal: int = 2):
    if b:
        return round((a or 0)/b, decimal)
    else:
        return 0

def get_data(data: dict, *keys, optional=True, pop=False):
    """
    从 dict 数据中批量获取变量，比如：
    task_id, status, err_msg = get_data(self.filtered, 'task_id', 'task_status', 'err_msg')
    """
    if optional:
        if pop:
            return [data.pop(key, None) for key in keys]
        else:
            return [data.get(key) for key in keys]
    else:
        if pop:
            return [data.pop(key) for key in keys]
        else:
            return [data[key] for key in keys]


def second_2_days(estimate: int):
    """把估时秒转为天"""
    if estimate:
        day = round(estimate / (3600 * 8), 3)
        return day
    return 0


def get_point_by_buglevel(buglevel: str):
    if buglevel:
        return JiraBugPoint.get_chinese(buglevel)
    else:
        return 0


def merge_2_dict_list(l1: list, l2: list, merge_key: str = None):
    '''根据指定key，合并两个list及dict'''
    l3 = []
    if not l1:
        return l2
    elif not l2:
        return l1
    elif l1 and l2 and merge_key:
        l1_keys = l1[0].keys()
        l2_keys = l2[0].keys()
        l1_mergekey_values = [data[merge_key] for data in l1]
        l2_mergekey_values = [data[merge_key] for data in l2]
        # 相同的mergekey_value
        same_values = set(l1_mergekey_values) & set(l2_mergekey_values)
        # 合并相同mergekey 的dict，且从各自list中pop
        for value in same_values:
            index1 = l1_mergekey_values.index(value)
            index2 = l2_mergekey_values.index(value)
            l3.append({**l1.pop(index1), **l2.pop(index2)})
            l1_mergekey_values.pop(index1), l2_mergekey_values.pop(index2)

        # l1中有l2中没有的key
        l2_need_keys = list(set(l1_keys).difference(set(l2_keys)))
        l1_need_keys = list(set(l2_keys).difference(set(l1_keys)))
        for l1_left in l1:
            l3.append({**l1_left, **{key: None for key in l1_need_keys}})
        for l2_left in l2:
            l3.append({**l2_left, **{key: None for key in l2_need_keys}})
        return l3
    return


def dateToTimeStamp(day=0, hour=0, min=0):
    """获取指定时间的时间戳"""
    dt = (datetime.datetime.now() + datetime.timedelta(days=day, hours=hour, minutes=min)).strftime("%Y-%m-%d %H:%M:%S")
    timeArray = time.strptime(dt, "%Y-%m-%d %H:%M:%S")
    timeStamp = time.mktime(timeArray)
    return timeStamp * 1000


def timeStampToTimeStr(time_stamp: int):
    """时间戳转换成时间字符串"""
    if time_stamp == None:
        return None
    time_local = time.localtime(time_stamp // 1000)
    time_str = time.strftime("%Y-%m-%dT%H:%M:%S", time_local)
    return time_str


def timeStampToDate(time_stamp: int):
    """时间戳转换成时间字符串"""
    if time_stamp == None:
        return None
    time_local = time.localtime(time_stamp // 1000)
    date = datetime.datetime.strptime(time.strftime("%Y-%m-%dT%H:%M:%S", time_local), "%Y-%m-%dT%H:%M:%S")
    return date


def timeStampToDatetime(time_stamp: int):
    """时间戳转换成时间字符串"""
    if time_stamp == None:
        return None
    time_local = time.localtime(time_stamp // 1000)
    date = datetime.datetime.strptime(time.strftime("%Y-%m-%d", time_local), "%Y-%m-%d")
    return date


def datestrToDate(s: str):
    """日期字符串转date"""
    if s == None:
        return None
    return datetime.datetime.strptime(s, "%Y-%m-%d")


def timestrToDatetime(s: str):
    """时间字符串转datetime"""
    if s == None:
        return None
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.000+0800")


def get_date_any(n=0):
    """
    :param n: 与当前日期的天数差，如n=-1时，获取前一天日期，
    :return:
    """
    return (datetime.datetime.now() + timedelta(days=n)).strftime("%Y-%m-%d")


def get_month_start_end(year, month):
    # 获取当前月的第一天的星期和当月总天数
    weekDay, monthCountDay = calendar.monthrange(year, month)
    # 获取当前月份第一天
    firstDay = datetime.datetime(year, month, day=1)
    # 获取当前月份最后一天
    lastDay = datetime.datetime(year, month, day=monthCountDay)
    # 返回第一天和最后一天
    return firstDay.strftime("%Y-%m-%d 00:00:00"), lastDay.strftime("%Y-%m-%d 23:59:59")


def get_special_month_start_end(n=0):
    """获得最近n月起始时间"""
    now = datetime.datetime.now()
    if now.month <= n:
        year = now.year - 1
        month = 12 - (n - now.month)
    else:
        year = now.year
        month = now.month - n
    start = datetime.datetime(year, month, 1).strftime("%Y-%m-%d 00:00:00")
    month = datetime.datetime(year, month, 1).month
    if n:
        end = (
                datetime.datetime(year + 1 if month == 12 else year, (month + 1) if month < 12 else (month - 11), 1)
                - timedelta(days=1)
        ).strftime("%Y-%m-%d 23:59:59")

    else:
        end = now.strftime("%Y-%m-%d 23:59:59")
    return {"start": start, "end": end, "xserie": "{}月".format(month)}


def get_three_month_start_end(year, month):
    """获取前后当月的第一天与最后一天"""
    days = {}
    # 获取当前月的第一天的星期和当月总天数
    weekDay, monthCountDay = calendar.monthrange(year, month)
    # 获取当前月份第一天
    first_day = datetime.datetime(year, month, day=1)
    # 获取当前月份最后一天
    last_day = datetime.datetime(year, month, day=monthCountDay)
    # 获取前一个月的最后一天
    last_day_of_pre_month = first_day - datetime.timedelta(days=1)
    # 获取前一个月第一天
    first_day_of_pre_month = datetime.date(last_day_of_pre_month.year, last_day_of_pre_month.month, 1)
    # 获取次月第一天
    first_day_of_next_month = first_day + datetime.timedelta(days=monthCountDay)
    # 获取次月最后一天
    days_num_of_next_month = calendar.monthrange(first_day_of_next_month.year, first_day_of_next_month.month)[1]
    last_day_of_next_month = datetime.date(first_day_of_next_month.year, first_day_of_next_month.month,
                                           days_num_of_next_month)
    days.update({"current_month_first_day": first_day, "current_month_last_day": last_day,
                 "first_day_of_pre_month": first_day_of_pre_month, "last_day_of_pre_month": last_day_of_pre_month,
                 "first_day_of_next_month": first_day_of_next_month, "last_day_of_next_month": last_day_of_next_month})
    return days

def check_cron_format(cron_str):
    """检查cron表达式是否符合规范"""
    regEx = "^[ \t]*(@reboot|@yearly|@annually|@monthly|@weekly|@daily|@midnight|@hourly|((((([1-5]?[0-9])-)?([1-5]?[0-9])|\*)(/([1-5]?[0-9]))?,)*((([1-5]?[0-9])-)?([1-5]?[0-9])|\*)(/([1-5]?[0-9]))?)[ \t]+(((((2[0-3]|1[0-9]|[0-9])-)?(2[0-3]|1[0-9]|[0-9])|\*)(/(2[0-3]|1[0-9]|[0-9]))?,)*(((2[0-3]|1[0-9]|[0-9])-)?(2[0-3]|1[0-9]|[0-9])|\*)(/(2[0-3]|1[0-9]|[0-9]))?)[ \t]+(((((3[01]|[12][0-9]|[1-9])-)?(3[01]|[12][0-9]|[1-9])|\*)(/(3[01]|[12][0-9]|[1-9]))?,)*(((3[01]|[12][0-9]|[1-9])-)?(3[01]|[12][0-9]|[1-9])|\*)(/(3[01]|[12][0-9]|[1-9]))?)[ \t]+((((((1[0-2]|[1-9])|[Jj][Aa][Nn]|[Ff][Ee][Bb]|[Mm][Aa][Rr]|[Aa][Pp][Rr]|[Mm][Aa][Yy]|[Jj][Uu][Nn]|[Jj][Uu][Ll]|[Aa][Uu][Gg]|[Ss][Ee][Pp]|[Oo][Cc][Tt]|[Nn][Oo][Vv]|[Dd][Ee][Cc])-)?((1[0-2]|[1-9])|[Jj][Aa][Nn]|[Ff][Ee][Bb]|[Mm][Aa][Rr]|[Aa][Pp][Rr]|[Mm][Aa][Yy]|[Jj][Uu][Nn]|[Jj][Uu][Ll]|[Aa][Uu][Gg]|[Ss][Ee][Pp]|[Oo][Cc][Tt]|[Nn][Oo][Vv]|[Dd][Ee][Cc])|\*)(/((1[0-2]|[1-9])|[Jj][Aa][Nn]|[Ff][Ee][Bb]|[Mm][Aa][Rr]|[Aa][Pp][Rr]|[Mm][Aa][Yy]|[Jj][Uu][Nn]|[Jj][Uu][Ll]|[Aa][Uu][Gg]|[Ss][Ee][Pp]|[Oo][Cc][Tt]|[Nn][Oo][Vv]|[Dd][Ee][Cc]))?,)*((((1[0-2]|[1-9])|[Jj][Aa][Nn]|[Ff][Ee][Bb]|[Mm][Aa][Rr]|[Aa][Pp][Rr]|[Mm][Aa][Yy]|[Jj][Uu][Nn]|[Jj][Uu][Ll]|[Aa][Uu][Gg]|[Ss][Ee][Pp]|[Oo][Cc][Tt]|[Nn][Oo][Vv]|[Dd][Ee][Cc])-)?((1[0-2]|[1-9])|[Jj][Aa][Nn]|[Ff][Ee][Bb]|[Mm][Aa][Rr]|[Aa][Pp][Rr]|[Mm][Aa][Yy]|[Jj][Uu][Nn]|[Jj][Uu][Ll]|[Aa][Uu][Gg]|[Ss][Ee][Pp]|[Oo][Cc][Tt]|[Nn][Oo][Vv]|[Dd][Ee][Cc])|\*)(/((1[0-2]|[1-9])|[Jj][Aa][Nn]|[Ff][Ee][Bb]|[Mm][Aa][Rr]|[Aa][Pp][Rr]|[Mm][Aa][Yy]|[Jj][Uu][Nn]|[Jj][Uu][Ll]|[Aa][Uu][Gg]|[Ss][Ee][Pp]|[Oo][Cc][Tt]|[Nn][Oo][Vv]|[Dd][Ee][Cc]))?)[ \t]+((((([0-7]|[Ss][Uu][Nn]|[Mm][Oo][Nn]|[Tt][Uu][Ee]|[Ww][Ee][Dd]|[Tt][Hh][Uu]|[Ff][Rr][Ii]|[Ss][Aa][Tt])-)?([0-7]|[Ss][Uu][Nn]|[Mm][Oo][Nn]|[Tt][Uu][Ee]|[Ww][Ee][Dd]|[Tt][Hh][Uu]|[Ff][Rr][Ii]|[Ss][Aa][Tt])|\*)(/([0-7]|[Ss][Uu][Nn]|[Mm][Oo][Nn]|[Tt][Uu][Ee]|[Ww][Ee][Dd]|[Tt][Hh][Uu]|[Ff][Rr][Ii]|[Ss][Aa][Tt]))?,)*((([0-7]|[Ss][Uu][Nn]|[Mm][Oo][Nn]|[Tt][Uu][Ee]|[Ww][Ee][Dd]|[Tt][Hh][Uu]|[Ff][Rr][Ii]|[Ss][Aa][Tt])-)?([0-7]|[Ss][Uu][Nn]|[Mm][Oo][Nn]|[Tt][Uu][Ee]|[Ww][Ee][Dd]|[Tt][Hh][Uu]|[Ff][Rr][Ii]|[Ss][Aa][Tt])|\*)(/([0-7]|[Ss][Uu][Nn]|[Mm][Oo][Nn]|[Tt][Uu][Ee]|[Ww][Ee][Dd]|[Tt][Hh][Uu]|[Ff][Rr][Ii]|[Ss][Aa][Tt]))?))[ \t]*$"
    if (re.match(regEx, cron_str)):
        return True
    else:
        return False


def basic_auth(id, tok):
    code = base64.b64encode(f'{id}:{tok}'.encode('utf-8'))
    return 'Basic ' + str(code, encoding="utf-8")


def now_timeStr():
    """获取当前时间的字符串形式"""
    dt = time.localtime(time.time())
    time_str = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", dt)
    return time_str
