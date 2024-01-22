# -*- coding: utf-8 -*-
# @Time    : 2021/2/4 5:32 下午
# @Author  : zoey
# @File    : commands.py
# @Software: PyCharm
from zero.jira.commands import jiraTool

default_deactive_time = '1970-01-01'

class Node(object):
    """
    构造节点
    """

    def __init__(self, parent, name, id):
        self.parent = parent
        self.name = name
        self.id = id


def build_tree(nodes, parent):
    """
    将树形列表构建dict结构
    :param nodes: 查询的节点列表
    :param parent: 当前节点父节点
    :return:
    """
    # 用来记录该节点下所有节点列表
    node_list = list()
    # 用于构建dict结构
    tree = list()
    build_tree_recursive(tree, parent, nodes, node_list)
    return tree


def build_tree_recursive(tree, parent, nodes, node_list):
    """
    递归方式构建
    :param tree: 构建dict结构
    :param parent: 当前父节点
    :param nodes: 查询节点列表
    :param node_list: 记录该节点下所有节点列表
    :return:
    """
    # 遍历循环所有子节点
    children = [n for n in nodes if n.parent == parent]
    node_list.extend([c.name for c in children])
    for child in children:
        # 子节点内创建新的子树
        value = {'id': child.id, 'name': child.name, 'children': []}
        tree.append(value)
        # 递归去构建子树
        build_tree_recursive(tree[-1]['children'], child, nodes, node_list)


def make_mode_list(module_list):
    """
    json形式生成一个个node对象，且关联父节点
    :param menu_list: 序列化后的菜单表
    :return:
    """
    # 返回node
    root_dict = {}
    while module_list:
        item = module_list.pop()
        pid = item.get("parent_open_department_id")
        if pid == '0':
            root_dict[item.get("open_department_id")] = Node(None, item.get("name"), item.get("open_department_id"))
            continue
        parent = root_dict.get(pid)
        if not parent and pid != '0':
            module_list.insert(0, item)
            continue
        root_dict[item.get("open_department_id")] = Node(parent, item.get("name"), item.get("open_department_id"))
    return list(root_dict.values())