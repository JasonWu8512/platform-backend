# -*- coding: utf-8 -*-
# @Time    : 2021/7/7 6:11 下午
# @Author  : zoey
# @File    : tasks.py
# @Software: PyCharm
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from zero.jira.models import CwdUser, JiraProject
from zero.organization.models import AceDepartment, AceDepartmentAccount, AceAccount
from zero.celery import app
from zero.user.models import User, UserAuthGroup, Group
import logging


@app.task()
def sync_user_from_jira():
    logging.info('---------同步jira用户到测试平台task start-------------------------')
    # 已经创建过的用户
    zero_users = User.objects.filter().order_by('username')
    zero_user_usernames = [user.username for user in zero_users]
    zero_user_ids = [user.id for user in zero_users]
    created_jira_users = CwdUser.objects.filter(user_name__in=zero_user_usernames).order_by('user_name')
    not_exist_users = CwdUser.objects.exclude(user_name__in=zero_user_usernames)
    bulk_create_users = []
    bulk_update_users = []
    for user in not_exist_users:
        bulk_create_users.append(User(id=user.id, email=user.lower_email_address, username=user.user_name, is_active=user.active, password=make_password('niuniuniu168')))
    User.objects.bulk_create(bulk_create_users, batch_size=200)
    for user in created_jira_users:
        if user.user_name in zero_user_usernames:
            index = zero_user_usernames.index(user.user_name)
            bulk_update_users.append(User(id=zero_user_ids[index], username=user.user_name, is_active=user.active, email=user.lower_email_address))
    User.objects.bulk_update(bulk_update_users, ['username', 'is_active', 'email'], batch_size=200)
    all_user_ids = CwdUser.objects.all().values_list('id', flat=True)
    User.objects.filter(last_login__isnull=True).exclude(id__in=list(all_user_ids)).delete()


@app.task()
def sync_user_groups():
    # permission = Permission.objects.get(codename='query', content_type_id=13)
    qa = Group.objects.get(name='qa')
    dev = Group.objects.get(name='dev')
    pm = Group.objects.get(name='pm')
    leader = Group.objects.get(name='leader')
    scrum_master = Group.objects.get(name='scrumMaster')
    # 技术部
    tech_open_department = 'od-6ac439ac289537cafd7d6e5cdff6a5e9'
    # 产品部
    product_open_department = 'od-e88a446342ff720acba17d4cc767f037'
    # 项目管理组
    proj_manager = AceDepartment.objects.get(name='项目管理组')
    # 技术部下所有部门
    tech_all_deparments = AceDepartment.objects.filter(
        parent_open_department_ids__contains=tech_open_department).values_list(
        'open_department_id', flat=True)
    # 产品部下所有部门
    product_all_departments = AceDepartment.objects.filter(
        parent_open_department_ids__contains=product_open_department).values_list('open_department_id', flat=True)
    zero_users = User.objects.filter().all()
    user_groups = []
    for user in zero_users:
        try:
            query_set = AceDepartment.objects.filter((Q(name__in=('技术部', '产品部', '项目管理组')) | Q(
                parent_open_department_ids__contains=tech_open_department)) & Q(
                leader_email=user.email))
            ace_account = AceAccount.objects.get(email=user.email)
            ace_account_department = AceDepartmentAccount.objects.filter(account_id=ace_account.id).values_list(
                'open_department_id', flat=True)
            # 判断是否leader
            if (len(query_set) or proj_manager.open_department_id in ace_account_department) and not len(UserAuthGroup.objects.filter(user_id=user.id, group_id=leader.id)):
                if leader.id not in [group.group_id for group in user.groups.constrained_target]:
                    user_groups.append(UserAuthGroup(user_id=user.id, group_id=leader.id))
            # 判断是否scrumMaster
            if len(JiraProject.objects.filter(lead=user.username)) and not len(
                    UserAuthGroup.objects.filter(user_id=user.id, group_id=scrum_master.id)):
                user_groups.append(UserAuthGroup(user_id=user.id, group_id=scrum_master.id))
            # 判断是否是QA
            if ace_account.user_role == 'QA' and not len(
                    UserAuthGroup.objects.filter(user_id=user.id, group_id=qa.id)):
                user_groups.append(UserAuthGroup(user_id=user.id, group_id=qa.id))
            # 判断是否是开发
            elif (set(list(ace_account_department)) & set(list(tech_all_deparments))) and ace_account.user_role != 'QA' and not len(
                    UserAuthGroup.objects.filter(user_id=user.id, group_id=dev.id)):
                user_groups.append(UserAuthGroup(user_id=user.id, group_id=dev.id))
            # 判断是否是产品
            elif (set(list(ace_account_department)) & set(list(product_all_departments))) and not len(
                    UserAuthGroup.objects.filter(user_id=user.id, group_id=pm.id)):
                user_groups.append(UserAuthGroup(user_id=user.id, group_id=pm.id))
        except Exception as e:
            logging.error(f'{user.username}{e}')
    UserAuthGroup.objects.bulk_create(user_groups, batch_size=200)