# -*- coding: utf-8 -*-
"""
@Time    : 2021/5/12 10:09 下午
@Author  : Demon
@File    : tasks.py
"""
import os

from zero.celery import app
import logging

@app.task(name='lesson.sync_data_task')
def sync_data_task(params):
    logging.info(params)
    logging.info('------sync data starting--------')
    try:
        code = os.system(command=params)
    except Exception as e:
        logging.error(f'sync data failed:{e}')
    finally:
        logging.info('------sync data ended--------')
    return 'code'

# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
# import time
# class InterfaceData():
#
#     @staticmethod
#     async def sync_data_crm(request):
#         loop = asyncio.get_event_loop()
#         time.sleep(3)
#         loop.run_in_executor(None, os.system, 'echo "nsmae\nksau">text.sh')
