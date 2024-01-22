import requests
from rest_framework import serializers
from rest_framework.decorators import detail_route

from zero import settings
from zero.api import BaseViewSet
from zero.api.decorators import schema
from zero.coverage.commands import SonarClient
from zero.coverage.models import CoveragePipeline
import zero.utils.superResponse as Response
from rest_framework.views import APIView

from zero.utils.format import get_data


class SonarStatusPipeline(serializers.Serializer):
    pipeline_ids = serializers.ListField(required=True)


class SonarViewSet(APIView):

    @schema(SonarStatusPipeline)
    def get(self, request):
        pipeline_ids = self.filtered.get("pipeline_ids")
        print(pipeline_ids)
        project_name_query_set = CoveragePipeline.objects.filter(id__in=pipeline_ids).values_list("project_name", flat=True)
        sonar_list = SonarClient.get_sonar_gate_results_by_app_name(project_name_query_set)
        print(sonar_list)
        return Response.success(data={'data': sonar_list, 'total': len(sonar_list)})

    def post(self, request):
        offset = request.data.get("offset")
        limit = request.data.get("limit")
        if offset == '0' or offset == 0:
            offset = '1'
        list_result, total = SonarClient.get_project_list(limit, offset)
        return Response.success(data={'data': list_result, 'total': total})
