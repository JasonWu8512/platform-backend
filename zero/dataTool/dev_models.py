from django.db import models

# Create your models here.
from zero.libs.baseModel import BaseDocument
import mongoengine as mongo
import shortuuid


class users(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    b = mongo.ListField()
    cts = mongo.DateTimeField()
    typ = mongo.StringField()
    mobile = mongo.StringField()
    lts = mongo.DateTimeField()
    tok = mongo.StringField()
    guaid = mongo.StringField()
    ava = mongo.StringField()
    nick = mongo.StringField()
    p = mongo.StringField()
    tts = mongo.DateTimeField()
    u = mongo.StringField()
    uts = mongo.DateTimeField()
    key = mongo.StringField()
    sms = mongo.DictField()
    curTyp = mongo.StringField()
    guadouBalance = mongo.FloatField()
    buystatus = mongo.BooleanField()
    ncnt = mongo.IntField()
    first_version = mongo.StringField()
    location = mongo.DictField()
    android = mongo.StringField()
    notif = mongo.DateTimeField()

    meta = {
        "db_alias": "jlgl_dev",
        "collection": "users"
    }


class user_devices(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    devices = mongo.DictField()

    meta = {
        "db_alias": "jlgl_dev",
        "collection": "user_devices"
    }


class pingxxorder(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    uid = mongo.StringField()
    cts = mongo.DateTimeField()

    meta = {
        "db_alias": "jlgl_dev",
        "collection": "pingxxorder"
    }


class lessonbuy(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    XX = mongo.DictField()
    MC = mongo.DictField()

    meta = {
        "db_alias": "jlgl_dev",
        "collection": "lessonbuy"
    }


class ghs_user(BaseDocument):
    _id = mongo.StringField(primary_key=True)

    meta = {
        "db_alias": "jlgl_dev",
        "collection": "ghs_user"
    }


class sc_possess(BaseDocument):
    _id = mongo.StringField(primary_key=True)

    meta = {
        "db_alias": "jlgl_dev",
        "collection": "sc_possess"
    }


class wc_users(BaseDocument):
    _id = mongo.ObjectIdField(primary_key=True)
    uid = mongo.StringField()
    unionId = mongo.StringField()

    meta = {
        "db_alias": "jlgl_dev",
        "collection": "wc_users"
    }


class wc_openusers(BaseDocument):
    _id = mongo.ObjectIdField(primary_key=True)
    unionId = mongo.StringField()
    appId = mongo.StringField()
    openId = mongo.StringField()

    meta = {
        "db_alias": "jlgl_dev",
        "collection": "wc_openusers"
    }


class promoter_accounts(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    unionId = mongo.StringField()
    level = mongo.StringField()
    openid = mongo.StringField()
    mobile = mongo.StringField()
    whitelist = mongo.BooleanField()
    uid = mongo.StringField()
    tok = mongo.StringField()
    state = mongo.StringField()
    totalAmount = mongo.IntField()
    totalRevenue = mongo.IntField()
    frozenRevenue = mongo.IntField()

    meta = {
        "db_alias": "xshare_dev",
        "collection": "promoter_accounts"
    }


# class promoter_users(BaseDocument):
#     _id = mongo.StringField(primary_key=True)
#     unionId = mongo.StringField()
#     level = mongo.StringField()
#     openid = mongo.StringField()
#     mobile = mongo.StringField()
#     whitelist = mongo.BooleanField()
#     uid = mongo.StringField()
#     tok = mongo.StringField()
#     state = mongo.StringField()
#     totalAmount = mongo.IntField()
#     totalRevenue = mongo.IntField()
#     frozenRevenue = mongo.IntField()
#
#     meta = {
#         "db_alias": "xshare_dev",
#         "collection": "promoter_users"
#     }


class promoter_wechat(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    uid = mongo.StringField()
    promoterId = mongo.StringField()

    meta = {
        "db_alias": "xshare_dev",
        "collection": "promoter_wechat"
    }


class promoter_status_log(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    login = mongo.BooleanField()
    createTime = mongo.DateTimeField()

    meta = {
        "db_alias": "xshare_dev",
        "collection": "promoter_status_log"
    }


class xshare_relationship(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    promoterId = mongo.StringField()
    uid = mongo.StringField()
    childUid = mongo.StringField()
    expirets = mongo.DateTimeField()
    relationType = mongo.IntField()

    meta = {
        "db_alias": "xshare_dev",
        "collection": "xshare_relationship"
    }


class promoter_paid_bind(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    promoterId = mongo.StringField()

    meta = {
        "db_alias": "xshare_dev",
        "collection": "promoter_paid_bind"
    }


class promoter_order(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    promoterId = mongo.StringField()
    status = mongo.StringField()

    meta = {
        "db_alias": "xshare_dev",
        "collection": "promoter_order"
    }


class xshare_group_purchase(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    gpid = mongo.StringField()
    title = mongo.StringField()
    status = mongo.StringField()
    inviterId = mongo.StringField()
    inviter_vip_openid = mongo.StringField()
    size = mongo.IntField(default=0)
    invitee = mongo.ListField()
    inviterInfo = mongo.DictField()
    cts = mongo.DateTimeField()
    ets = mongo.DateTimeField()
    uts = mongo.DateTimeField()
    createAwardId = mongo.StringField()
    joinAwardId = mongo.StringField()
    createAwardTtl = mongo.StringField()
    joinAwardTtl = mongo.StringField()
    type = mongo.StringField()
    itemId = mongo.StringField()

    meta = {
        "db_alias": "xshare_dev",
        "collection": "xshare_group_purchase",
        "indexes": ["size"]
    }


class xshare_screenshot_history(BaseDocument):
    _id = mongo.StringField(primary_key=True)
    uid = mongo.StringField()
    mobile = mongo.StringField()
    status = mongo.StringField()

    meta = {
        "db_alias": "xshare_dev",
        "collection": "xshare_screenshot_history"
    }
