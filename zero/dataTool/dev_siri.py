# coding=utf-8
# @Time    : 2020/12/9 3:05 下午
# @Author  : jerry
# @File    : dev_siri.py
from rest_framework_mongoengine.serializers import DocumentSerializer
from zero.dataTool.dev_models import *

"""返回请求体的serializer"""


class PromoterWechatSiri(DocumentSerializer):
    class Meta:
        model = promoter_wechat
        fields = '__all__'


class UsersSiri(DocumentSerializer):
    class Meta:
        model = users
        fields = '__all__'


class User_devicesSiri(DocumentSerializer):
    class Meta:
        model = user_devices
        fields = '__all__'


class PingxxorderSiri(DocumentSerializer):
    class Meta:
        model = pingxxorder
        fields = '__all__'


class LessonbuySiri(DocumentSerializer):
    class Meta:
        model = lessonbuy
        fields = '__all__'


class PromoterAccountsSiri(DocumentSerializer):
    class Meta:
        model = promoter_accounts
        fields = '__all__'


class XshareScreenshotHistorySiri(DocumentSerializer):
    class Meta:
        model = xshare_screenshot_history
        fields = '__all__'


class XshareGroupPurchaseSiri(DocumentSerializer):
    class Meta:
        model = xshare_group_purchase
        fields = '__all__'
