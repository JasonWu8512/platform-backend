# -*- coding: utf-8 -*-
# @Time    : 2020/10/21 10:09 上午
# @Author  : zoey
# @File    : commands.py
# @Software: PyCharm

from zero.utils.enums.jlgl_enum import ChineseEnum, ChineseTuple
from email.utils import parseaddr, formataddr
from email.header import Header
import smtplib


class CaseType(ChineseEnum):
    """用例类型"""
    FUNCTIONAL = ChineseTuple(('functional', '功能'))
    PERFORMANCE = ChineseTuple(('performance', '性能'))
    API = ChineseTuple(('api', '接口'))


class ReviewStatus(ChineseEnum):
    """"""
    PASS = ChineseTuple(('pass', '通过'))  # case的评审状态
    REJECT = ChineseTuple(('reject', '未通过'))  # case的评审状态
    INIT = ChineseTuple(('init', '待评审'))  # case的评审状态


class ProgressStatus(ChineseEnum):
    INIT = ChineseTuple(('init', '未启动'))  # 评审计划的评审状态
    INPROGRESS = ChineseTuple(('in_progress', '进行中'))  # 评审计划的评审状态
    DONE = ChineseTuple(('done', '已完成'))  # 评审计划的评审状态
    REJECT = ChineseTuple(('reject', '驳回'))  # 针对冒烟计划使用


class PlanStatus(ChineseEnum):
    INIT = ChineseTuple(('init', '未开始'))
    PASS = ChineseTuple(('pass', '通过'))  # case的执行状态
    FAIL = ChineseTuple(('fail', '失败'))  # case的执行状态
    BLOCK = ChineseTuple(('block', '阻塞'))
    SKIP = ChineseTuple(('skip', '跳过'))


class PlanStage(ChineseEnum):
    SMOKE = ChineseTuple(('smoke', '冒烟测试'))
    REGRESSION = ChineseTuple(('regression', '回归测试'))
    SYSTEM = ChineseTuple(('system', '系统测试'))


class PlanReportComponents(ChineseEnum):
    BaseInfo = ChineseTuple(('1', 'base_info'))
    Tickets = ChineseTuple(('2', 'tickets'))
    ModuleExecuteResult = ChineseTuple(('3', 'module_execute_result'))
    ExecuteTesult = ChineseTuple(('4', 'execute_result'))
    BugLevelCharts = ChineseTuple(('5', 'bug_level_charts'))
    BugOwnerCharts = ChineseTuple(('6', 'bug_owner_charts'))
    IssueList = ChineseTuple(('7', 'issue_list'))


class PlanInstanceStatus(ChineseEnum):
    INIT = ChineseTuple(('INIT', '未提交'))
    PENDING = ChineseTuple(('PENDING', '处理中'))
    APPROVED = ChineseTuple(('APPROVED', '已通过'))
    REJECTED = ChineseTuple(('REJECTED', '已驳回'))
    CANCELED = ChineseTuple(('CANCELED', '已取消'))


def PlanStatusCounter():
    status_counter = {}
    for status in PlanStatus:
        status_counter[status.value] = 0
    return status_counter


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
        value = {'id': str(child.id), 'name': child.name, 'children': []}
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
        pid = item.get("parent")
        if not pid:
            root_dict[item.get("id")] = Node(None, item.get("name"), item.get("id"))
            continue
        parent = root_dict.get(int(pid))
        if not parent:
            module_list.insert(0, item)
            continue
        root_dict[item.get("id")] = Node(parent, item.get("name"), item.get("id"))
    return list(root_dict.values())


def send_email(to_addrs:list, message):
    def _format_addr(s):
        name, addr = parseaddr(s)
        return formataddr((Header(name, 'utf-8').encode(), addr))
    smtp_server = 'smtp.feishu.cn'
    mail_user = "qa_develop@jiliguala.com" # 'zoey_zhang@jiliguala.com'  # 用户名
    mail_pass = "oPASmMZHLOHZkTkg" # "r7nuBZIq5l4qyP38"  # 口令
    message['From'] = _format_addr(f"Ace_boot<{mail_user}>")
    message['To'] = ','.join(_format_addr(x) for x in to_addrs)
    try:
        smtpObj = smtplib.SMTP()
        smtpObj.connect(smtp_server, 25)  # 25 为 SMTP 端口号
        smtpObj.login(mail_user, mail_pass)
        smtpObj.sendmail(mail_user, to_addrs, message.as_string())
    except Exception as e:
        print("Error: 无法发送邮件")
        raise e

# if __name__ == '__main__':
    # message = MIMEText('Python 邮件发送测试...', 'plain', 'utf-8')
    # subject = 'Python SMTP 邮件测试'
    # message['Subject'] = Header(subject, 'utf-8')
    # message.attach(MIMEText(f'<p><img src=f"" alt="image1"></p>'))
    # send_email('张莹', 'zoey_zhang@jiliguala.com', 'r7nuBZIq5l4qyP38', ['jerry_zhu@jiliguala.com'], message=message)