# -*- coding: utf-8 -*-
# @Time    : 2021/3/8 4:03 下午
# @Author  : zoey
# @File    : commands.py
# @Software: PyCharm
import re
import base64
from urllib import parse
import requests
from zero.settings import BASE_GIT_URL, GIT_APITOKEN
import shortuuid
import gitlab
# from zero.auto.models import *


class GitLabApi:
    header = {"private_token": GIT_APITOKEN}

    def __init__(self):
        self.gl = gitlab.Gitlab(BASE_GIT_URL, GIT_APITOKEN)
        self.project_id = self.get_project_id()

    def get_project_id(self, name='qa/tiga'):
        """
        :param name: 项目名称 NAMESPACE/PROJECT_NAME
        :return:
        """
        project_id = None
        name_code = parse.quote(name, safe='')
        res = requests.get("{}/api/v4/projects/{}".format(BASE_GIT_URL, name_code), data=self.header, verify=False)
        res.raise_for_status()
        content = res.json()
        if content:
            project_id = content.get('id')
        return project_id

    def get_tag_list(self, project_id=None, branch='develop'):
        """
        获取tiga项目中的标签列表
        :param project_id:
        :param branch:
        :return:
        """
        project_id = project_id or self.project_id
        file = self.get_file(project_id=project_id, dir='pytest.ini', branch=branch)
        lines = file.split('\n')
        tags = [line.strip(' ').split(':')[0] for line in lines if line.startswith('    ')]
        return tags

    def get_case_tree_list(self, dir, branch='develop', project_id=None):
        """返回目录下的所有子目录列表，树形方式children，name，直至function，用于展示用例库的树形结构"""
        project_id = project_id or self.project_id
        first_dir = dir.split('/')[0]
        if first_dir != 'testcase':
            dir = 'testcase/'+dir
        line_list = self.get_project_trees(project_id=project_id, path=dir, branch=branch)
        # 将原目录字符串列表转化成 列表列表，字符串按/split
        # line_list_list = []
        # for i in line_list:
        #     split_list = i.replace('::', '/').split('/')
        #     line_list_list.append(split_list)
        # sorted(line_list_list)
        # 先将dir组成起始case_tree
        dir_list = dir.split('/')
        def get_children(node):
            sz = []
            for item in line_list:
                if item.replace('::', '/').split('/')[:-1] == node.replace('::', '/').split('/'):
                    sz.append({"name": item.replace('::', '/').split('/')[-1], "children": get_children(item), "id": item})
            return sz

        def get_tree(j):
            case = []
            if j < len(dir_list)-1:
                case.append({"name": dir_list[j], "children": get_tree(j+1), "id": shortuuid.uuid()})
            else:
                case.append({"name": dir_list[j], "children": get_children(dir_list[j]), "id": dir_list[j]})
            return case

        case_list = get_tree(0)
        return case_list

    def get_project_trees(self, path, branch='develop', project_id=None):
        """
        :param project_id:
        :param path:
        :param branch:
        :return: path下面的递归子目录list
        """
        project_id = project_id or self.project_id
        tree = []
        if re.search('\.py', path):  # 如果原path是已经到文件层了,直接计算文件里的方法
            tree.extend(self.get_all_test_functions_from_file(project_id=project_id, file_path=path, branch=branch))
            return sorted(tree)
        data_tree = self.header
        data_tree['path'] = path
        data_tree['ref'] = branch
        data_tree['recursive'] = True
        # max
        data_tree['per_page'] = 100
        data_tree['page'] = 1
        resp = requests.get("{}/api/v4/projects/{}/repository/tree".format(BASE_GIT_URL, project_id), data=data_tree)
        resp.raise_for_status()
        content = resp.json()
        while len(resp.json()) == 100:
            data_tree['page'] += 1
            resp = requests.get("{}/api/v4/projects/{}/repository/tree".format(BASE_GIT_URL, project_id),
                                data=data_tree)
            resp.raise_for_status()
            content.extend(resp.json())
        if content:
            for item in content:
                # 查找test文件
                if not re.search('\.', item['name']):  # 目录
                    tree.append(item['path'])
                elif re.match(r'test[^/]*\.py', item['name'], re.I):  # 文件
                    tree.append(item['path'])
                    tree.extend(self.get_all_test_functions_from_file(project_id=project_id, file_path=item['path'], branch=branch))
        return sorted(tree)

    def get_all_test_functions_from_file(self, file_path, branch='develop', project_id=None):
        """
        获取文件下面的的全部test方法,格式：类名.方法名
        :param project_id:
        :param file_path:
        :param branch:
        :return:
        """
        project_id = project_id or self.project_id
        file = self.get_file(project_id=project_id, dir=file_path, branch=branch)
        # 去掉注释
        filtreg = r'#.*'
        filtre = re.compile(filtreg)
        file_new = filtre.sub('', file)
        file_lines = file_new.split('\n')
        # 匹配类名，每行只有一个类
        reg_class = r'^class (\w*)\(\w*\)|^class (\w*):'
        class_re = re.compile(reg_class)
        # 匹配类中测试函数
        reg_class_func = r'    def (test.*)\(.*\)'
        class_func_re = re.compile(reg_class_func)
        # 匹配模块测试函数
        reg_func = r'def (test.*)\(.*\)'
        module_func_re = re.compile(reg_func)
        test_list = []
        class_name = ''
        for line in file_lines:
            class_name_list = class_re.findall(line)
            if class_name_list:
                class_name = class_name_list[0][0] or class_name_list[0][1]
                test_list.append(file_path + '::' + class_name)
            elif class_func_re.findall(line):
                test_case = class_func_re.findall(line)[0]
                test_list.append(file_path+'::'+class_name+'::'+test_case)
            elif module_func_re.findall(line):
                test_case = module_func_re.findall(line)[0]
                test_list.append(file_path+'::'+test_case)
        return test_list

    def get_file(self, dir, branch='develop', project_id=None):
        """
        :param project_id:
        :param dir:
        :param branch:
        :return: 文件内容
        """
        project_id = project_id or self.project_id
        file = None
        data_file = self.header
        data_file['ref'] = branch
        dir_code = parse.quote(dir, safe='')
        uri = "{}/api/v4/projects/{}/repository/files/{}".format(BASE_GIT_URL, project_id, dir_code)
        res = requests.get(uri, data=data_file)
        res.raise_for_status()
        content = res.json()
        if content:
            file = base64.b64decode(content['content'])
        return file.decode('utf-8')

    def get_project_branches(self, project_id, search=''):
        """获取分支"""
        project = self.gl.projects.get(project_id)
        branches = project.branches.list(search=search)
        branches = [branch.__dict__['_attrs'] for branch in branches]
        return branches

    def create_branches(self, project_id, branch_name, ref='master'):
        """创建分支"""
        project = self.gl.projects.get(project_id)
        res = project.branches.create({'branch': branch_name, 'ref': ref})
        return res

    def delete_branches(self, project_id, branch_name):
        """删除分支"""
        project = self.gl.projects.get(project_id)
        res = project.branches.delete(branch_name)
        return res

    def get_projects(self, search=''):
        """获取项目列表"""
        projects = self.gl.projects.list(search=search, sort='desc', simple=True)
        projects = [project.__dict__['_attrs'] for project in projects]
        return projects

    def get_project_pipelines(self, project_id):
        uri = f'{BASE_GIT_URL}/api/v4/projects/{project_id}/pipelines'
        res = requests.get(uri, data=self.header)
        return res.json()





gitTool = GitLabApi()
# gitTool.get_projects(search='trade')
# gitTool.get_project_branches(622, '')
# gitTool.get_tag_list(550)
# gitTool.get_case_tree_list(project_id=550, dir='testcase', branch='develop')
# gitTool.get_project_id('qa/tiga')