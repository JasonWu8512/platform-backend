# -*- coding: utf-8 -*-
# @Time    : 2021/7/28 10:06 上午
# @Author  : zoey
# @File    : mongo.py
# @Software: PyCharm
import pymongo
from django.conf import settings

mongoOpts = {
    'fat': {
        "host": "10.100.128.122",
        "port": 27017,
        "db": "JLGL",
        "user": "JLAdmin",
        "pass": "niuniuniu168",
        "authsrc": "admin",
        "auth": "SCRAM-SHA-1"
    }
}


class mongoClient(object):
    _clients = {}

    @classmethod
    def get_client(cls, env='fat', db='JLGL'):
        if env in cls._clients:
            return cls._clients[env].get_database(db)
        mongo = mongoOpts[env]
        client = pymongo.MongoClient(
            mongo['host'], mongo['port'], username=mongo["user"], password=mongo["pass"], authSource=mongo["authsrc"],
            authMechanism=mongo["auth"])
        cls._clients[env] = client
        db = client.get_database(db)
        return db