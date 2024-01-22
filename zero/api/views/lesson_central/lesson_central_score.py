# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/16 8:49 下午
@Author  : Demon
@File    : lesson_central_score.py
"""
import os
import json
from zero.api.decorators import login_or_permission_required
from zero.api import BaseViewSet
from zero.api.views.lesson_central.parsebase import parse_db_tb
from zero.api.views.lesson_central.rpc_lesson_score import get_lesson_score
import zero.utils.superResponse as Response
from rest_framework import serializers
from rest_framework.decorators import list_route
from zero.lesson_central import models
from django.views.decorators.csrf import csrf_exempt
import logging
from zero.api.views.lesson_central.tasks import sync_data_task
from zero.config.log_conf import LOG_DIR

class LessonScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LessonScore
        fields = ('server', 'uri', 'env', 'params')


class LessonScoreViewSet(BaseViewSet):

    serializer_class = LessonScoreSerializer

    @login_or_permission_required(['qa.edit'])
    @list_route(methods=['post'], url_path='get_lesson_score')
    def get_lesson_score(self, request):
        params = request.data.get('params')
        if not params:
            return Response.bad_request(message='请输入params')
        try:
            env = request.data.get('env')
            servers = request.data.get('server_name')
            uri_obj = models.RPCUri.objects.get(operation=request.data.get('operation'))
            data = get_lesson_score(
                server_name=servers,
                uri=uri_obj.uri,
                env='dev' if env == 'fat' else env,
                params=params if isinstance(params, list) else json.loads(params)
            )
            models.LessonScore.objects.create(params=params, data=data, server=servers, env=env, uri=uri_obj)
            return Response.success(data=data)
        except Exception as e:

            return Response.bad_request(data=str(e))

    @login_or_permission_required(['qa.edit'])
    @list_route(methods=['post'], url_path='get_name')
    def get_name(self, request):
        # 解析中台库存储uid数据规则
        uid = request.data.get('uid')
        env = request.data.get('env')
        if not uid:
            raise Exception('请输入uid')
        if not env:
            raise Exception('请输入环境')
        data = parse_db_tb(uid=uid, env=env, table=request.data.get('table'))

        return Response.success('.'.join(data))

    def mapping_ip_host(self, sync_action, env='fat'):
        # sync_action 同步动作映射服务器
        # ip_host_maps = {
        #     'ESSync_refund_order': {'dev': 'dev-crm-server0', 'fat': 'tx-fat-crm-server0'},
        #     'ESSync_student_math': {'dev': 'dev-crm-server0', 'fat': 'tx-fat-crm-server0'},
        #     'ESSync_student_english': {'dev': 'dev-crm-server0', 'fat': 'tx-fat-crm-server0'},
        #     'ESSync_app_performance': {'dev': 'dev-crm-server0', 'fat': 'tx-fat-crm-server0'},
        #     'ESSync_performance': {'dev': 'dev-crm-server0', 'fat': 'tx-fat-crm-server0'},
        # }
        ip_host_maps = {
            'fat': {'default': 'tx-fat-crm-server0'},
            'dev': {'default': 'dev-crm-server0'},
        }
        # sync_act = ip_host_maps.get(sync_action)
        # return sync_act.get(env) if sync_act else 'tx-fat-crm-server0'
        env_sync = ip_host_maps.get(env)
        if not env_sync:
            raise Exception('不支持除dev/fat之外的数据同步')

        return env_sync.get(sync_action) if env_sync.get(sync_action) else env_sync.get('default')

    def get_cmd_run_lines(self, operate):
        # 获取cmd执行命令
        mapping = {
            # 'ESSync_student': ['python3 /crm/srv/thrall/app/es/student_db_to_es.py init',
            #                    'python3 /crm/srv/thrall/app/es/math_student_db_to_es.py init'],
            'ESSync_student_math': ['python3 /crm/srv/thrall/app/es/math_student_db_to_es.py init'],
            'ESSync_student_english': ['python3 /crm/srv/thrall/app/es/student_db_to_es.py init'],
            'ESSync_app_performance': ['python3 /crm/srv/thrall/app/es/app_order_db_to_es.py init'],
            'ESSync_performance': ['python3 /crm/srv/thrall/app/es/cr_order_adoption_db_to_es.py init'],
            'ESSync_refund_order': ['python3 /home/deploy/fat_es_sync_data_temp.py'],
            # 规划师
            'ESSync_activity_info': ['python3 /crm/srv/jaina/app/es/activity_student_db_to_es.py init'],
            'ESSync_finish_info': ['python3 /crm/srv/jaina/app/es/finish_lesson_detail_db_to_es.py init'],
            'ESSync_no_person': ['python3 /crm/srv/jaina/app/es/unmatched_order_pro_db_to_es.py init'],
            'ESSync_youzan_order': ['python3 /crm/srv/jaina/app/es/youzan_order_pro_db_to_es.py init'],
            'ESSync_app_order': ['python3 /crm/srv/jaina/app/es/app_order_db_to_es.py init'],
            'ESSync_student_en_ghs': ['python3 /crm/srv/jaina/app/es/student_db_to_es.py init'],
            'ESSync_math_en_ghs': ['python3 /crm/srv/jaina/app/es/math_student_db_to_es.py init'],
            # 推广人
            'ESSync_prometer_info': ['python3 /crm/srv/jaina/app/es/promoter_db_to_es.py init'],

            # 客服
        }
        return mapping.get(operate)

    def get_sh_file_path(self, ismore=False):
        # 根据同步数据需要的步骤获取对应的sh
        # floder = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'es_sync_data_single.sh')
        file = 'es_sync_data.sh' if ismore else 'es_sync_data_single.sh'
        return os.path.join(os.path.split(os.path.abspath(__file__))[0], file)

    # @csrf_exempt
    # @login_or_permission_required(['qa.edit'])
    @list_route(methods=['post'], url_path='es_sync_data')
    def get_es_sync_data(self, request):
        # 数据同步功能
        env = request.data.get('env')
        try:
            operations = request.data.get('operation')
            ip_host = self.mapping_ip_host(sync_action=operations, env=env)  # 暂时使用默认fat-crmserver-ip
            # ip_host = 'tx-fat-crm-server0'
            if operations == 'ESSync_refund_order':
                # 订单同步支持两种方式，订单ID和时间
                orders = request.data.get('content')
                floder = self.get_sh_file_path(ismore=False)  # sh脚本绝对路径
                py_cmdline = self.get_cmd_run_lines(operations)[0]
                if orders:
                    order_param = ' '.join([_ for _ in orders])
                    py_cmdline = f'{py_cmdline} {order_param}'
                sh_cmdline = f'{floder} {ip_host} {py_cmdline}'
            else:
                py_cmdline = self.get_cmd_run_lines(operations)
                if len(py_cmdline) < 2:  # 一步执行
                    sh_cmdline = f'{self.get_sh_file_path(ismore=False)} {ip_host} {py_cmdline[0]}'
                else:
                    opera = ' '.join([_.split(' ')[1] for _ in py_cmdline])
                    sh_cmdline = f'{self.get_sh_file_path(ismore=True)} {ip_host} {opera}'
            print(sh_cmdline)
            sh_cmdline = sh_cmdline + f' >> {LOG_DIR}sync_sh.log'
            sync_data_task.apply_async(countdown=2, kwargs={'params': sh_cmdline})

            return Response.bad_request(message='数据同步中，请2min后查看结果，勿重复同步', data=sh_cmdline)
        except Exception as e:
            logging.error(e)
            logging.info('es_sync_exception_flat')
            logging.error(str(e))
            return Response.bad_request(message=str(e))
