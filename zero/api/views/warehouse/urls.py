
"""zero URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from zero.api.views.warehouse import houseMonitor
from zero.api.views.warehouse import crontabs

urlpatterns = [
    # url(r'monitor$', houseMonitor.MonitorManageViewSet.as_view({"get": "list", "post": "create"}), name='monitor'),
    url(r'^monitor$', houseMonitor.MonitorConfigViewSet.as_view(actions={"get": "list", "post": "create"}), name='monitor'),
    url(r'^monitor/update$', houseMonitor.MonitorConfigViewSet.as_view(
        actions={"get": "retrieve", "post": "update", "delete": "destroy"}), name='update'),
    url(r'^monitor-rules$', houseMonitor.MonitorRulesViewSet.as_view(actions={"get": "list"}), name='monitor-rules'),

    url(r'^crontabs$', crontabs.CrontabViewSet.as_view(actions={'get': 'list', 'post': 'create'}), name='crontabs'),

    # url(r"monitor/add$", houseMonitor.add_monitor, name="add_monitor"),
]
