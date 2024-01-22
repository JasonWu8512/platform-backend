# -*- coding: utf-8 -*-
# @Time    : 2020/10/22 9:57 上午
# @Author  : zoey
# @File    : tasks.py
# @Software: PyCharm
from zero.testTrack.models import TestPlanTree, TestPlanCase, ModuleTree
from zero.testTrack.siris import CaseTreeSerializer
from zero.testTrack.commands import build_tree, make_mode_list
from zero.celery import app
from meican import MeiCan, MeiCanLoginFail, NoOrderAvailable
import logging
import os


@app.task(bind=True)
def save_test_plan_tree(self, pid):
    # 获取该计划关联的所有用例取得tree_id集合
    origin_tree = TestPlanTree.query_first(**{'id': pid}).tree
    target_tree = []
    try:
        for proj in origin_tree:
            test_plan_case = TestPlanCase.query_all(**{'plan_id': pid, 'proj_id': proj.get('id')})
            tree_ids = list(set([item.tree_id for item in test_plan_case]))
            nodes = ModuleTree.objects.filter(id__in=tree_ids, parent__isnull=False).exclude(parent='')
            parents_ids = set(item.parent for item in nodes)
            # 循环取得一级节点
            while parents_ids:
                parent_nodes = ModuleTree.objects.filter(id__in=parents_ids)
                tree_ids.extend(list(parents_ids))
                parents_ids = set(item.parent for item in parent_nodes)
            nodes = ModuleTree.objects.filter(id__in=tree_ids)
            module_list = CaseTreeSerializer(nodes, many=True).data
            # 把tree_id列表转成节点列表
            node_list = make_mode_list(module_list)
            # 把列表转成前端需要的树状结构，并保存到mongo
            tree = build_tree(node_list, None)
            target_tree.append({**proj, **{'children': tree}})
        TestPlanTree.base_upsert(query={'id': pid}, **{'id': pid, 'tree': target_tree})
    except Exception as e:
        logging.error(f'{pid}:{e}')

@app.task()
def backup_mysql_database():
    # 备份mysql数据
    os.system('mysqldump -uroot -pZG$#RkbGdyZ3I0Nu zero > /home/deploy/log/zero/zero_mysql_$(date +%Y%m%d_%H%M%S).sql')

@app.task()
def order_dishes():
    import time
    try:
        meican1 = MeiCan('juanjuan_cheng@jiliguala.com', 'Cheng1234')  # login
        meican2 = MeiCan('zoey_zhang@jiliguala.com', 'Zshy1203')
        meican3 = MeiCan('keith_lu@jiliguala.com', 'Keith814')
        # meican4 = MeiCan('Jerry_zhu@jiliguala.com', 'Zwh19951116')
        for tab in meican3.tabs:
            time.sleep(10)
            try:
                dishes = meican3.list_dishes(tab)
                like_dishes = [dish for dish in dishes if dish.name.__contains__('中式套餐')]
                if like_dishes:
                    meican1.order(like_dishes[0])
                    meican2.order(like_dishes[0])
                    meican3.order(like_dishes[0])
                    # meican4.order(like_dishes[0])
                else:
                    print('今天没有宝钢食堂 :sad:')
            except Exception as e:
                print(e)
                continue
    except NoOrderAvailable:
        print('今天没有开放点餐')
    except MeiCanLoginFail:
        print('用户名或者密码不正确')

# order_dishes()