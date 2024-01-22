# coding=utf-8
# @Time    : 2020/12/9 11:48 上午
# @Author  : jerry
# @File    : command.py
import base64
import datetime
import json
import random
import time
from itertools import groupby
from operator import itemgetter

import pandas
import shortuuid
from dateutil import parser

import zero.dataTool.apiRequest as api
import zero.utils.super_requests as requests
from zero.api.views.lesson_central.parsebase import parse_db_tb
from zero.api.views.lesson_central.rpc_lesson_score import get_lesson_score
from zero.dataTool import dev_models, dev_siri, fat_models, fat_siri
from zero.dataTool.checkcase import CasenameError, ParaError, checkcase
from zero.libs.mongo import mongoClient
from zero.libs.mysql import MySQL
from zero.utils.enums.businessEnums import CategoryEnum
from zero.utils.format import basic_auth, dateToTimeStamp, now_timeStr


class DataOperate:
    """---------------------------------------------通用-----------------------------------------"""

    def delete_user_purchase_record(self, data):
        """删除用户购买记录"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
            dev_models.pingxxorder.hard_delete(uid=user["_id"])
            dev_models.ghs_user.hard_delete(_id=user["_id"])
            dev_models.lessonbuy.hard_delete(_id=user["_id"])
            dev_models.sc_possess.hard_delete(_id=user["_id"])
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
            fat_models.pingxxorder.hard_delete(uid=user["_id"])
            fat_models.ghs_user.hard_delete(_id=user["_id"])
            fat_models.lessonbuy.hard_delete(_id=user["_id"])
            fat_models.sc_possess.hard_delete(_id=user["_id"])

    def top_up_user_guadou_balance(self, data):
        """充值10000呱豆"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        value = {"guadouBalance": 1000000}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            dev_models.users.base_upsert(query=query, **value)
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            fat_models.users.base_upsert(query=query, **value)

    def update_users(self, data):
        """修改用户信息"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        content = data["content"]
        if not content:
            raise ValueError("修改的内容不允许为空")
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            dev_models.users.base_upsert(query=query, **content)
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            fat_models.users.base_upsert(query=query, **content)

    def get_sms_code(self, data):
        """获取短信验证码"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
            code = user.get("sms").get("code")
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
            code = user.get("sms").get("code")
        return code

    def create_eshop_order(self, data):
        """创建正价课订单"""
        env = data["env"]
        mobile = data.get("mobile")
        spu_no = data.get("spu_no")
        promoter_id = data.get("promoter_id")
        if not mobile:
            raise ValueError("请输入手机号")
        if not spu_no:
            raise ValueError("请输入商品编号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
        # 获取spu详情
        headers = {"Authorization": basic_auth(id=user["_id"], tok=user["tok"])}
        res = requests.request(
            method="GET",
            url=f"https://{env}.jiliguala.com/api/eshop/v2/commodity/spu/{spu_no}",
            headers=headers,
            verify=False,
        )
        if res.status_code != 200:
            raise ValueError(res.text)
        spu_detail = res.json()
        # 创建订单
        order_body = {
            "sp2xuId": spu_detail["data"]["skuSpecBriefList"][0]["sp2xuId"],
            "payPrice": 0,
            "number": 1,
            "shipping": True,
            "recipientInfo": {
                "recipient": "测试订单",
                "mobile": "12345678901",
                "addressProvince": "黑龙江省",
                "addressCity": "双鸭山市",
                "addressDistrict": "宝山区",
                "addressStreet": "测试地址",
            },
            "promotionId": None,
            "useGuadou": True,
            "guaDouNum": int(spu_detail["data"]["skuSpecBriefList"][0]["priceRmb"]),
            "marketingChannel": None,
            "groupId": None,
            "promoterId": promoter_id,
            "userRemarks": None,
        }
        order_res = requests.request(
            method="POST",
            url=f"https://{env}.jiliguala.com/api/eshop/v2/orders",
            json=order_body,
            headers=headers,
            verify=False,
        ).json()
        # 支付订单
        charge_body = {
            "oid": order_res["data"]["orderNo"],
            "channel": "wx_pub",
            "payTotal": 0,
            "guadouDiscount": int(spu_detail["data"]["skuSpecBriefList"][0]["priceRmb"]),
            "pay_wechat_token": None,
            "pay_wechat_token_typ": None,
            "extra": {"result_url": None, "success_url": None, "hb_fq_num": None},
        }
        charge_res = requests.request(
            method="POST",
            url=f"https://{env}.jiliguala.com/api/eshop/v2/orders/charge",
            json=charge_body,
            headers=headers,
            verify=False,
        ).json()
        return charge_res.get("data").get("order_no")

    def clean_user_device(self, data):
        """删除用户设备"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.User_devicesSiri(query_set).data
            dev_models.user_devices.hard_delete(_id=user["_id"])
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.User_devicesSiri(query_set).data
            fat_models.user_devices.hard_delete(_id=user["_id"])

    """---------------------------------------------推广人-----------------------------------------"""

    def create_Sample_order(self, data):
        """购买9.9体验课"""
        env = data["env"]
        mobile = data.get("mobile")
        fan_mobile = data.get("fan_mobile")
        sp2xuId = data.get("sp2xuIds")
        sp2xuIds = []
        sp2xuIds.append(int(sp2xuId))
        if not mobile or not fan_mobile or not sp2xuIds:
            raise ValueError("手机号，粉丝手机号及体验课sp2xuIds均为必填项")
        query1 = {"mobile": mobile}
        query2 = {"mobile": fan_mobile}
        if env == "dev":
            query_set1 = dev_models.users.query_first(**query1)
            query_set2 = dev_models.users.query_first(**query2)
            if not query_set1 or not query_set2:
                raise ValueError("用户不存在，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set1).data
            fan = dev_siri.UsersSiri(query_set2).data
        else:
            query_set1 = fat_models.users.query_first(**query1)
            query_set2 = fat_models.users.query_first(**query2)
            if not query_set1 or not query_set2:
                raise ValueError("用户不存在，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set1).data
            fan = fat_siri.UsersSiri(query_set2).data
        headers = {"Authorization": basic_auth(id=fan["_id"], tok=fan["tok"])}
        order_body = {
            "itemid": "H5_Sample_DiamondActivity",
            "nonce": now_timeStr(),
            "source": "AppHomeView",
            "xshareInitiator": user["_id"],
            "sharer": user["_id"],
            "sp2xuIds": sp2xuIds,
        }
        order_res = requests.request(
            method="PUT",
            url=f"https://{env}.jiliguala.com/api/mars/order/create/v2",
            json=order_body,
            headers=headers,
            verify=False,
        ).json()
        charge_body = {
            "channel": "wx_wap",
            "oid": order_res["data"]["orderNo"],
            "extra": {"result_url": "https://devt.jiliguala.com/test"},
        }
        charge_res = requests.request(
            method="POST",
            url=f"https://{env}.jiliguala.com/api/mars/order/charge/v2",
            json=charge_body,
            headers=headers,
            verify=False,
        ).json()
        if charge_res.get("code") == 0:
            return charge_res.get("data").get("order_no")
        else:
            raise ValueError(charge_res.get("msg"))

    def delete_promoter(self, data):
        """删除推广人信息"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            promoter = dev_siri.PromoterAccountsSiri(query_set).data
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            dev_models.promoter_accounts.hard_delete(**query)
            dev_models.promoter_wechat.hard_delete(promoterId=promoter["_id"])
            dev_models.promoter_status_log.hard_delete(_id=promoter["_id"])
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            promoter = fat_siri.PromoterAccountsSiri(query_set).data
            fat_models.promoter_accounts.hard_delete(**query)
            fat_models.promoter_wechat.hard_delete(promoterId=promoter["_id"])
            fat_models.promoter_status_log.hard_delete(_id=promoter["_id"])

    def delete_promoter_openidOrUnionId(self, data):
        """推广人账号解绑wechatInfo"""
        env = data.get("env")
        openid = data.get("openid")
        unionId = data.get("union_id")
        query = {}
        if openid:
            query.update({"openid": openid})
        if unionId:
            query.update({"unionId": unionId})
        if not query:
            raise ValueError("openid与unionId必填其一")
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有匹配记录，请输入正确的openid或unionId")
            promoter = dev_siri.PromoterAccountsSiri(query_set).data
            dev_models.promoter_accounts.objects(**query).update(unset__openid=1, unset__unionId=1)
            dev_models.promoter_wechat.hard_delete(promoterId=promoter["_id"])
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有匹配记录，请输入正确的openid或unionId")
            promoter = dev_siri.PromoterAccountsSiri(query_set).data
            fat_models.promoter_accounts.objects(**query).update(unset__openid=1, unset__unionId=1)
            fat_models.promoter_wechat.hard_delete(promoterId=promoter["_id"])

    def update_promoter(self, data):
        """修改推广人信息"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        content = data["content"]
        if not content:
            raise ValueError("修改的内容不允许为空")
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            dev_models.promoter_accounts.base_upsert(query=query, **content)
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            fat_models.promoter_accounts.base_upsert(query=query, **content)

    def delelte_promoter_wechat(self, data):
        """删除微信绑定与首次登录记录"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            promoter = dev_siri.PromoterAccountsSiri(query_set).data
            dev_models.promoter_wechat.hard_delete(promoterId=promoter["_id"])
            dev_models.promoter_status_log.hard_delete(_id=promoter["_id"])
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            promoter = fat_siri.PromoterAccountsSiri(query_set).data
            fat_models.promoter_wechat.hard_delete(promoterId=promoter["_id"])
            fat_models.promoter_status_log.hard_delete(_id=promoter["_id"])

    def delete_promoter_xshare_fans(self, data):
        """删除锁粉信息"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
            dev_models.xshare_relationship.hard_delete(childUid=user["_id"])
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
            fat_models.xshare_relationship.hard_delete(childUid=user["_id"])

    def delete_promoter_all_fans(self, data):
        """删除推广人下全部粉丝"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            promoter = dev_siri.PromoterAccountsSiri(query_set).data
            dev_models.xshare_relationship.hard_delete(promoterId=promoter["_id"])
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            promoter = fat_siri.PromoterAccountsSiri(query_set).data
            fat_models.xshare_relationship.hard_delete(promoterId=promoter["_id"])

    def delete_promoter_order(self, data):
        """删除推广人下所有分佣记录"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            promoter = dev_siri.PromoterAccountsSiri(query_set).data
            dev_models.promoter_order.hard_delete(promoterId=promoter["_id"])
            dev_models.pingxxorder.hard_delete(newPromoterId=promoter["_id"])
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            promoter = fat_siri.PromoterAccountsSiri(query_set).data
            fat_models.promoter_order.hard_delete(promoterId=promoter["_id"])
            fat_models.pingxxorder.hard_delete(newPromoterId=promoter["_id"])

    def reset_promoter_amount_to_0(self, data):
        """重置推广人金额为0"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        value = {"totalAmount": 0, "totalRevenue": 0, "frozenRevenue": 0, "doneRevenue": 0}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            dev_models.promoter_accounts.base_upsert(query=query, **value)
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            fat_models.promoter_accounts.base_upsert(query=query, **value)

    def update_promoter_level_to_partner(self, data):
        """推广人修改为合伙人"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        value = {"level": "partner", "totalAmount": 1000100}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            dev_models.promoter_accounts.base_upsert(query=query, **value)
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            fat_models.promoter_accounts.base_upsert(query=query, **value)

    def update_partner_level_to_promoter(self, data):
        """合伙人修改为推广人"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        value = {"level": "promoter", "totalAmount": 100}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            dev_models.promoter_accounts.base_upsert(query=query, **value)
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            fat_models.promoter_accounts.base_upsert(query=query, **value)

    def update_promoter_state_inactive(self, data):
        """推广人状态修改为未激活"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        value = {"state": "inactive"}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            dev_models.promoter_accounts.base_upsert(query=query, **value)
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            fat_models.promoter_accounts.base_upsert(query=query, **value)

    def update_promoter_state_active(self, data):
        """推广人状态修改为激活"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        value = {"state": "active"}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            dev_models.promoter_accounts.base_upsert(query=query, **value)
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            fat_models.promoter_accounts.base_upsert(query=query, **value)

    def update_promoter_state_frozen(self, data):
        """推广人状态修改为已冻结"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        value = {"state": "frozen"}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            dev_models.promoter_accounts.base_upsert(query=query, **value)
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            fat_models.promoter_accounts.base_upsert(query=query, **value)

    def update_promoter_state_forbidden(self, data):
        """推广人状态修改为已封号"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        value = {"state": "forbidden"}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            dev_models.promoter_accounts.base_upsert(query=query, **value)
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            fat_models.promoter_accounts.base_upsert(query=query, **value)

    def update_promoter_state_invalid(self, data):
        """推广人状态修改为已失效"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        value = {"state": "invalid"}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            dev_models.promoter_accounts.base_upsert(query=query, **value)
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            if not query_set:
                raise ValueError("没有该推广人，请输入正确的手机号")
            fat_models.promoter_accounts.base_upsert(query=query, **value)

    def get_promoter(self, data):
        """查询推广人信息"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.promoter_accounts.query_first(**query)
            promoter = dev_siri.PromoterAccountsSiri(query_set).data
        else:
            query_set = fat_models.promoter_accounts.query_first(**query)
            promoter = fat_siri.PromoterAccountsSiri(query_set).data
        return promoter

    """---------------------------------------------转介绍-----------------------------------------"""

    def delete_wc_users(self, data):
        """删uid&unionId绑定关系"""
        env = data["env"]
        mobile = data.get("mobile")
        union_id = data.get("union_id")
        query = {}
        if union_id:
            query.update({"unionId": union_id})
            if env == "dev":
                query_set = dev_models.wc_users.query_first(**query)
                if not query_set:
                    raise ValueError("没有匹配记录，请输入正确的unionId")
                dev_models.wc_users.hard_delete(unionId=union_id)
            else:
                query_set = fat_models.wc_users.query_first(**query)
                if not query_set:
                    raise ValueError("没有匹配记录，请输入正确的unionId")
                fat_models.wc_users.hard_delete(unionId=union_id)
        elif mobile:
            query.update({"mobile": mobile})
            if env == "dev":
                query_set = dev_models.users.query_first(**query)
                if not query_set:
                    raise ValueError("没有该用户，请输入正确的手机号")
                user = dev_siri.UsersSiri(query_set).data
                dev_models.wc_users.hard_delete(uid=user["_id"])
            else:
                query_set = fat_models.users.query_first(**query)
                if not query_set:
                    raise ValueError("没有该用户，请输入正确的手机号")
                user = fat_siri.UsersSiri(query_set).data
                fat_models.wc_users.hard_delete(uid=user["_id"])
        else:
            raise ValueError("请输入要删除的记录的手机号或者unionId")

    def delete_unionId(self, data):
        """删除unionId对应绑定关系"""
        env = data["env"]
        union_id = data.get("union_id")
        query = {}
        if not union_id:
            raise ValueError("请输入unionId")
        else:
            query.update({"unionId": union_id})
        if env == "dev":
            query_set = dev_models.wc_users.query_first(**query)
            query_openusers = dev_models.wc_openusers.query_first(**query)
            if not query_set and not query_openusers:
                raise ValueError("没有匹配记录，请输入正确的unionId")
            dev_models.wc_users.hard_delete(unionId=union_id)
            dev_models.wc_openusers.hard_delete(unionId=union_id)
        else:
            query_set = fat_models.wc_users.query_first(**query)
            query_openusers = fat_models.wc_openusers.query_first(**query)
            if not query_set and not query_openusers:
                raise ValueError("没有匹配记录，请输入正确的unionId")
            fat_models.wc_users.hard_delete(unionId=union_id)
            fat_models.wc_openusers.hard_delete(unionId=union_id)

    def delete_xshare_group_purchase(self, data):
        """删除团单"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
            dev_models.xshare_group_purchase.hard_delete(inviterId=user["_id"])
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
            fat_models.xshare_group_purchase.hard_delete(inviterId=user["_id"])

    def reset_xshare_group_purchase(self, data):
        """删除参团信息"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
            old_group_purchase = dev_models.xshare_group_purchase.query_first(**{"inviterId": user["_id"]})
            group_purchase = dev_siri.XshareGroupPurchaseSiri(old_group_purchase).data
            group_purchase["invitee"] = []
            group_purchase["size"] = 1
            dev_models.xshare_group_purchase.hard_delete(_id=group_purchase["_id"])
            dev_models.xshare_group_purchase.objects.create(**group_purchase)
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
            old_group_purchase = fat_models.xshare_group_purchase.query_first(**{"inviterId": user["_id"]})
            group_purchase = fat_siri.XshareGroupPurchaseSiri(old_group_purchase).data
            group_purchase["invitee"] = []
            group_purchase["size"] = 1
            fat_models.xshare_group_purchase.hard_delete(_id=group_purchase["_id"])
            fat_models.xshare_group_purchase.objects.create(**group_purchase)

    def delete_xshare_screenshot_history_newest(self, data):
        """删除截图表中最新一条记录"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
            history = dev_models.xshare_screenshot_history.query_all(**{"uid": user["_id"]})
            if not history:
                raise ValueError("该用户没有相关截图记录，请输入其他手机号")
            history_sc = dev_siri.XshareScreenshotHistorySiri(history, many=True).data
            dev_models.xshare_screenshot_history.hard_delete(_id=history_sc[-1]["_id"])
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
            history = fat_models.xshare_screenshot_history.query_all(**{"uid": user["_id"]})
            if not history:
                raise ValueError("该用户没有相关截图记录，请输入其他手机号")
            history_sc = fat_models.XshareScreenshotHistorySiri(history, many=True).data
            fat_models.xshare_screenshot_history.hard_delete(_id=history_sc[-1]["_id"])

    def update_pingxxorder_cts(self, data):
        """修改完课返现时间(默认提前一周)"""
        env = data["env"]
        mobile = data.get("mobile")
        content = data.get("content")
        if content:
            cts = data.get("content").get("cts")
        value = {}
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
            pingxxorder = dev_models.pingxxorder.query_all(**{"uid": user["_id"]})
            pingxxorder_data = dev_siri.PingxxorderSiri(pingxxorder, many=True).data
            if cts:
                value.update({"cts": parser.parse(cts)})
            else:
                value.update({"cts": parser.parse(pingxxorder_data[-1]["cts"]) + datetime.timedelta(days=-7)})
            dev_models.pingxxorder.base_upsert(query={"_id": pingxxorder_data[-1]["_id"]}, **value)
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
            pingxxorder = fat_models.pingxxorder.query_all(**{"uid": user["_id"]})
            pingxxorder_data = fat_siri.PingxxorderSiri(pingxxorder, many=True).data
            if cts:
                value.update({"cts": parser.parse(cts)})
            else:
                value.update({"cts": parser.parse(pingxxorder_data[-1]["cts"]) + datetime.timedelta(days=-7)})
            fat_models.pingxxorder.base_upsert(query={"_id": pingxxorder_data[-1]["_id"]}, **value)

    """---------------------------------------------tiga-----------------------------------------"""

    def delete_fan_purchase_record(self, data):
        """tiga调用，用于清除数据，删除粉丝购买的课程记录"""
        env = data["env"]
        if env == "dev":
            dev_models.pingxxorder.hard_delete(_id=data["orderId"])
            dev_models.promoter_order.hard_delete(_id=data["orderId"])
        else:
            fat_models.pingxxorder.hard_delete(_id=data["orderId"])
            fat_models.promoter_order.hard_delete(_id=data["orderId"])

    def delete_pingxxorder_and_ghs(self, data):
        """tiga调用，删除订单与规划师"""
        env = data["env"]
        mobile = data.get("mobile")
        if not mobile:
            raise ValueError("请输入手机号")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
            dev_models.pingxxorder.hard_delete(uid=user["_id"])
            dev_models.ghs_user.hard_delete(_id=user["_id"])
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
            fat_models.pingxxorder.hard_delete(uid=user["_id"])
            fat_models.ghs_user.hard_delete(_id=user["_id"])

    def update_promoter_xshare_fans_expirets(self, data):
        """tiga调用,修改锁粉时间"""
        env = data["env"]
        mobile = data.get("mobile")
        cts = data.get("content").get("cts")
        value = {}
        if not mobile:
            raise ValueError("请输入手机号")
        if not cts:
            raise ValueError("请输入修改的日期")
        query = {"mobile": mobile}
        value.update({"cts": parser.parse(cts)})
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
            dev_models.xshare_relationship.base_upsert(query={"childUid": user["_id"]}, **value)
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
            fat_models.xshare_relationship.base_upsert(query={"childUid": user["_id"]}, **value)

    """---------------------------------------------eshop-----------------------------------------"""

    def get_sso_code(self, env):
        sso_body = {"email_address": "sso.test@jiliguala.com", "pwd": "OIucobw7"}
        sso_login_res = requests.request(
            method="POST", json=sso_body, verify=False, url=f"https://{env}-sso.jiliguala.com/api/sso/login_by_email"
        )
        cookies = sso_login_res.cookies
        body = {}
        sso_res = requests.request(
            method="POST",
            url=f"https://{env}-sso.jiliguala.com/api/sso/authorize",
            cookies=cookies,
            verify=False,
            json=body,
        )
        resp = sso_res.json()
        code = resp.get("data").get("sso_auth_code")
        return code

    def create_SGU(self, data):
        """一键创建SGU"""
        env = data["env"]
        title = data.get("title")
        price_rmb = data.get("price")
        price_teaching_tool = data.get("tool_price")
        sub_category = data.get("sub_category")
        skus_name = data.get("skus")
        if not title or not price_rmb or not sub_category or not skus_name:
            raise ValueError("title,price,sub_category,skus不能为空")
        skus = skus_name.split(",")
        code = self.get_sso_code(env)
        login_body = {"code": code}
        token = (
            requests.request(
                method="POST",
                url=f"https://{env}.jiliguala.com/api/admin/eshop/sso/login",
                json=login_body,
                verify=False,
            )
                .json()
                .get("data")
                .get("token")
        )
        headers = {
            "admintoken": token,
        }
        sku_list = []
        for sku in skus:
            url = f"https://{env}.jiliguala.com/api/admin/eshop/commodity/sku?pageNo=1&pageSize=10&type=1&keyword=&commodityNo={sku}"
            res = requests.request(method="GET", url=url, headers=headers, verify=False)
            if not res.json().get("data").get("content"):
                raise ValueError(f"{sku}不存在")
            skuid = res.json().get("data").get("content")[0].get("id")
            sku_list.append({"id": skuid, "free": 0, "num": 1})
        body = {
            "commodityNo": f"{shortuuid.uuid()}_SGU",
            "describes": "测试",
            "title": title,
            "priceBy": 0,
            "priceDiamond": 0,
            "priceGuaDouPp": 100,
            "priceMagika": 0,
            "priceRmb": price_rmb,
            "priceTeachingTool": price_teaching_tool if price_teaching_tool else 0,
            "purchaseLimit": 1,
            "skuList": sku_list,
            "state": 1,
            "stockNum": 999,
            "subCategoryId": CategoryEnum.get_chinese(sub_category),
            "thumb": "https://qiniucdn.jiliguala.com/eshop/9f13b514-e5ad-44cd-8d79-859646780a72.jpeg",
            "type": 2,
        }
        res = requests.request(
            method="POST",
            url=f"https://{env}.jiliguala.com/api/admin/eshop/commodity/sku",
            json=body,
            headers=headers,
            verify=False,
        )
        resp = res.json()
        if resp.get("code") == 0:
            return resp.get("data")
        else:
            raise ValueError(resp.get("msg"))

    def create_SPU(self, data):
        """一键创建SGU"""
        env = data["env"]
        title = data.get("title")
        sgus_name = data.get("sgus")
        if not title or not sgus_name:
            raise ValueError("title,sgus不能为空")
        sgus = sgus_name.split(",")
        code = self.get_sso_code(env)
        login_body = {"code": code}
        token = (
            requests.request(
                method="POST",
                url=f"https://{env}.jiliguala.com/api/admin/eshop/sso/login",
                json=login_body,
                verify=False,
            )
                .json()
                .get("data")
                .get("token")
        )
        headers = {
            "admintoken": token,
        }
        sgu_list = []
        spec_name_list = []
        for sgu in sgus:
            url = f"https://{env}.jiliguala.com/api/admin/eshop/commodity/sku?pageNo=1&pageSize=10&type=2&keyword=&commodityNo={sgu}"
            res = requests.request(method="GET", url=url, headers=headers, verify=False)
            if not res.json().get("data").get("content"):
                raise ValueError(f"{sgu}不存在")
            sgu_id = res.json().get("data").get("content")[0].get("id")
            sgu_list.append({"id": sgu_id, "specValues": [f"{sgu_id}"]})
            spec_name_list.append({"name": sgu_id, "specValueList": [f"{sgu_id}"]})
        body = {
            "title": title,
            "hbfqId": 0,
            "state": 1,
            "commodityNo": f"{shortuuid.uuid()}_SPU",
            "priceBy": 0,
            "specNameList": spec_name_list,
            "skuSpecBriefList": sgu_list,
            "thumb": "https://qiniucdn.jiliguala.com/eshop/70a72b39-6429-4fb2-a62c-a8eb08c02fce.jpeg",
            "thumbsArray": ["https://qiniucdn.jiliguala.com/eshop/f5c97ab0-faf4-4be3-a8fb-1659f555dafc.jpeg"],
        }
        res = requests.request(
            method="POST",
            url=f"https://{env}.jiliguala.com/api/admin/eshop/commodity/spu",
            json=body,
            headers=headers,
            verify=False,
        )
        resp = res.json()
        if resp.get("code") == 0:
            return resp.get("data")
        else:
            raise ValueError(resp.get("msg"))

    """---------------------------------------------下沉--------------------------------------------"""

    def saturn_bind(self, data):
        """下沉锁粉"""
        env = data["env"]
        mobile = data.get("mobile")
        channel = data.get("channel")
        if not mobile or not channel:
            raise ValueError("请输入手机号与channel")
        query = {"mobile": mobile}
        if env == "dev":
            query_set = dev_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = dev_siri.UsersSiri(query_set).data
        else:
            query_set = fat_models.users.query_first(**query)
            if not query_set:
                raise ValueError("没有该用户，请输入正确的手机号")
            user = fat_siri.UsersSiri(query_set).data
        headers = {"Authorization": basic_auth(id=user["_id"], tok=user["tok"])}
        body = {"channel": channel}
        res = requests.request(
            method="GET",
            url=f"http://{env}ggr.jiliguala.com/api/saturn/channel/bind",
            params=body,
            headers=headers,
            verify=False,
        )
        resp = res.json()
        if resp.get("code") == 0:
            return resp.get("data")
        else:
            raise ValueError(resp.get("msg"))

    """---------------------------------------------接口操作-----------------------------------------"""


class InterfaceOperate:
    def refund(self, data):
        """订单退款"""
        env = data["env"]
        oid = data.get("oid")
        if not oid:
            raise ValueError("请输入需要退款的订单id")
        body = {"orderNo": oid}
        headers = {
            "authorization": "Basic MTNjNDlkNmM3YmI1NGQzYWE5NjNiMThkMjBlNGExNjE6MDFkNDVhYTczNGE4NDg4NGE4ODQ0OGIzOWI5ZGJkZTU=",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "postman-token": "1c376f8a-5a5e-00c3-40f0-c4244e78a5b5",
            "version": "1",
        }
        res = requests.request(
            method="POST",
            url=f"http://{env}.jiliguala.com/api/trade-order/refund",
            json=body,
            headers=headers,
            verify=False,
        )
        resp = res.json()
        if resp.get("code") == 0:
            return resp
        else:
            raise ValueError(res.text)

    def redeem(self, data):
        """生成兑换码"""
        env = data["env"]
        item_id = data.get("item_id")
        num = data.get("num")
        if not item_id or not num:
            raise ValueError("请输入兑换码所需参数")
        body = {"itemid": item_id, "channel": "qa_20191220", "num": num}
        headers = {
            "authorization": "Basic MGJlZjUzNGE4Nzc1NDg3ZmE0MmI3ZmE4ZTBkNGQ3ZjQ6YzdkNTFkN2NlYjM0NDg2NWIwNWMzYzdmZTJkYjBjZWY=",
            "content-type": "application/json",
            "version": "1",
        }
        res = requests.request(
            method="POST",
            url=f"http://{env}.jiliguala.com/api/circulars/redeem",
            json=body,
            headers=headers,
            verify=False,
        )
        resp = res.json()
        if resp.get("code") == 0:
            return resp
        else:
            raise ValueError(resp.get("msg"))

    def trace_seller_ship(self, data):
        """聚水潭发货"""
        env = data["env"]
        oid = data.get("oid")
        if not oid:
            raise ValueError("请输入需要发货的订单id")
        body = {"oid": oid, "subItems": [{"companyId": "ZTO", "trackingNumber": "75404521278873", "company": "中通"}]}
        headers = {
            "content-type": "application/json",
        }
        res = requests.request(
            method="POST",
            url=f"https://{env}.jiliguala.com/api/xshare/jst/traceSellerShip",
            json=body,
            headers=headers,
            verify=False,
        )
        resp = res.json()
        if resp.get("code") == 0:
            return resp
        else:
            raise ValueError(resp.get("msg"))


def get_user_basic_auth_by(uid, tok):
    code = base64.b64encode(f"{uid}:{tok}".encode("utf-8"))
    return "Basic " + str(code, encoding="utf-8")


def create_lock_powder_relationship(channel, subject, fan_type, mobile, fan_mobile):
    """生成锁粉关系"""
    mongoDb = mongoClient.get_client(db="JLGL")
    mongoDb_xshare = mongoClient.get_client(db="XSHARE")
    now_dt = datetime.datetime.now()
    user_query, fan_query = {"mobile": mobile}, {"mobile": fan_mobile}
    user = mongoDb.get_collection("users").find_one(user_query)
    fan = mongoDb.get_collection("users").find_one(fan_query)
    if not user:
        raise ValueError("没有该用户账号，请输入正确的手机号")
    if not fan:
        raise ValueError("没有该粉丝账号，请输入正确的粉丝手机号")
    relation_query_set = mongoDb_xshare.get_collection("xshare_relationship").find_one(
        {"childUid": fan["_id"], "relationType": "0"}
    )
    if relation_query_set:
        if fan_type == "0":
            raise ValueError("该粉丝已存在其他用户下的有效锁粉，请解除后再锁粉。")
    value = {
        "uid": user["_id"],
        "childUid": fan["_id"],
        "subjectType": subject,
        "businessType": channel,
        "relationType": fan_type,
        "expirets": datetime.datetime(year=now_dt.year + 1, month=now_dt.month, day=now_dt.day),
        "cts": now_dt,
        "uts": now_dt,
    }
    mongoDb_xshare.get_collection("xshare_relationship").update_one(
        filter={"uid": user["_id"], "childUid": fan["_id"]}, update={"$set": value}, upsert=True
    )


def get_sp2xuIds(spu_no):
    """获取SPU下的所有sp2xuids信息"""
    resp = []
    res = requests.request(
        method="GET", url=f"https://fat.jiliguala.com/api/eshop/v2/commodity/spu/{spu_no}", verify=False
    )
    if res.status_code != 200:
        raise ValueError(res.text)
    spu = res.json()
    detail = spu.get("data").get("skuSpecBriefList")
    if detail:
        for d in detail:
            sp = {}
            sp.update({"sp2xuId": d.get("sp2xuId"), "commodityNo": d.get("commodityNo")})
            resp.append(json.dumps(sp))
    else:
        return ""
    return "".join(resp)


def create_each_channel_order(source, subject, invitee, inviter=None):
    """创建各个渠道的9.9订单"""
    mongoDb = mongoClient.get_client(db="JLGL")
    # 被邀请人相关信息，订单由被邀请人下单
    invitee_user = mongoDb.get_collection("users").find_one({"mobile": invitee})
    if not invitee_user:
        raise ValueError("没有该被邀请人账号，请输入正确的手机号")
    headers = {"Authorization": basic_auth(id=invitee_user["_id"], tok=invitee_user["tok"])}
    create_order_body = {
        "itemid": "H5_Sample_OutsideH5",
        "nonce": now_timeStr(),
        "source": source,
        "sp2xuIds": [subject],
    }
    # 判断是否有指定邀请人
    if inviter:
        inviter_user = mongoDb.get_collection("users").find_one({"mobile": inviter})
        if not inviter_user:
            raise ValueError("没有该邀请人账号，请输入正确的手机号")
        create_order_body = {
            "itemid": "H5_Sample_OutsideH5",
            "nonce": now_timeStr(),
            "source": source,
            "sp2xuIds": [subject],
            "sharer": inviter_user["_id"],
        }
    # 生成订单
    create_res = requests.request(
        method="PUT",
        url=f"https://fat.jiliguala.com/api/mars/order/create/v2",
        json=create_order_body,
        headers=headers,
        verify=False,
    ).json()
    # 若生成订单成功,支付订单
    if create_res.get("code") == 0:
        charge_body = {
            "channel": "wx_wap",
            "oid": create_res["data"]["orderNo"],
            "extra": {"result_url": "https://devt.jiliguala.com/test"},
        }
        charge_res = requests.request(
            method="POST",
            url=f"https://fat.jiliguala.com/api/mars/order/charge/v2",
            json=charge_body,
            headers=headers,
            verify=False,
        ).json()
        if charge_res.get("code") == 0:
            return charge_res.get("data").get("order_no")
        else:
            raise ValueError(charge_res.get("msg"))
    else:
        raise ValueError(create_res.get("msg"))


def create_each_channel_normal_order(subject, mobile: str):
    """创建各个渠道的正价课订单"""
    # 被邀请人相关信息，订单由被邀请人下单
    user = fat_models.users.query_first(**{"mobile": mobile})
    if not user:
        raise ValueError("没有该用户账号，请输入正确的手机号")
    invitee_user = fat_siri.UsersSiri(user).data
    headers = {"Authorization": basic_auth(id=invitee_user["_id"], tok=invitee_user["tok"])}
    price = str(
        MySQL("eshop").query(
            f"select c.price_rmb from commodity_map cm join commodity c on cm.sxu_id = c.id where cm.id={subject};"
        )[0]["price_rmb"]
    )
    create_order_body = {
        "sp2xuId": subject,
        "payPrice": price,
        "number": 1,
        "shipping": True,
        "recipientInfo": {
            "recipient": "测试订单",
            "mobile": mobile,
            "addressProvince": "黑龙江省",
            "addressCity": "双鸭山市",
            "addressDistrict": "宝山区",
            "addressStreet": "测试地址",
        },
        "useGuadou": False,
        "guaDouNum": 0,
    }
    # 生成订单
    create_res = requests.post(
        url=f"https://fat.jiliguala.com/api/eshop/v2/orders",
        json=create_order_body,
        headers=headers,
        verify=False,
    ).json()
    # 若生成订单成功,支付订单
    if create_res.get("code") == 0:
        charge_body = {
            "oid": create_res["data"]["orderNo"],
            "channel": "wx_pub",
            "payTotal": float(price),
            "guadouDiscount": 0,
            "pay_wechat_token": None,
            "pay_wechat_token_typ": None,
            "extra": {"result_url": None, "success_url": None, "hb_fq_num": None},
        }
        charge_res = requests.post(
            url=f"https://fat.jiliguala.com/api/eshop/v2/orders/charge",
            json=charge_body,
            headers=headers,
            verify=False,
        ).json()
        if charge_res.get("code") == 0:
            return charge_res.get("data").get("order_no")
        else:
            raise ValueError(charge_res.get("msg"))
    else:
        raise ValueError(create_res.get("msg"))


def create_account_type_user(account_type, level="T1GE", mobile=None, bd=None):
    """
    创建账号类型用户
    :param account_type: 账号类型
    :param level: 课程级别
    :param mobile: 手机号
    :return:
    """
    mongoDb = mongoClient.get_client(db="JLGL")
    if account_type in ["bd_mobile_user", "bd_guest_user"]:
        if not bd:
            raise ValueError("账号类型为不同年龄宝贝时,bd不能为空")
        if account_type == "bd_mobile_user":
            mobile = api.register_user(mobile)
            user = mongoDb.get_collection("users").find_one({"mobile": mobile})
            api.onboarding_create_baby(bd, auth=get_user_basic_auth_by(user["_id"], user["tok"]))
            return {"mobile": mobile}
        elif account_type == "bd_guest_user":
            user = api.register_guest()
            api.onboarding_create_baby(bd, auth=get_user_basic_auth_by(user["_id"], user["tok"]))
            return {"guaid": user["guaid"]}
    mobile = api.register_user(mobile)
    user = mongoDb.get_collection("users").find_one({"mobile": mobile})
    if account_type == "getcNew":
        mongoDb.get_collection("user_flags").update_one(
            filter={"_id": user["_id"]}, update={"$set": {"allot99State": "GETC_NEW"}}, upsert=True
        )
    elif account_type == "newTurn":
        mongoDb.get_collection("user_flags").update_one(
            filter={"_id": user["_id"]}, update={"$set": {"allotNormal": "Z_NewMode_GEDoubleM"}}, upsert=True
        )
    elif account_type == "matcNew":
        mongoDb.get_collection("user_flags").update_one(
            filter={"_id": user["_id"]}, update={"$set": {"allot99MAK5State": "K5MATC_NEW"}}, upsert=True
        )
    elif account_type == "oldTurn":
        if not level:
            raise ValueError("导新机转时，level不能为空")
        mongoDb.get_collection("user_flags").update_one(
            filter={"_id": user["_id"]},
            update={"$set": {"allotNormalState": "JZ_Tradition", "allotNormalLevel": level}},
            upsert=True,
        )
    elif account_type == "1001004":
        api.onboarding_create_baby(bd=dateToTimeStamp(day=-1200), auth=get_user_basic_auth_by(user["_id"], user["tok"]))
        mongoDb.get_collection("user_flags").update_one(
            filter={"_id": user["_id"]},
            update={"$unset": {"allotNormalState": "", "allot99State": "", "allotNormalLevel": ""}},
        )
    elif account_type == "promoter":
        api.create_promoter(mobile, user["guaid"])
    return {"mobile": mobile}


def create_data_type_user(data_type, mobile=None, item_id=None):
    """
    创建数据类型用户
    :param data_type: 数据类型
    :param mobile: 手机号
    :param item_id: 课程itemid
    :return:
    """
    if data_type == "rePurchase":
        if not item_id:
            raise ValueError("itemId必填")
        mobile = api.register_user(mobile)
        user = mongoClient.get_client().get_collection("users").find_one({"mobile": mobile})
        auth = get_user_basic_auth_by(user["_id"], user["tok"])
        api.purchase_item(bid=user["b"][0], channel="alipay", item_id=item_id, basic_auth=auth)
        return {"mobile": mobile}


def reset_checkin_state(guaid, task: int, days: int):
    """重置用户打卡天数"""
    mongoDb = mongoClient.get_client(db="JLGL")
    user = mongoDb.get_collection("users").find_one({"$or": [{"guaid": guaid}, {"_id": guaid}]})
    if not user:
        raise ValueError("提供的guaid/uid不正确")
    try:
        uid = user["_id"]
        # Get case
        if task == "i0":
            # reset
            mongoDb.get_collection("check").delete_one({"_id": uid})
            print("RESET")
        else:
            case = checkcase.getCase(task, days)
            mongoDb.get_collection("check").delete_one({"_id": uid})
            mongoDb.get_collection("check").update_one({"_id": uid}, {"$set": case}, upsert=True)
            print("SET case, Task: {}, days: {}".format(task, days))

        return 0
    except (CasenameError, ParaError) as err:
        raise ValueError(err)


def update_promoter_state(mobile, state):
    """修改推广人状态"""
    if not state or not mobile:
        raise ValueError("手机号与状态必填")
    mongoDb = mongoClient.get_client(db="XSHARE")
    mongoDb.get_collection("promoter_accounts").update_one(
        filter={"mobile": mobile}, update={"$set": {"state": state}}, upsert=False
    )


def order_refund(mobile, oid):
    """强制退款"""
    if not oid and not mobile:
        raise ValueError("手机号或订单号必填其一")
    mongoDb = mongoClient.get_client(db="JLGL")
    orders = []
    if not oid:
        user = mongoDb.get_collection("users").find_one({"mobile": mobile})
        if not user:
            raise ValueError("手机号错误，没有该用户，请重新输入")
        mysqlDb = MySQL("eshop_orders")
        user_orders = mysqlDb.query(f"select * from orders where user_no = '{user['_id']}' and state in (2, 3)")
        orders = [order.get("order_no") for order in user_orders]
    else:
        orders.append(oid)
    if not orders:
        raise ValueError("该用户下暂无已支付订单")
    headers = {
        "authorization": "Basic MTNjNDlkNmM3YmI1NGQzYWE5NjNiMThkMjBlNGExNjE6MDFkNDVhYTczNGE4NDg4NGE4ODQ0OGIzOWI5ZGJkZTU=",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "postman-token": "1c376f8a-5a5e-00c3-40f0-c4244e78a5b5",
        "version": "1",
    }
    fail_order = []
    for id in orders:
        body = {"orderNo": id}
        resp = requests.request(
            method="POST",
            url="http://fat.jiliguala.com/api/trade-order/refund",
            json=body,
            headers=headers,
            verify=False,
        ).json()
        if resp.get("code") != 200:
            fail_order.append(id)
            continue
    if fail_order:
        msg = "".join(fail_order)
        raise ValueError(f"{msg}等订单退款失败，请稍后重试")


def query_all_class(mobile):
    """查询用户拥有的所有课程，仅课程中台"""
    if not mobile:
        raise ValueError("请输入手机号")
    mongoDb = mongoClient.get_client(db="JLGL")
    user = mongoDb.get_collection("users").find_one({"mobile": mobile})
    if not user:
        raise ValueError("没有该用户，请重新输入手机号")
    db = parse_db_tb(uid=user["_id"], table="lessonbuy", env="fat")
    if not db:
        raise ValueError("无该用户相关课程信息")
    mysql = MySQL(db=db[0])
    orders = mysql.query(sql=f"select * from {db[1]} where uid = '{user['_id']}'")
    resp = []
    if orders:
        for order in orders:
            order["possess_time"] = order["possess_time"].strftime("%Y-%m-%d %H:%M:%S")
            order["create_time"] = order["create_time"].strftime("%Y-%m-%d %H:%M:%S")
            order["update_time"] = order["update_time"].strftime("%Y-%m-%d %H:%M:%S")
            resp.append(json.dumps(order))
    return "".join(resp)


def remove_all_class(mobile):
    """全量删除用户拥有的课程，仅课程中台数据"""
    if not mobile:
        raise ValueError("请输入手机号")
    mongoDb = mongoClient.get_client(db="JLGL")
    user = mongoDb.get_collection("users").find_one({"mobile": mobile})
    if not user:
        raise ValueError("没有该用户，请重新输入手机号")
    db = parse_db_tb(uid=user["_id"], table="lessonbuy", env="fat")
    if not db:
        raise ValueError("无该用户相关课程信息")
    mysql = MySQL(db=db[0])
    orders = mysql.query(sql=f"select * from {db[1]} where uid = '{user['_id']}' and is_removed = 0 order by source")
    if not orders:
        raise ValueError("该用户下无需删除课程")
    orders_group = [
        {"source": key, "levelList": list(order_groups)} for key, order_groups in groupby(orders, itemgetter("source"))
    ]
    params = list(
        map(
            lambda x: dict(
                x, **{"uid": user["_id"], "levelList": [y["level_id"] for y in x["levelList"]], "source": x["source"]}
            ),
            orders_group,
        )
    )
    server_name = "course.course.atom"
    uri = "com.jiliguala.phoenix.course.courseatom.feign.LessonBuyFeignClient/remove/UserLessonBuyCRUDRequestDto"
    resp = get_lesson_score(server_name=server_name, uri=uri, params=params, env="fat")
    return resp


def courses_experience_lesson(subject, mobile):
    """一键开通体验课"""
    mobile = api.register_user(mobile)
    return create_each_channel_order(source="dataTools", subject=subject, invitee=mobile)


def courses_normal_lesson(subject, mobile):
    """一键开通正价课"""
    mobile = api.register_user(mobile)
    return create_each_channel_normal_order(subject=subject, mobile=mobile)


def logout_user(mobile):
    mongoDb = mongoClient.get_client(db="JLGL")
    # 被邀请人相关信息，订单由被邀请人下单
    user = mongoDb.get_collection("users").find_one({"mobile": mobile})
    if not user:
        raise ValueError("没有用户账号，请输入正确的手机号")
    api.logout_user(mobile=mobile, basic_auth=basic_auth(id=user["_id"], tok=user["tok"]))


def delete_user_order(mobile):
    """删除用户开课数据"""
    logout_user(mobile)
    api.register_user(mobile)


def create_inviter_order(group_id, captain, crews):
    mongo_jlgl = mongoClient.get_client(db="JLGL")
    mongo_xshare = mongoClient.get_client(db="XSHARE")
    # 如果有团员，先把团员状态重置
    if crews:
        [delete_user_order(mobile=crew) for crew in crews]
    else:
        size = mongo_xshare.get_collection("pintuan_config").find_one({"_id": group_id})["size"] - 1
        crews = [api.register_user() for _ in range(size)]
    # 清理团长的历史团单
    user = mongo_jlgl.get_collection("users").find_one({"mobile": captain})
    mongo_xshare.get_collection("xshare_group_purchase").delete_many({"inviterId": user["_id"]})
    # 创建拼团
    headers = {"Authorization": basic_auth(id=user["_id"], tok=user["tok"])}
    resp = requests.post(
        "https://fat.jiliguala.com/api/xshare/grouppurchase/inviter/order",
        json={"gpid": group_id},
        headers=headers,
        verify=False,
    ).json()
    if resp.get("code") != 0:
        raise ValueError(resp.get("msg"))

    group_oid = resp["data"]["gpOid"]
    for crew in crews:
        crew_user = mongo_jlgl.get_collection("users").find_one({"mobile": crew})
        headers = {"Authorization": basic_auth(id=crew_user["_id"], tok=crew_user["tok"])}
        resp = requests.post(
            "https://fat.jiliguala.com/api/xshare/grouppurchase/invitee/qualification",
            json={"gpid": group_id, "gpoid": group_oid},
            headers=headers,
            verify=False,
        ).json()
        if resp.get("code") != 0:
            raise ValueError(resp.get("msg"))
        if not resp["data"]["inviteeQualified"]:
            raise ValueError(f"{crew}没有该团参团资格")
        # 生成订单
        create_order_body = {
            "itemid": "H5_Sample_Pintuan",
            "nonce": now_timeStr(),
            "source": "dataTools",
            "sp2xuIds": [2460],  # 转介绍sgu:H5_XX_Sample
            "xshareInitiator": user["_id"],
            "sharer": user["_id"],
            "gpid": group_id,
            "gpoid": group_oid,
        }
        create_res = requests.put(
            url=f"https://fat.jiliguala.com/api/mars/order/create/v2",
            json=create_order_body,
            headers=headers,
            verify=False,
        ).json()
        # 若生成订单成功,支付订单
        if create_res.get("code") != 0:
            raise ValueError(create_res.get("msg"))
        charge_body = {
            "channel": "wx_wap",
            "oid": create_res["data"]["orderNo"],
            "extra": {"result_url": "https://devt.jiliguala.com/test"},
        }
        charge_res = requests.post(
            url=f"https://fat.jiliguala.com/api/mars/order/charge/v2",
            json=charge_body,
            headers=headers,
            verify=False,
        ).json()
        if charge_res.get("code") != 0:
            raise ValueError(charge_res.get("msg"))
    return mongo_xshare.get_collection("xshare_group_purchase").find_one({"inviterId": user["_id"]})


def lesson_progress(bid, lesson_id, is_first, finish_time):
    mysqlDb = MySQL("eduplatform0")
    _id = f"{time.time()}{random.randint(100, 999)}".replace(".", "")
    _time = pandas.to_datetime(datetime.datetime.fromtimestamp(finish_time / 1000)).strftime("%Y-%m-%d %H:%M:%S")
    mysqlDb.execute(
        f"insert into lesson_record0 (`id`, `bid`, `lesson_id`, `score`, `is_finish`, `finish_count`, `finish_time`, `create_time`, `update_time`) values ({_id}, '{bid}', '{lesson_id}', 100, 1, 1, {finish_time}, '{_time}', '{_time}');"
    )
    mysqlDb.execute(
        f"insert into lesson_flow_record1 (`id`, `bid`, `lesson_id`, `score`, `is_first`, `finish_time`, `create_time`, `update_time`) values ({_id}, '{bid}', '{lesson_id}', 100, {is_first}, {finish_time}, '{_time}', '{_time}');"
    )
    return _id
