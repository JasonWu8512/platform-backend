# -*- coding: utf-8 -*-
"""
@Time    : 2021/6/10 6:11 下午
@Author  : Demon
@File    : buriedDeal.py
"""
import re
import json
import arrow
import logging
import datetime
import requests
from zero.api import BaseViewSet
import zero.utils.superResponse as Response
from urllib import parse
from copy import deepcopy
from zero.lesson_central.models import BuriedTestProject


class Elephant(object):
    def __init__(self, env):
        mapping = {
            'dev': 'http://10.9.4.124:8088',
            'fat': 'http://10.9.4.124:8088',
            'rc': 'http://givendata.jiliguala.com',
            'prod': 'http://givendata.jiliguala.com',
        }
        self.env = env
        self.host = mapping.get(self.env)
        resp = self.api_get_forever_token()
        self.headers = {'Authorization': f'Bearer {resp.get("data")}'}

    def api_get_forever_token(self):
        '''获取账号token
        http://10.9.5.23:9002/auth/getToken
        '''

        url = 'http://10.9.5.23:9002/auth/getToken' if self.env in ('rc', 'prod') else 'http://10.9.4.124:9002/auth/getToken'
        usr_pwd = {
            'dev': ['demon_jiao@jiliguala.com', 'PpiJlsYsn1'],
            'fat': ['demon_jiao@jiliguala.com', 'PpiJlsYsn1'],
            'rc': ['BuriedTest@jiliguala.com', 'zpimvd7w2s'],
            'prod': ['BuriedTest@jiliguala.com', 'zpimvd7w2s'],
        }
        body = {
            'username': usr_pwd.get(self.env)[0],
            'password': usr_pwd.get(self.env)[1]
        }
        resp = requests.post(url=url, json=body, verify=False)
        self.__api_check(resp)
        return resp.json()

    def api_get_project(self):
        # 查询象数埋点项目
        url = parse.urljoin(self.host, '/api_tracking/project/fetchList')
        resp = requests.get(url=url, verify=False, headers=self.headers)
        self.__api_check(resp=resp)
        return resp.json()

    def api_get_column_enums(self, projectId):
        # 列名枚举值
        url = parse.urljoin(self.host, '/api_tracking/event/fetchColumnEnums')
        body = {
            'columns': ["startVersion", "endVersion", "status"],
            'projectId': projectId
        }

        resp = requests.post(url=url, verify=False, json=body, headers=self.headers)
        self.__api_check(resp=resp)
        return resp.json()

    def __api_check(self, resp):
        message = '象数平台查询接口报错'
        if resp.status_code != 200:
            message = resp.json().get('message') if resp.json().get('message') else message
            raise Exception(message)
        if resp.json().get('info'):
            message = resp.json().get('info')
            raise Exception(message)

    def api_get_event_list(self, projectId, tagFilter, pageSize=20, currentPage=1, filter=None):
        url = parse.urljoin(self.host, '/api_tracking/event/fetchList')
        body = {
          "tagFilter": tagFilter,
          "isDeleted": False,
          "projectId": projectId,
          "batchType": None,
          "pageSize": pageSize,
          "currentPage": currentPage,
          "filter": filter,
          "orders": [
            {
              "column": "updateTime",
              "orderBy": "desc"
            }
          ]
        }
        resp = requests.post(url=url, verify=False, json=body, headers=self.headers)
        assert resp.status_code == 200
        self.__api_check(resp=resp)
        return resp.json()

    def get_default_data_config(self):
        '''默认七天内数据
        "type": "between",
        "granularity": "day",
        "date": ['20210419', '20210420']
        '''
        dateConfig = {
            "type": "last",
            "granularity": "day",
            "date": 1
            # "type": "between",
            # "granularity": "day",
            # "date": ['20210419', '20210420']
        }
        return dateConfig

    def api_get_user_event(self, uid, project_id, event_keys, platform):
        # 获取个人事件列表数据
        '''
        :param uid
        :param project_id
        :param eventKeys :[]
        '''
        url = parse.urljoin(self.host, '/api_bi/personProfile/fetchUserEvents')
        body = {
          "userId": uid,
          "projectId": project_id,
          "platform": platform,
          "eventKeys": event_keys,
          "dateConfig": self.get_default_data_config()
        }
        resp = requests.post(url=url, verify=False, json=body, headers=self.headers)
        self.__api_check(resp=resp)
        return resp.json()

    def api_person_fetch_users(self, uid, project_id):
        # 获取个人画像用户列表
        '''
        :param uid
        :param projectId
        '''
        url = parse.urljoin(self.host, '/api_bi/personProfile/fetchUsers')
        body = {
            "projectId": project_id,
            "filter": uid,
            "userGroup": "all",
            "platform": "all",
            "dateConfig": self.get_default_data_config()
        }
        resp = requests.post(url=url, verify=False, json=body, headers=self.headers)
        self.__api_check(resp=resp)
        return resp.json()

    def api_event_fetch_by_id(self, event_id):
        # 获取事件详情
        '''
        :param event_id
        '''
        url = parse.urljoin(self.host, '/api_tracking/event/fetchById')
        body = {
            "id": event_id
        }
        resp = requests.post(url=url, verify=False, json=body, headers=self.headers)
        self.__api_check(resp=resp)
        return resp.json()

    def api_fetch_event_props(self, project_id, uid, platform, event_id, dates, time_stamp):
        #获取事件属性
        url = parse.urljoin(self.host, '/api_bi/personProfile/fetchEventProps')
        body = {
            "projectId": project_id,
            "userId": uid,
            "platform": platform,
            "eventId": event_id,
            "date": dates,
            "timestamp": time_stamp
        }
        resp = requests.post(url=url, verify=False, json=body, headers=self.headers)
        self.__api_check(resp=resp)
        return resp.json()


class ClickHouseConnection():
    def __init__(self):
        self.conf = dict(
            host='10.18.2.19',
            database='ods',
            user='default',
            password='BBE^oKpHxt4VqcKp',
            send_receive_timeout=20,
            port=8123
        )

    # def query(self):
    #     client = Client(**self.conf)
    #     res = client.execute('show tables;')
    #     print(res.fetchall())

    def search(self, sqls):
        print(sqls)
        url = f'http://10.18.2.19:8123/?database=ods&user=default&password=BBE^oKpHxt4VqcKp&query={sqls}'
        return requests.get(url)


def get_off_set_time(base=None, days=0, hours=0, weeks=0, months=0, years=0, minutes=0, fmt='YYYY-MM-DD HH:mm:ss'):
    """ 获取偏移时间, 不传任何参数为当前时间
    :param base: 基准时间，str，默认当前时间，
    :param hour: 偏移小时，
    :param day: 偏移天数
    :param fmt: 时间的格式，YYYY-MM-DD HH:mm:ss
    :return: str
    """
    base = arrow.get(base) if base else arrow.get(datetime.datetime.now())
    # return (base + datetime.timedelta(days=day, hours=hour)).strftime(fmt)
    return arrow.get(base).shift(days=days, hours=hours, weeks=weeks, years=years, months=months, minutes=minutes).format(fmt=fmt)


def generate_table_configs(**kwargs):
    # 生成简单sql
    # self.mysql.query('SELECT * FROM students WHERE gua_id IN ()')
    base = 'SELECT date_partition,api_key,event_type,event_datetime,user_id,platform,event_id,user_properties,event_properties  FROM %s %s '
    rules = list()
    for arg, kw in kwargs.items():

        if isinstance(kw, str):
            rul = " %s = '%s'" % (arg, kw)
        elif isinstance(kw, int):
            rul = " %s = %d" % (arg, kw)
        elif iter(kw):
            rul = " %s IN (%s) " % (arg, ",".join(["'%s'" % item for item in kw]))
        rules.append(rul)
    is_where = " WHERE %s" % " AND ".join(rules) if rules else ""
    sql = base % ("ods_jlgl_amplitude_dis", is_where)
    orderd = f" AND event_datetime > '{get_off_set_time(minutes=-3)}' ORDER BY timestamp ASC;"
    # orderd = f" ORDER BY timestamp ASC;"
    return sql + orderd


class BuriedViewSet(BaseViewSet):
    def get_test_proj(self, proj_max):
        filters = BuriedTestProject.objects.filter(name__contains='^_^dev', deleted=0)
        test_proj = []
        for row in filters:
            proj_max += 1
            test_proj.append({
                'id': proj_max + 1,
                'apiKeyDesc': row.api_key_desc,
                'apiKey': row.api_key,
                'name': row.name,
                'platform': row.platform,
                'version': row.version,
                'isCrossProject': row.is_cross_project,
                'eventCount': 0,
                'eventPropertyCount': 0,
                'userPropertyCount': 0,
                'relateProjectIds': None,
                'relateIds': None,
                'commonProperties': [],
                'desc': row.name,
            })
        return test_proj

    def list_project(self, request, *args):
        # 获取项目
        env = request.data.get('env') if request.data.get('env') else 'dev'
        try:

            ep = Elephant(env=env)
            projects = ep.api_get_project()

            if isinstance(projects.get('data'), list):
                test_ = self.get_test_proj(max(map(lambda x:x.get('id'), projects['data'])))
                projects['data'] = projects['data'] + test_
            # print(projects)

        except Exception as e:
            logging.error(str(e))
            return Response.bad_request(message=str(e))
        return Response.success(data=projects)


class BuriedCheckViewSet(BaseViewSet):

    def _check_event_key(self, event_keys, respon):
        isperformanced = set()
        for day in respon:
            for event in day.get('events'):
                isperformanced.add(event.get('eventKey'))
        # data = [{'eventKey': _, 'result': '是' if _.get('event_key') in isperformanced else '否'} for _ in event_keys]
        for eve in event_keys:
            if eve.get('event_key') in isperformanced:
                eve['result'] = '是'
            else:
                eve['result'] = '否'
        return event_keys

    def get_event_property_from_ep(self, env, uid, project_id):
        '''从个人画像整合事件/属性'''
        # ep = Elephant(env=env)
        user_list = self.ep.api_person_fetch_users(uid=uid, project_id=project_id).get('data')
        if not user_list:
            # 在个人画像列表查不到行为历史
            return {}
        platform = user_list[0].get('platform')
        user_event = self.ep.api_get_user_event(
            uid=uid,
            project_id=project_id,
            event_keys=[],
            platform=platform,
        )
        user_event_N = user_event.get('data') if user_event.get('data') else []
        profile_user = {}
        utc_N = arrow.get(arrow.now()).shift(minutes=-3).format(fmt='HH:mm')
        for day_event in user_event_N:
            for event in day_event.get('events'):
                if event.get('eventTime') > utc_N: # 筛选3分钟内数据
                    event_id = event.get('eventKey')
                    event_info = self.ep.api_fetch_event_props(project_id=project_id, uid=uid,
                                         platform=platform, dates=event.get('date_partition'),
                                         event_id=event_id, time_stamp=event.get('timestamp')).get('data')
                    if not (event_id in profile_user):
                        profile_user[event_id] = list(event_info.get('eventProps').keys())
        # {event_key: [event_props]}
        return profile_user

    def get_event_info_from_ep_bury(self, event_keys):
        # 从埋点获取事件详情
        # ep = Elephant(env=env)
        for event in event_keys:
            resp = self.ep.api_event_fetch_by_id(event_id=event.get('id')).get('data')
            # info[event.get('eventKey')] = [_.get('propertyKey') for _ in resp.get('eventProperties')]
            event.update(**{'eventProperties': [_.get('propertyKey') for _ in resp.get('eventProperties')]})
        return event_keys

    def ck_data_format(self, res):
        # {"key": {"prop1": "propvalue"}}
        data = {}
        for name in res.text.split('\n'):
            params = name.split('	')
            if params and name:
                event_properies = json.loads(params[-1])
                user_properies = json.loads(params[-2])
                event_key = params[2]
                event_properies.update(**{'event^_^time': params[3], 'event^_^user_properties': user_properies})
                if event_key in data:
                    data[event_key].update(**event_properies)
                else:
                    data[event_key] = event_properies
        return data

    def get_event_property_from_ep_ck(self, uid, event_type, api_key):
        # 从ck查询数据
        logging.debug('get_event_property_from_ep_ck')
        event_type = [_.get('event_key') for _ in event_type]
        # env = env, uid = uid, project_id = project_id
        sqls = generate_table_configs(
            date_partition=get_off_set_time(fmt='YYYYMMDD'),
            api_key=api_key,
            user_id=uid if uid else 'NA',
            event_type=event_type
        )

        return self.ck_data_format(ClickHouseConnection().search(sqls))

    def check_enum(self, request, *args):
        # 埋点检查
        '''{
            uid: '',
            event_keys: ''
            project_id: ''
        }
        '''
        env = request.data.get('env') if request.data.get('env') else 'fat'

        try:
            uid = request.data.get('uid')
            # if not uid:
            #     raise Exception('input uid please')

            self.ep = Elephant(env=env)
            event_keys = request.data.get('event_keys')
            api_key = request.data.get('project_id')
            logging.debug('event_keys', event_keys)
            ep_event_and_propers = self.get_event_property_from_ep_ck(uid=uid, event_type=event_keys, api_key=api_key)
            ep_bury_event_info = self.get_event_info_from_ep_bury(event_keys=event_keys)
            # buried_result = self.compare_ck_and_buried_all(ep_event_and_propers, ep_bury_event_info)
            buried_result = self.compare_ck_and_buried(ck_data=ep_event_and_propers, bury_data=ep_bury_event_info)

            return Response.success(data=buried_result)

        except Exception as e:
            logging.error(str(e))
            return Response.bad_request(message=str(e))

    def compare_ck_and_buried(self, ck_data, bury_data):
        # ck and 埋点数据对比,以埋点的属性为准
        # print('bury_data', bury_data, )
        # print('ck_data', ck_data, )
        buried_result = []
        for event in bury_data:
            event_k = event.get('event_key')
            result = 'true' if event_k in ck_data else 'false'  # 埋点结果
            properties = ck_data.get(event_k) if ck_data.get(event_k) else {}
            ck_props = list(properties.keys()) if properties else []
            raw_properties = deepcopy(properties)
            if raw_properties.get('event^_^time'):
                raw_properties.pop('event^_^time', raw_properties)
            if raw_properties.get('event^_^user_properties'): # event^_^user_properties
                raw_properties.pop('event^_^user_properties', raw_properties)
            if not event.get('eventProperties'):
                check_data_row = {
                    'id': event.get('id'),
                    'eventKey': event_k,
                    'priority': event.get('priority'),
                    'name': event.get('name'),
                    'result': result,
                    'eventEventProper': '',
                    'eventEventProperValue': '',
                    'eventEventProperResult': '',
                    'eventTime': properties.get('event^_^time'),
                    'eventDesc': event.get('desc'),
                    'eventEventAllPropsCK': json.dumps(raw_properties) if raw_properties else '',
                    'eventUserAllPropsCK': json.dumps(properties.get('event^_^user_properties')) if 'event^_^user_properties' in properties else '',
                }
                buried_result.append(check_data_row)
            # print('profile_props', ck_props, properties, )
            for event_property in event.get('eventProperties'):
                eventProperValue = ''
                if properties and str(properties.get(event_property)) and properties.get(event_property) is not None:
                    eventProperValue = str(properties.get(event_property))
                check_data_row = {
                    'id': event.get('id'),
                    'eventKey': event_k,
                    'priority': event.get('priority'),
                    'name': event.get('name'),
                    'result': result,
                    'eventEventProper': event_property,
                    'eventEventProperValue': eventProperValue,
                    'eventEventProperResult': 'true' if (result == 'true') & (event_property in ck_props) else 'false',
                    'eventTime': properties.get('event^_^time') if properties else '',
                    'eventDesc': event.get('desc'),
                    'eventEventAllPropsCK': json.dumps(raw_properties) if raw_properties else '',
                    'eventUserAllPropsCK': json.dumps(properties.get('event^_^user_properties')) if 'event^_^user_properties' in properties else '',
                }
                buried_result.append(check_data_row)
        return buried_result

    def compare_ck_and_buried_all(self, ep_bury_event_info_ck, ep_bury_event_info):
        # ck and 埋点数据对比,展示所有属性
        # ep_bury_event_info_ck [[id,key,prop,prop_value]]
        # ep_bury_event_info [[id,key,prop]]
        print(ep_bury_event_info_ck,)
        print(ep_bury_event_info,)
        buried_result = []
        for event in ep_bury_event_info:
            event_k = event.get('event_key')
            result = 'true' if event_k in ep_bury_event_info_ck else 'false' # 埋点结果
            properties = ep_bury_event_info_ck.get(event_k)
            profile_props = list(properties.keys()) if properties else []

            if not event.get('eventProperties'):
                check_data_row = {
                    'id': event.get('id'),
                    'eventKey': event_k,
                    'priority': event.get('priority'),
                    'name': event.get('name'),
                    'result': result,
                    'eventProper': '',
                    'eventProperValue': '',
                    'eventProperResult': '',
                }
                buried_result.append(check_data_row)
            print('profile_props', profile_props)
            for event_property in event.get('eventProperties'):
                check_data_row = {
                    'id': event.get('id'),
                    'eventKey': event_k,
                    'priority': event.get('priority'),
                    'name': event.get('name'),
                    'result': result,
                    'eventProper': event_property,
                    'eventProperValue': properties.get(event_property) if properties else '',
                    'eventProperResult': 'true' if (result == 'true') & (event_property in profile_props) else 'false',
                }
                buried_result.append(check_data_row)
        return buried_result

    def compare_buried(self, ep_bury_event_info, ep_event_and_propers):
        # 检查个人画像和埋点
        buried_result = []
        for event in ep_bury_event_info:
            event_k = event.get('event_key')
            result = 'true' if event_k in ep_event_and_propers else 'false'
            profile_props = ep_event_and_propers.get(event_k) if ep_event_and_propers.get(event_k) else []

            if not event.get('eventProperties'):
                check_data_row = {
                    'id': event.get('id'),
                    'eventKey': event_k,
                    'priority': event.get('priority'),
                    'name': event.get('name'),
                    'result': result,
                    'eventProper': '',
                    'eventProperResult': '',
                }
                buried_result.append(check_data_row)

            for event_property in event.get('eventProperties'):
                check_data_row = {
                    'id': event.get('id'),
                    'eventKey': event_k,
                    'priority': event.get('priority'),
                    'name': event.get('name'),
                    'result': result,
                    'eventProper': event_property,
                    'eventProperResult': 'true' if (result == 'true') & (event_property in profile_props) else 'false',
                }
                buried_result.append(check_data_row)
        return buried_result


class BuriedColumnEnumsViewSet(BaseViewSet):
    def list_enum(self, request, *args):
        # 获取枚举值
        env = request.data.get('env') if request.data.get('env') else 'dev'
        projectId = request.data.get('project_id')
        if not projectId:
            return Response.bad_request(message='select project please')
        try:
            ep = Elephant(env=env)
            respEnums = ep.api_get_column_enums(projectId=projectId)
            return Response.success(data=respEnums)
        except Exception as e:
            logging.error(str(e))
            return Response.bad_request(message=str(e))


class BuriedEventViewSet(BaseViewSet):

    def formatter(self, src: str, firstUpper: bool=False):
        """
        将下划线分隔的名字,转换为驼峰模式
        :param src:
        :param firstUpper: 转换后的首字母是否指定大写(如
        :return:
        """
        arr = src.split('_')
        res = ''
        for i in arr:
            res = res + i[0].upper() + i[1:]

        if not firstUpper:
            res = res[0].lower() + res[1:]
        return res

    def list_event(self, request, *args):
        # 获取事件
        '''
        request.data {
            page_size: 20,
            project_id: 1,
            filter: None,
            current_page: 1,
            tag_filter: {status: []}
            search_text: ''
        }
        '''
        env = request.data.get('env') if request.data.get('env') else 'dev'
        projectId = request.data.get('project_id')
        if not projectId:
            return Response.bad_request(message='select project please')
        try:
            ep = Elephant(env=env)
            tag = request.data.get('tag_filter')
            tag_filter = {}
            # 框架数据驼峰字段转化
            for k in tag.keys():
                tag_filter[self.formatter(k)] = tag[k]
            version = {}
            if tag_filter.get('version'):
                for v in tag_filter.get('version').keys():
                    version[self.formatter(v)] = tag_filter['version'][v]
                tag_filter['version'] = version

            events = ep.api_get_event_list(
                projectId=projectId,
                currentPage=request.data.get('current_page'),
                pageSize=request.data.get('page_size'),
                filter=request.data.get('filter'),
                tagFilter=tag_filter
            )
            # print(request.data.get('tag_filter'), tag_filter)
            return Response.success(data=events)
        except Exception as e:
            logging.error(str(e))
            return Response.bad_request(message=str(e))



class BuriedAmpProfileViewSet(BaseViewSet):

    def get_sql(self, **kwargs):
        rules = list()
        for arg, kw in kwargs.items():

            if isinstance(kw, str):
                rul = " %s = '%s'" % (arg, kw)
            elif isinstance(kw, int):
                rul = " %s = %d" % (arg, kw)
            elif iter(kw):
                rul = " %s IN (%s) " % (arg, ",".join(["'%s'" % item for item in kw]))
            rules.append(rul)
        is_where = "WHERE %s" % " AND ".join(rules) if rules else ""
        return is_where + " AND  event_type <> '$identify' "

    def format_json(self, data):
        # data = data.replace('\\', '\\\\')
        re_ans = list(re.finditer('":', data))
        n = 0
        keys = []
        for ans in range(len(re_ans)):
            # print(re_ans[ans].span())
            span_str = data[: re_ans[ans].span()[0]]
            for i in range(len(span_str) - 1, n, -1):
                if span_str[i] == '"' and span_str[i - 1] != '\\':
                    re_key = span_str[i + 1: re_ans[ans].span()[1]]
                    if not re_key.endswith('jiliguala.com'):
                        keys.append(re_key)
                    break
            n = re_ans[ans].span()[1]
        key_sp = list(re.finditer('|'.join(keys), data))
        # print(keys)
        values = []
        for p in range(len(key_sp)):

            if p + 1 < len(key_sp):
                v = data[key_sp[p].span()[1] + 2: key_sp[p + 1].span()[0] - 2]
            else:
                v = data[key_sp[p].span()[1] + 2: -1]
            values.append(v)

        return dict(zip(keys, values))

    def to_json_data(self, json_str):
        logging.debug('to_json_data')
        try:
            # ans = json.loads(json_str.replace('\\\\', '\\'))
            ans = json.loads(json_str)
        except Exception as e:
            try:
                ans = self.format_json(json_str)
            except Exception as f:
                # print('ans', json_str)
                ans = {'eventProper': json_str}
        return ans

    def format_ck_data(self, ck_data):
        logging.debug(ck_data)
        # print(ck_data.text)
        data = []
        n = 0
        for name in ck_data.text.split('\n'):
            params = name.split('	')
            if params and name:
                event_properties = params[-1]
                user_properties = params[-2]
                event_key = params[2]
                # if event_properties != '{}':
                #     split_event = re.split('":"|","', event_properties)
                #     for i in range(0, len(split_event), 2):
                #         event_temp[split_event[i]] = split_event[i+1]
                data.append({
                    'event_key': event_key,
                    'uuid': params[-3],
                    'user_properties': json.loads(user_properties),
                    # 'event_properties': event_temp,
                    'event_properties': self.to_json_data(event_properties),
                    'event_datetime': params[1].split('.')[0] if params[1] else params[1],
                    'row': n,
                    'device_id': params[-4],
                })
                n += 1

        return data

    def combine_sql_condition(self, **kwargs):
        condition = dict()
        for k, v in kwargs.items():
            if v:
                condition[k] = v
        return self.get_sql(**condition)

    def get_events_by_uid(self, request, *args):
        request_data = request.data if request.data else request.GET
        user_id = request_data.get('uid') if request_data.get('uid') else 'NA'
        event_type = request_data.get('eventKey') if request_data.get('eventKey') else ''
        device_id = request_data.get('deviceId')
        base = 'SELECT date_partition,event_datetime,event_type,api_key,user_id,platform,device_id,uuid,user_properties,event_properties FROM ods_jlgl_amplitude_dis '
        # if event_keys:
        #     sql = self.get_sql(date_partition=get_off_set_time(fmt='YYYYMMDD'), user_id=uid, event_type=event_keys)
        # else:
        #     sql = self.get_sql(date_partition=get_off_set_time(fmt='YYYYMMDD'), user_id=uid, )
        sql_where = self.combine_sql_condition(
            date_partition=get_off_set_time(fmt='YYYYMMDD'),
            event_type=event_type, device_id=device_id, user_id=user_id,
        )
        if user_id == 'NA':
            sql = f'{base} {sql_where} ORDER BY `event_datetime` DESC LIMIT 200'
        else:
            sql = f'{base} {sql_where} ORDER BY `event_datetime` DESC LIMIT 200'
        # sql = base + " WHERE  date_partition = '20210723' AND event_type <> '$identify' " \
        #              "AND  api_key='76382ab7cc9f61be703afadc802bf276' order BY `event_datetime` DESC limit 1500"
        try:
            ck_data = self.format_ck_data(ClickHouseConnection().search(sqls=sql))
            # print(ck_data)
            return Response.success(data={'sql': sql, 'data': ck_data})
        except Exception as e:
            print(e)
            return Response.bad_request(message='ck连接超时', data=sql)

