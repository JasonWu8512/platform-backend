#!/usr/bin/python3
# encoding: utf-8
import requests
import json

from zero.settings import OPS_ALERT_ROBOT_WEBHOOK


def alert_robot(webhook: str, name: str, msg: str):
    msg_to_send = {"msgtype": "text", "text": {"content": f"【{name}】{msg}"}}

    requests.post(webhook, data=json.dumps(msg_to_send), headers={'Content-Type': 'application/json'})


def alert_ops_robot(msg: str):
    alert_robot(OPS_ALERT_ROBOT_WEBHOOK, '测试平台', msg)
