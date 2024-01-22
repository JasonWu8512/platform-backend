#!/usr/bin/env python
# -*- coding: utf-8 -*-

# https://github.com/nacos-group/nacos-sdk-python

import json
import time
import random
import threading
from typing import List

import gevent
import gevent.pool
import requests
import nacos
import json
from nacos.listener import SubscribeListener
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

dev_nacos_cfg = {
        "server_addrs": "nacos.jlgltech.com:80",
        "namespace": "public",
        "cluster_name": "DEFAULT",
        "group_name": "DEFAULT_GROUP",
        "port": 8191
    }


def get_nacos_client(cfg: dict, logger: object) -> dict:
    """
    获取nacos客户端

    cfg
        server_addrs: str
        namespace: str
        cluster_name: str
        group_name: str
    logger: logger
    """
    return {
        "server_addrs": cfg["server_addrs"],
        "namespace": cfg["namespace"],
        "cluster_name": cfg["cluster_name"],
        "group_name": cfg["group_name"],
        "nacos_client": nacos.NacosClient(
            cfg["server_addrs"], namespace=cfg["namespace"]
        ),
        "instances": {},
        "logger": logger,
        "services": {},
    }


def register_to_nacos(
    cli: dict,
    service_name: str,
    host_ip: str,
    port: int,
    weight: float = 1.0,
    metadata: dict = None,
    heatbeat_delta: int = 5,
):
    """
    注册至nacos

    service_name: 服务名
    host_ip: 宿主机ip
    port: 服务端口
    weight: 权重
    metadata: 元数据
    heatbeat_delta: 心跳间隔(秒)

    """

    def keep_heatbeat():
        while 1:
            _heatbeat()
            gevent.sleep(heatbeat_delta)

    def _heatbeat():
        cli["nacos_client"].send_heartbeat(
            service_name,
            host_ip,
            port,
            cli["cluster_name"],
            group_name=cli["group_name"],
        )

    # 注册
    cli["nacos_client"].add_naming_instance(
        service_name,
        host_ip,
        port,
        cli["cluster_name"],
        weight=weight,
        metadata=metadata,
        healthy=True,
        group_name=cli["group_name"],
    )

    # 发送心跳
    gpool = gevent.pool.Pool(size=1)
    nacos_heatbeater = gpool.spawn(keep_heatbeat)
    cli["services"][service_name] = {
        "heatbeator": nacos_heatbeater,
        "host_ip": host_ip,
        "port": port,
    }


def unregister(cli: dict, service_name: str):
    """
    注销一个服务实例
    """
    cli["logger"].warn("service {} unregister from nacos".format(service_name))
    if service_name in cli["services"]:
        service = cli["services"][service_name]
        gevent.kill(service["heatbeator"])
        del cli["services"][service_name]
    cli["nacos_client"].remove_naming_instance(
        service_name, service["host_ip"], service["port"]
    )


def subscribe_service(cli: dict, service_names: List[str], listen_interval: int = 5):
    """
    订阅服务

    服务数据结构

    service_name =>
        instance_id 实例id
        metadata    元数据
        ip          ip地址
        port        端口
        weight      权重
        enabled     是否可用
    """

    def _cast_service(host: dict) -> dict:
        return {
            "instance_id": host["instanceId"],
            "metadata": host["metadata"],
            "ip": host["ip"],
            "port": host["port"],
            "weight": host["weight"],
            "enabled": host["enabled"],
        }

    def _service_listener(event: str, instance: object):
        """
        服务监听的hook函数

        # 新节点加入
        service changing ==>  ADDED {
            "valid": true,
            "marked": false,
            "metadata": {},
            "instanceId": "10.50.126.0#7200#DEFAULT#DEFAULT_GROUP@@jlgl.crm.alliance",
            "port": 7200,
            "healthy": true,
            "ip": "10.50.126.0",
            "clusterName": "DEFAULT",
            "weight": 1,
            "ephemeral": true,
            "serviceName": "jlgl.crm.alliance",
            "enabled": true
        }

        # 节点修改
        service changing ==>  MODIFIED {
            "valid": true,
            "marked": false,
            "metadata": {},
            "instanceId": "10.50.126.0#7200#DEFAULT#DEFAULT_GROUP@@jlgl.crm.alliance",
            "port": 7200,
            "healthy": true,
            "ip": "10.50.126.0",
            "clusterName": "DEFAULT",
            "weight": 1,
            "ephemeral": true,
            "serviceName": "jlgl.crm.alliance",
            "enabled": true
        }

        # 节点注销
        service changing ==>  DELETED {
            "valid": true,
            "marked": false,
            "metadata": {},
            "instanceId": "10.50.126.0#7200#DEFAULT#DEFAULT_GROUP@@jlgl.crm.alliance",
            "port": 7200,
            "healthy": true,
            "ip": "10.50.126.0",
            "clusterName": "DEFAULT",
            "weight": 1.0,
            "ephemeral": true,
            "serviceName": "jlgl.crm.alliance",
            "enabled": true
        }

        """
        cli["logger"].warn(
            "service changing ==> {}\n{}".format(event, json.dumps(instance.instance))
        )

        # NOTE:
        # add your own events here

    # 订阅这些服务

    for service_name in service_names:
        cli["instances"][service_name] = 1
        listener = SubscribeListener(
            fn=_service_listener, listener_name="{}_listener".format(service_name)
        )
        cli["logger"].warn("开始监听{}".format(service_name))
        cli["nacos_client"].subscribe(
            listener,
            listen_interval,
            service_name,
            cli["cluster_name"],
            cli["namespace"],
            cli["group_name"],
        )


def unsubscribe_service(cli: dict, service_name: str):
    """
    取消订阅
    """
    cli["nacos_client"].unsubscribe(service_name, "{}_listener".format(service_name))
    cli["instances"][service_name] = 0


def unsubscribe_all(cli):
    """
    全部取消订阅
    """
    for service_name, listening in cli["instances"].items():
        if listening:
            unsubscribe_service(cli, service_name)


def display_instances(cli: dict):
    """
    展示已订阅的服务
    """
    # print(json.dumps(cli["instances"], indent=4))
    for service_name, listening in cli["instances"].items():
        if listening:
            print("{} >>>>>>>>>>>>>".format(service_name))
            for instance in (
                cli["nacos_client"]
                .subscribed_local_manager.get_local_instances(service_name)
                .values()
            ):
                print(instance.instances)


def get_local_instances(cli: dict, service_name: str) -> List[dict]:
    """
    获取服务的节点信息

    [
        {
            "valid": true,
            "marked": false,
            "metadata": {},
            "instanceId": "10.50.126.0#8191#DEFAULT#DEFAULT_GROUP@@base-sso-atom",
            "port": 8191,
            "healthy": true,
            "ip": "10.50.126.0",
            "clusterName": "DEFAULT",
            "weight": 1.0,
            "ephemeral": true,
            "serviceName": "base-sso-atom",
            "enabled": true
        },
        ....
    ]
    """
    instance_map = cli["nacos_client"].subscribed_local_manager.get_local_instances(
        service_name
    )
    if instance_map:
        return list([elem.instance for elem in instance_map.values()])
    return []


def get_random_instance(cli: dict, service_name: str) -> dict:
    """
    随机获取一个服务实例

    instance
        ip          ip地址
        port        端口
    """

    def _weight_random(weights: List[float]) -> int:
        """
        加权随机
        """
        weight_sum = sum(weights)
        t = random.random()

        for i, w in enumerate(weights):
            t -= w / weight_sum
            if t < 0:
                return i
        return len(weights) - 1

    instances = [
        inst for inst in get_local_instances(cli, service_name) if inst["enabled"]
    ]

    if len(instances) == 0:
        return None

    # 加权随机一个节点

    weights = [inst["weight"] for inst in instances]

    instance = instances[_weight_random(weights)]

    return {"ip": instance["ip"], "port": instance["port"]}


class ServiceNotAvailable(Exception):
    """
    无可用服务异常
    """

    pass


class InvalidCallMethod(Exception):
    """
    方法异常
    """

    pass


def rpc_call(
    cli: dict,
    service_name: str,
    method: str,
    uri: str,
    headers: dict,
    payload: any,
    https_enable: bool = False,
    retry_times: int = 3,
) -> requests.Response:

    instance = get_random_instance(cli, service_name)

    if not instance:
        raise ServiceNotAvailable

    method_processor = {
        "POST": _do_post,
        "GET": _do_get,
        # TODO
        "PUT": None,
        "PATCH": None,
        "DELETE": None,
    }

    if method not in method_processor:
        raise InvalidCallMethod

    server_response: requests.Response = method_processor[method](
        _cast_url(instance, uri, https_enable), headers, payload
    )
    while server_response.status_code != 200 and retry_times > 0:
        server_response: requests.Response = method_processor[method](
            _cast_url(instance, uri, https_enable), headers, payload
        )
        retry_times -= 1
    return server_response


def _cast_url(instance: dict, uri: str, https_enable: bool = False):
    if uri.startswith("/"):
        pass
    else:
        uri = "/" + uri

    if https_enable:
        return "https://{}:{}{}".format(instance["ip"], instance["port"], uri)
    return "http://{}:{}{}".format(instance["ip"], instance["port"], uri)


def _do_post(
    url: str, headers: dict, payload: any, timeout: float = 3
) -> requests.Response:
    return requests.post(url, headers=headers, data=payload, timeout=timeout)


def _do_get(
    url: str, headers: dict, payload: any, timeout: float = 3
) -> requests.Response:
    return requests.get(url, headers=headers, params=payload, timeout=timeout)

def call_sso(cli: dict, call: str, *args, **kwargs):
    payload = {"args": args, "kwargs": kwargs}
    reply = rpc_call(cli, 'base-sso-atom', 'POST', call, {"content-type":"application/json"}, json.dumps(payload))
    return reply.json()

def sso_auth_token(sso_auth_code: str):
    cli = get_nacos_client(dev_nacos_cfg, logging)
    # sso
    subscribe_service(cli, ['base-sso-atom'])
    reply = call_sso(cli, 'service-ssoatom/auth_token', app_name="QA", sso_auth_code=sso_auth_code)
    return reply

def sso_account(access_token: str, uid: str):
    cli = get_nacos_client(dev_nacos_cfg, logging)

    # sso
    subscribe_service(cli, ['base-sso-atom'])
    reply = call_sso(cli, 'service-ssoatom/get_account', app_name="QA", access_token=access_token, target_account_identity=uid)
    return reply

def sso_logout(access_token):
    cli = get_nacos_client(dev_nacos_cfg, logging)
    # sso
    subscribe_service(cli, ['base-sso-atom'])
    reply = call_sso(cli, 'service-ssoatom/logout_sso', app_name="QA", access_token=access_token)
    return reply

