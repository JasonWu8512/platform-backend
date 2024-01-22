# -*- coding: utf-8 -*-
# @Time    : 2020/10/21 2:06 下午
# @Author  : zoey
# @File    : siris.py
# @Software: PyCharm
import json

from rest_framework import serializers

from zero.organization.models import AceLarkCallback, AceJiraProjectChat
from zero.testTrack import models
from zero.api.baseSiri import OffsetLimitSiri, CustomSerializer, DocumentCustomSerializer
from django.contrib.auth.models import User
from zero.testTrack.commands import ReviewStatus, PlanStatus, PlanInstanceStatus, PlanStage

'''请求参数serializers'''


class UpdateModuleTreeSerializer(serializers.Serializer):
    tree = serializers.DictField(required=True)
    proj_id = serializers.CharField(required=True)
    tree_id = serializers.DictField(required=False)
    remove_tree = serializers.DictField(required=False)


class UploadXmindCaseSerializer(serializers.Serializer):
    proj_id = serializers.CharField(required=True)
    tree_id = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    case_file = serializers.FileField(required=True)


class BaseUpdateCase(serializers.Serializer):
    type = serializers.ChoiceField(required=True,
                                   choices=['delete', 'update_case', 'update_plan_status', 'update_plan_executor',
                                            'update_review_status', 'update_plan_smoke_check'])
    # type = serializers.CharField(required=True)
    review_id = serializers.CharField(required=False)
    status = serializers.ChoiceField(required=False,
                                     choices=[status.value for status in ReviewStatus] + [status.value for status in
                                                                                          PlanStatus])
    plan_id = serializers.CharField(required=False)
    executor = serializers.CharField(required=False)
    case = serializers.DictField(required=False)
    smoke_check = serializers.ChoiceField(required=False, choices=[status.value for status in PlanStatus])


class SingleUpdateCase(BaseUpdateCase):
    add_step = serializers.ListField(required=False)
    delete_step = serializers.ListField(required=False)
    update_step = serializers.ListField(required=False)
    step_actual_results = serializers.ListField(required=False, default=[])
    step_actual_status = serializers.ListField(required=False, default=[])
    issue_ids = serializers.ListField(required=False, default=[])


class BatchUpdateCase(BaseUpdateCase):
    case_ids = serializers.ListField()


class GetCaseListSerializer(OffsetLimitSiri):
    proj_id = serializers.CharField(required=False)
    tree_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.ListField(required=False)
    reviewer = serializers.ListField(required=False)
    name = serializers.CharField(required=False, default='')
    creator = serializers.ListField(required=False)
    importance = serializers.ListField(required=False)
    executor = serializers.ListField(required=False)


class RelatePlanCaseSerializer(serializers.Serializer):
    tree_id = serializers.CharField(required=False)
    proj_id = serializers.CharField(required=False)
    operation = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    case_ids = serializers.ListField(required=False, default=[])


class GetPlanSerializer(OffsetLimitSiri):
    name = serializers.CharField(required=False, default='')
    proj_id = serializers.ListField(required=False)
    owner = serializers.ListField(required=False)
    status = serializers.ListField(required=False)
    stage = serializers.ListField(required=False)
    is_reject = serializers.BooleanField(required=False)


class GetPlanNoRelateCaseSerializer(OffsetLimitSiri):
    proj_id = serializers.CharField(required=False)
    tree_id = serializers.CharField(required=False)


class GetReviewSerializer(OffsetLimitSiri):
    name = serializers.CharField(required=False)
    status = serializers.ListField(required=False)
    proj_id = serializers.ListField(required=False)
    reviewer = serializers.ListField(required=False)
    creator = serializers.ListField(required=False)


class GetCaseTreeSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    proj_id = serializers.CharField(required=False)


'''返回体serializer'''


# class ManualCaseTree(serializers.ModelSerializer):
#     class Meta:
#         model = models.CaseModuleTree
#         fields = ('id', 'proj_id', 'tree', 'review_id')


class ManualCaseSerializer(DocumentCustomSerializer):
    description = serializers.CharField(allow_blank=True)
    class Meta:
        model = models.ManualCase
        fields = '__all__'
        extra_fields = ['status_chinese']


class TestPlanSerializer(CustomSerializer):
    percentage = serializers.SerializerMethodField()
    instance_status = serializers.SerializerMethodField()
    reject_count = serializers.SerializerMethodField()
    check_percentage = serializers.SerializerMethodField()

    def get_percentage(self, obj):
        cases = models.TestPlanCase.objects(plan_id=str(obj.id))
        total = len(cases)
        done = [case.status for case in cases if case.status in [PlanStatus.PASS.value, PlanStatus.SKIP.value]]
        return round(len(done) * 100 / total, 2) if total else 0

    def get_instance_status(self, obj):
        if obj.stage == PlanStage.SMOKE.value:
            if obj.approval_instance:
                instance_code = json.loads(obj.approval_instance).get("instance_codes")[-1]
                try:
                    return AceLarkCallback.objects.get(instance_code=instance_code, callback_type="approval_task").status
                except AceLarkCallback.DoesNotExist:
                    pass
            return PlanInstanceStatus.INIT.value

    def get_reject_count(self, obj):
        if obj.stage == PlanStage.SMOKE.value:
            if obj.approval_instance:
                instance_codes = json.loads(obj.approval_instance).get("instance_codes")
                count = len(AceLarkCallback.objects.filter(instance_code__in=instance_codes, callback_type="approval_task", status=PlanInstanceStatus.REJECTED.value))
                if count:
                    obj.reject_count = count
                    obj.save()
                return count

    def get_check_percentage(self, obj):
        if obj.stage == PlanStage.SMOKE.value:
            cases = models.TestPlanCase.objects(plan_id=str(obj.id))
            total = len(cases)
            done = [case.smoke_check for case in cases if case.smoke_check in [PlanStatus.PASS.value, PlanStatus.SKIP.value]]
            return round(len(done) * 100 / total, 2) if total else 0
        return None

    class Meta:
        model = models.TestPlanModel
        fields = '__all__'
        extra_fields = ['status_chinese', 'stage_chinese', 'proj_ids', 'proj_names', 'story_ids', 'instance_status', 'reject_count', 'pipeline_ids']


class CaseTreeSerializer(CustomSerializer):
    class Meta:
        model = models.ModuleTree
        fields = ('id', 'name', 'proj_id', 'parent')


class TestPlanCaseSerializer(DocumentCustomSerializer):
    case_detail = serializers.SerializerMethodField()

    def get_case_detail(self, obj):
        case = models.ManualCase.query_first(**{'id': obj.case_id})
        return ManualCaseSerializer(case).data

    class Meta:
        model = models.TestPlanCase
        fields = '__all__'
        extra_fields = ['status_chinese', 'issues']


class TestPlanTreeSerializer(DocumentCustomSerializer):
    class Meta:
        model = models.TestPlanTree
        fields = '__all__'


class ApprovalConfigSerializer(CustomSerializer):
    class Meta:
        model = AceJiraProjectChat
        fields = '__all__'


class TestReviewSerializer(CustomSerializer):
    class Meta:
        model = models.TestReviewModel
        fields = '__all__'
        extra_fields = ['status_chinese', 'reviewer_list']


class UserSiri(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email')
