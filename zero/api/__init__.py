from rest_framework.views import APIView
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet


class BaseViewSet(mixins.CreateModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  GenericViewSet):
    # authentication_classes = [JSONWebTokenAuthentication]
    # lookup_field = 'id'  # url中传递的参数作为id去数据库中查找，而不是默认的pk
    filtered = None


class BaseApiView(APIView):
    pass
