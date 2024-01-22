import requests
from retry import retry


@retry(tries=10, delay=1)
def request(method, *args, **kwargs):
    return requests.request(method, *args, **kwargs)


def get(*args, **kwargs):
    return request("get", *args, **kwargs)


def put(*args, **kwargs):
    return request("put", *args, **kwargs)


def post(*args, **kwargs):
    return request("post", *args, **kwargs)


def patch(*args, **kwargs):
    return request("patch", *args, **kwargs)


def delete(*args, **kwargs):
    return request("delete", *args, **kwargs)


def session():
    return requests.session()


class Session(requests.Session):
    pass
