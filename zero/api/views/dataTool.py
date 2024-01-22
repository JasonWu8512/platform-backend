# coding=utf-8
# @Time    : 2020/12/9 1:06 下午
# @Author  : jerry
# @File    : dataTool.py
import json

from rest_framework.decorators import list_route

import zero.utils.superResponse as Response
from zero.api import BaseViewSet
from zero.api.decorators import login_or_permission_required, raise_exception, schema
from zero.dataTool.Apollo import ace_larkhooks_edit_apollo, ace_larkhooks_release_apollo, apollo
#  from zero.dataTool.ApolloIntl import ace_larkhooks_edit_apollo, ace_larkhooks_release_apollo, apolloIntl
from zero.dataTool.command import (
    DataOperate,
    InterfaceOperate,
    courses_experience_lesson,
    courses_normal_lesson,
    create_account_type_user,
    create_data_type_user,
    create_each_channel_order,
    create_inviter_order,
    create_lock_powder_relationship,
    delete_user_order,
    get_sp2xuIds,
    lesson_progress,
    logout_user,
    mongoClient,
    order_refund,
    query_all_class,
    remove_all_class,
    reset_checkin_state,
    update_promoter_state,
)
from zero.dataTool.dev_siri import *
from zero.dataTool.fat_siri import SampleOrderSchema, XshareRelationshipSchema
# from zero.dataTool.models import ApolloAppChat, ApolloAppItems, ApolloOperateLog, ApolloIntlAppItems, \
#     ApolloIntlOperateLog
from zero.dataTool.models import ApolloAppChat, ApolloAppItems, ApolloOperateLog
from zero.dataTool.siris import *
from zero.utils.contextLib import catch_error
from zero.utils.enums.businessEnums import *
from zero.utils.format import get_data


class ApolloAppChatViewSet(BaseViewSet):
    queryset = ApolloAppChat.objects.filter()
    serializer_class = ApolloAppChatSiri

    @schema(GetAppChatSchema)
    def list(self, request, *args, **kwargs):
        offset, limit, search = get_data(self.filtered, "offset", "limit", "search")
        queryset = ApolloAppChat.objects.filter(app_id__contains=search)
        data = ApolloAppChatSiri(queryset[offset: offset + limit], many=True).data
        total = len(queryset)
        return Response.success(data={"data": data, "total": total})


class ApolloViewSet(BaseViewSet):
    queryset = ApolloAppItems.objects.filter()
    serializer_class = OffsetLimitSiri

    @list_route(methods=["get"], url_path="apps")
    def get_apollo_apps(self, request):
        config_apps = ApolloAppItems.objects.filter().values_list("appId", flat=True).distinct()
        apps = apollo.get_apps()["content"]
        data = [{"id": app["id"], "appId": app["appId"]} for app in apps if app["appId"] in config_apps]
        return Response.success(data=data)

    @list_route(methods=["get"], url_path="app/(?P<appid>[^/]+)/items")
    def get_app_items(self, request, appid=None):
        items = ApolloAppItems.objects.filter(appId=appid).values_list("key", flat=True)
        all_space = apollo.get_app_items(appid)
        data = []
        for space in all_space:
            editable = True
            if space["parentAppId"] != appid:
                associated_items = apollo.get_associated_items(appid, space["baseInfo"]["namespaceName"])
                space["items"].extend(associated_items["items"])
                editable = False
            namespace = {
                "namespace": space["baseInfo"]["namespaceName"],
                "editable": editable,
                "itemModifiedCnt": space["itemModifiedCnt"],
                "items": [
                    dict(
                        item["item"],
                        **{
                            "isModified": item["isModified"],
                            "isDeleted": item["isDeleted"],
                            "newValue": item.get("newValue"),
                            "oldValue": item.get("oldValue"),
                            "dataChangeLastModifiedBy": ApolloAppItems.objects.get(
                                appId=appid, key=item["item"]["key"]
                            ).dataChangeLastModifiedBy
                                                        or item["item"]["dataChangeLastModifiedBy"],
                        }
                    )
                    for item in space["items"]
                    if item["item"]["key"] in items
                ],
            }
            if namespace["items"]:
                data.append(namespace)
        return Response.success(data=data)

    @login_or_permission_required("qa.edit")
    @list_route(methods=["put"], url_path="app/(?P<appid>[^/]+)/item/update")
    def update_app_items(self, request, appid=None):
        data = request.data
        with catch_error():
            apollo.edit_app_item(app_id=appid, item=data, namespace=data["namespace"])
            item = ApolloAppItems.objects.get(appId=appid, key=data["key"])
            item.dataChangeLastModifiedBy = self.username
            item.save()
            chat_ids = ApolloAppChat.objects.filter(app_id=appid).values_list("chat_id", flat=True)
            ace_larkhooks_edit_apollo(
                open_id=self.open_id,
                appid=appid,
                key=data["key"],
                value=data["value"],
                namespace=data["namespace"],
                chat_ids=chat_ids,
            )
            ApolloOperateLog.objects.create(
                appId=appid,
                key=data["key"],
                value=data["value"],
                comment=data["comment"],
                operator=self.username,
                operation="edit",
            )
        return Response.success()

    @login_or_permission_required("qa.edit")
    @list_route(methods=["post"], url_path="app/(?P<appid>[^/]+)/item/release")
    def release_app_configs(self, request, appid=None):
        title, comment, namespace = (
            request.data.get("title"),
            request.data.get("comment"),
            request.data.get("namespace"),
        )
        with catch_error():
            apollo.release_app_configs(app_id=appid, release_comment=comment, release_title=title, namespace=namespace)
            ApolloOperateLog.objects.create(appId=appid, operation="release", operator=self.username)
            chat_ids = ApolloAppChat.objects.filter(app_id=appid).values_list("chat_id", flat=True)
            ace_larkhooks_release_apollo(open_id=self.open_id, appid=appid, namespace=namespace, chat_ids=chat_ids)
        return Response.success()


# class ApolloIntlAppChatViewSet(BaseViewSet):
#     queryset = ApolloIntlAppChat.objects.filter()
#     serializer_class = ApolloIntlAppChatSiri
#
#     @schema(GetAppChatSchema)
#     def list(self, request, *args, **kwargs):
#         offset, limit, search = get_data(self.filtered, "offset", "limit", "search")
#         queryset = ApolloIntlAppChat.objects.filter(app_id__contains=search)
#         data = ApolloIntlAppChatSiri(queryset[offset: offset + limit], many=True).data
#         total = len(queryset)
#         return Response.success(data={"data": data, "total": total})
#
#
# class ApolloIntlViewSet(BaseViewSet):
#     queryset = ApolloIntlAppItems.objects.filter()
#     serializer_class = OffsetLimitSiri
#
#     @list_route(methods=["get"], url_path="apps")
#     def get_apollo_apps(self, request):
#         config_apps = ApolloIntlAppItems.objects.filter().values_list("appId", flat=True).distinct()
#         apps = apolloIntl.get_apps()["content"]
#         data = [{"id": app["id"], "appId": app["appId"]} for app in apps if app["appId"] in config_apps]
#         return Response.success(data=data)
#
#     @list_route(methods=["get"], url_path="app/(?P<appid>[^/]+)/items")
#     def get_app_items(self, request, appid=None):
#         items = ApolloIntlAppItems.objects.filter(appId=appid).values_list("key", flat=True)
#         all_space = apolloIntl.get_app_items(appid)
#         data = []
#         for space in all_space:
#             editable = True
#             if space["parentAppId"] != appid:
#                 associated_items = apolloIntl.get_associated_items(appid, space["baseInfo"]["namespaceName"])
#                 space["items"].extend(associated_items["items"])
#                 editable = False
#             namespace = {
#                 "namespace": space["baseInfo"]["namespaceName"],
#                 "editable": editable,
#                 "itemModifiedCnt": space["itemModifiedCnt"],
#                 "items": [
#                     dict(
#                         item["item"],
#                         **{
#                             "isModified": item["isModified"],
#                             "isDeleted": item["isDeleted"],
#                             "newValue": item.get("newValue"),
#                             "oldValue": item.get("oldValue"),
#                             "dataChangeLastModifiedBy": ApolloIntlAppItems.objects.get(
#                                 appId=appid, key=item["item"]["key"]
#                             ).dataChangeLastModifiedBy
#                                                         or item["item"]["dataChangeLastModifiedBy"],
#                         }
#                     )
#                     for item in space["items"]
#                     if item["item"]["key"] in items
#                 ],
#             }
#             if namespace["items"]:
#                 data.append(namespace)
#         return Response.success(data=data)
#
#     @login_or_permission_required("qa.edit")
#     @list_route(methods=["put"], url_path="app/(?P<appid>[^/]+)/item/update")
#     def update_app_items(self, request, appid=None):
#         data = request.data
#         with catch_error():
#             apolloIntl.edit_app_item(app_id=appid, item=data, namespace=data["namespace"])
#             item = ApolloIntlAppItems.objects.get(appId=appid, key=data["key"])
#             item.dataChangeLastModifiedBy = self.username
#             item.save()
#             chat_ids = ApolloIntlAppChat.objects.filter(app_id=appid).values_list("chat_id", flat=True)
#             ace_larkhooks_edit_apollo(
#                 open_id=self.open_id,
#                 appid=appid,
#                 key=data["key"],
#                 value=data["value"],
#                 namespace=data["namespace"],
#                 chat_ids=chat_ids,
#             )
#             ApolloIntlOperateLog.objects.create(
#                 appId=appid,
#                 key=data["key"],
#                 value=data["value"],
#                 comment=data["comment"],
#                 operator=self.username,
#                 operation="edit",
#             )
#         return Response.success()
#
#     @login_or_permission_required("qa.edit")
#     @list_route(methods=["post"], url_path="app/(?P<appid>[^/]+)/item/release")
#     def release_app_configs(self, request, appid=None):
#         title, comment, namespace = (
#             request.data.get("title"),
#             request.data.get("comment"),
#             request.data.get("namespace"),
#         )
#         with catch_error():
#             apolloIntl.release_app_configs(app_id=appid, release_comment=comment, release_title=title, namespace=namespace)
#             ApolloIntlOperateLog.objects.create(appId=appid, operation="release", operator=self.username)
#             chat_ids = ApolloIntlAppChat.objects.filter(app_id=appid).values_list("chat_id", flat=True)
#             ace_larkhooks_release_apollo(open_id=self.open_id, appid=appid, namespace=namespace, chat_ids=chat_ids)
#         return Response.success()


class DataViewSet(BaseViewSet):
    queryset = users.objects
    serializer_class = OffsetLimitSiri

    data_operate = DataOperate()
    interface_operate = InterfaceOperate()

    @schema()
    @list_route(methods=["post"], url_path="data/operate")
    def set_promoter_data(self, request):
        """根据不同的测试场景，预置测试数据"""
        try:
            operation = request.data.get("operation")
            f = getattr(self.data_operate, operation)
            data = request.data
            result = f(data)
            if result:
                return Response.success(data=result)
            else:
                return Response.success()
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=e)

    @schema()
    @list_route(methods=["get"], url_path="data/operation/query")
    def query_operation(self, request):
        """获取场景"""
        try:
            data = []
            for item in BusinessEnum:
                list = []
                for i in item.chinese:
                    print(i, item.chinese, "*******", type(i))
                    list.append({"chinese_scene": i.value, "scene": i.chinese})
                data.append({"project": item.value, "datas": list})
            return Response.success(data=data)
        except Exception as e:
            return Response.server_error(message=e)

    @schema()
    @list_route(methods=["post"], url_path="interface/operate")
    def operate_interface(self, request):
        """常用的接口操作"""
        try:
            operation = request.data.get("operation")
            f = getattr(self.interface_operate, operation)
            data = request.data
            result = f(data)
            if result:
                return Response.success(data=result)
            else:
                return Response.success()
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=e)

    """------------------------------------------------商品配置相关---------------------------------------------------"""

    @list_route(methods=["post"], url_path="spuConfig/spu/detail")
    def get_spu_detail(self, request):
        """数据工厂——商品配置:获取SPU下的所有sp2xuids信息"""
        try:
            spu_no = request.data.get("spu_no")
            resp = get_sp2xuIds(spu_no)
            return Response.success(resp)
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=e)

    """--------------------------------------------------订单配置相关------------------------------------------------"""

    @schema(SampleOrderSchema)
    @list_route(methods=["post"], url_path="orderConfig/sample/order")
    def create_sample_order(self, request):
        """数据工厂——订单配置:创建各个渠道的9.9订单"""
        try:
            subject, source, invitee = get_data(self.filtered, "subject", "source", "mobile")
            subject = subject.split("_")[1]
            resp = create_each_channel_order(source=source, subject=subject, invitee=invitee)
            return Response.success(resp)
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=e)

    """---------------------------用户配置相关------------------------------------------"""

    @schema(XshareRelationshipSchema)
    @list_route(methods=["post"], url_path="userConfig/xshare/relationship")
    def create_xshare_relationship(self, request):
        """数据工厂——用户配置:创建转推关系"""
        try:
            subject, channel, fan_type, mobile, fan_mobile = get_data(
                self.filtered, "subject", "channel", "fan_type", "mobile", "fan_mobile"
            )
            create_lock_powder_relationship(channel, subject, fan_type, mobile, fan_mobile)
            return Response.success()
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=e)

    @list_route(methods=["post"], url_path="userConfig/create/sample/user")
    @raise_exception
    def create_account_type_user(self, request):
        """创建指定账号\数据\课程类型用户"""
        class_type, account_type, data_type, level, mobile, item_id, bd = get_data(
            request.data, "class_type", "account_type", "data_type", "level", "mobile", "item_id", "bd"
        )
        data = {}
        if class_type:
            class_type, subject = class_type[0].split("_")
            if class_type == "mars":
                data = courses_experience_lesson(subject=subject, mobile=mobile)
            else:
                data = courses_normal_lesson(subject=subject, mobile=mobile)
        elif account_type:
            data = create_account_type_user(account_type[0], level=level, mobile=mobile, bd=bd)
        elif data_type:
            data = create_data_type_user(data_type[0], mobile=mobile, item_id=item_id)
        return Response.success(data=json.dumps(data))

    @list_route(methods=["post"], url_path="userConfig/create/inviter_order")
    @raise_exception
    def create_inviter_order(self, request):
        """一键拼团"""
        group_id, captain, crews = get_data(request.data, "group_id", "captain", "crew")
        if crews:
            crews = crews.replace("，", ",").split(",")
        resp = create_inviter_order(group_id, captain, crews)
        return Response.success(resp)

    @list_route(methods=["delete"], url_path="userConfig/handle/delete_user")
    @raise_exception
    def delete_account_type_user(self, request):
        """注销指定账号"""
        mobile = request.data.get("mobile")
        logout_user(mobile=mobile)
        return Response.success()

    @list_route(methods=["delete"], url_path="userConfig/handle/delete_user_order")
    @raise_exception
    def delete_user_order(self, request):
        """删除账号课程数据"""
        mobile = request.data.get("mobile")
        delete_user_order(mobile=mobile)
        return Response.success()

    @list_route(methods=["post"], url_path="userConfig/handle/update_user_ghs_cts")
    def update_user_ghs_cts(self, request):
        uid, cts = get_data(request.data, "uid", "cts")
        with catch_error():
            mongoClient.get_client().get_collection("ghs_user").update_one(
                filter={"_id": uid}, upsert=True, update={"$set": {"cts": cts}}
            )
        return Response.success()

    @list_route(methods=["post"], url_path="userConfig/handle/update_global_ios_ver")
    def update_global_ios_ver(self, request):
        """开/关审核模式"""
        ios_ver = request.data.get("ios_ver")
        with catch_error():
            mongoClient.get_client().get_collection("global").update_one(
                filter={"_id": "JLGL_GLOBAL_SETTINGS"}, update={"$set": {"ios_ver": ios_ver}}, upsert=True
            )
        return Response.success()

    @list_route(methods=["post"], url_path="userConfig/handle/reset_user_checkin_days")
    def reset_user_checkin_days(self, request):
        """重置打卡天数"""
        id, task, days = get_data(request.data, "id", "task", "days")
        try:
            reset_checkin_state(id, task, days)
            return Response.success()
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=str(e))

    @list_route(methods=["post"], url_path="userConfig/class")
    def get_all_class(self, request):
        """数据工厂——用户配置:一键查询用户拥有课程"""
        try:
            mobile = request.data.get("mobile")
            orders = query_all_class(mobile)
            return Response.success(orders)
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=e)

    @list_route(methods=["post"], url_path="userConfig/delete/class")
    def delete_all_class(self, request):
        """数据工厂——用户配置:一键删除用户拥有课程"""
        try:
            mobile = request.data.get("mobile")
            resp = remove_all_class(mobile)
            return Response.success(resp)
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=e)

    @list_route(methods=["post"], url_path="userConfig/promoter/state")
    def update_promter(self, request):
        """数据工厂——用户配置:一键修改推广人状态"""
        try:
            mobile, state = request.data.get("mobile"), request.data.get("state")
            update_promoter_state(mobile, state)
            return Response.success()
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=e)

    @list_route(methods=["post"], url_path="userConfig/refund")
    def refund_order(self, request):
        try:
            mobile, order_no = request.data.get("mobile"), request.data.get("order_no")
            order_refund(mobile=mobile, oid=order_no)
            return Response.success()
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=e)

    @list_route(methods=["post"], url_path="lessonConfig/lesson_progress")
    @raise_exception
    def lesson_progress(self, request):
        bid, lesson_id, is_first, finish_time = get_data(request.data, "bid", "lesson_id", "is_first", "finish_time")
        data = lesson_progress(bid, lesson_id, is_first, finish_time)
        return Response.success(data=data)
