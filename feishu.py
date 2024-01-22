# -*- coding: utf-8 -*-
# @Time    : 2021/3/1 11:15 上午
# @Author  : zoey
# @File    : feishu.py
# @Software: PyCharm
from copy import deepcopy
from requests.exceptions import HTTPError
import requests
import functools
from retry import retry

appid = 'cli_a08c2d8ad262900e'
secret = '2JdeQY1j9vj4DUpH8peaNbEfOWbsm4ym'

def valid_login(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        try:
            res = func(*args, **kw)
        except HTTPError as e:
            if e.response.status_code == 403:
                LarkClient.access_token = fetch_access_token()
                res = func(*args, **kw)
            else:
                raise Exception(e.response.content)
        return res

    return wrapper


@retry(tries=3, delay=1)
def fetch_access_token():
    """登录获取access_token,此处放在类变量中，建议放在redis"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    response = requests.post(url, json={"app_id": appid, "app_secret": secret})
    data = response.json()
    return data["tenant_access_token"]


class LarkClient:

    host = 'https://open.feishu.cn/open-apis'
    session = requests.session()
    access_token = fetch_access_token()

    @retry(tries=3, delay=1)
    @valid_login
    def _get(self, path, get_data=False, **data):
        response = self.session.get(self.host + path, headers={"Authorization": f"Bearer {self.access_token}"},
                                    params=data)
        response.raise_for_status()
        data = response.json()
        if get_data:
            data = data["data"]
        return data

    @retry(tries=3, delay=1)
    @valid_login
    def _post(self, path, **data):
        data = {k: v for k, v in data.items() if v}
        response = self.session.post(
            self.host + path,
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=data,
        )
        response.raise_for_status()
        return response.json()

    def create_user(self, name: str, email: str, mobile: str, department_ids: list, employee_type: int, **kwargs):
        """
        创建用户
        :param name: 用户名
        :param email: 用户邮箱
        :param mobile: 手机号
        :param department_ids: 用户所在的部门, string list
        :param employee_type: 员工类型，可用值：【1（正式员工），2（实习生），3（外包），4（劳务），5（顾问）】
        :param kwargs:
        :return:
        """
        body = {
            "name": name,
            "email": email,
            "mobile": mobile,
            "department_ids": department_ids,
            "employee_type": employee_type,
            **kwargs
        }
        resp = self._post("/contact/v1/user/add", **body)
        return resp

    def update_user(self, open_id: str, **kwargs):
        """更新用户"""
        resp = self._post("/contact/v1/user/update", open_id=open_id, **kwargs)
        return resp

    def delete_user(self, open_id):
        resp = self._post("/contact/v1/user/delete", open_id=open_id)
        return resp

    def get_users(self, open_department_id):
        """根据部门获取用户列表"""
        resp = self._get(
            "/contact/v3/users",
            department_id=open_department_id,
            page_size=100,
            get_data=True,
        )
        return resp

    def create_department(self, name: str, parent_open_department_id: str, create_group_chat: bool = True, leader_open_id: str = None, **kwargs):
        """
        创建部门
        :param name: 部门名称
        :param parent_open_department_id: 父部门 openID，选填，parent_id、parent_open_department_id至少指定其中之一；同时传两个参数，优先使用parent_open_department_id
        :param create_group_chat:
        :param leader_open_id: 部门领导 ID，支持通过 leader_employee_id 或者 leader_open_id 设置部门领导，请求同时传递两个参数时按 leader_employee_id 处理
        :param kwargs: 其它选填参数 见https://open.feishu.cn/document/ukTMukTMukTM/uYzNz4iN3MjL2czM
        :return:
        """
        body = {
            "name": name,
            "parent_open_department_id": parent_open_department_id,
            "create_group_chat": create_group_chat,
            "leader_open_id": leader_open_id,
            **kwargs
        }
        resp = self._post("/contact/v1/department/add", **body)
        return resp

    def get_department_detail(self, department_id):
        """
        获取部门详情
        :param department_id:
        :return:
        """
        resp = self._get(
            f"/contact/v3/departments/{department_id}",
            get_data=True,
        )
        return resp

    def delete_department(self, id: str):
        """
        删除部门
        :param id: 待删除部门id/open_department_id
        :return:
        """
        body = {"id": id}
        resp = self._post(f"/contact/v1/department/delete", **body)
        return resp

    def get_departments(self, open_department_id: str = 0, page_token: str = None, fetch_child: bool = True):
        """
        获取部门列表
        :param open_department_id:
        :param page_token:
        :param fetch_child:
        :return:
        """
        resp = self._get(
            "/contact/v1/department/simple/list",
            open_department_id=open_department_id,
            fetch_child=fetch_child,
            page_size=50,
            get_data=True,
            page_token=page_token,
        )
        return resp

    def get_all_departments(self):
        """
        获取全量部门
        :return:
        """
        _ = self.get_departments()
        resp = deepcopy(_)
        while _["has_more"]:
            _ = self.get_departments(page_token=_["page_token"])
            resp["department_infos"] += _["department_infos"]
        return resp



lark = LarkClient()
# lark.delete_user('ou_70d030d721d70673ffc7a38f3c37bbf5')
# lark.create_user(name='test', email='test@jiliguala.com', mobile='18720006801', department_ids=["9bfd4272fd484b83"], employee_type=1)
# lark.get_all_departments()
# print(lark.get_departments(fetch_child=False))
# lark.create_department(parent_open_department_id="0", name="test2", create_group_chat=False)
# lark.delete_department('g7fgc67a66bg4519')
# lark.get_department_detail('od-3d763741b9c1d85f452b9a6bc9c72f77')
# {'department_infos': [{'id': 'od-e88a446342ff720acba17d4cc767f037', 'open_department_id': 'od-e88a446342ff720acba17d4cc767f037', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-b264b408ddad10de1a811ec716e1624c', 'open_department_id': 'od-b264b408ddad10de1a811ec716e1624c', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-7f4c46b191051b11183491ab1b9bf926', 'open_department_id': 'od-7f4c46b191051b11183491ab1b9bf926', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-6ac439ac289537cafd7d6e5cdff6a5e9', 'open_department_id': 'od-6ac439ac289537cafd7d6e5cdff6a5e9', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-ce9f2b316d42df51c38b8d2c7038d946', 'open_department_id': 'od-ce9f2b316d42df51c38b8d2c7038d946', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-3fbd1c814b031965136603445b1e467b', 'open_department_id': 'od-3fbd1c814b031965136603445b1e467b', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-484a248e362d89feddfc5813a44a078a', 'open_department_id': 'od-484a248e362d89feddfc5813a44a078a', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-f608030ead2565a9915b9459d189f336', 'open_department_id': 'od-f608030ead2565a9915b9459d189f336', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-a730c74acdf204affd7e0bf027c0a46c', 'open_department_id': 'od-a730c74acdf204affd7e0bf027c0a46c', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-dbeb63b7b3e87aadaddb9c3a5a9978a0', 'open_department_id': 'od-dbeb63b7b3e87aadaddb9c3a5a9978a0', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-afb9b0f7bd2747a2a1279258a125a217', 'open_department_id': 'od-afb9b0f7bd2747a2a1279258a125a217', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'od-4390861adfa2a883e138268a440ab35c', 'open_department_id': 'od-4390861adfa2a883e138268a440ab35c', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'd9e3af614egg56d5', 'open_department_id': 'od-e8bad95395c571ae461294c3d6c02fd7', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'e66199322febgcb7', 'open_department_id': 'od-29ef39924d2d0d38e503b6b92f25e6a1', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': '7b9a12efcee84862', 'open_department_id': 'od-d730c19748ed56ef6466f397942af7ba', 'parent_id': '0', 'parent_open_department_id': '0'}, {'id': 'dgbeeecfcgb9a66a', 'open_department_id': 'od-9d325ed6be1d5dbf54bf52d62895a90a', 'parent_id': '0', 'parent_open_department_id': '0'}], 'has_more': False}
# '5b9c76fgc85dd268' 'od-3d763741b9c1d85f452b9a6bc9c72f77'