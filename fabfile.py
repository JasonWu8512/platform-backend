# -*- coding: utf-8 -*-
# @Time    : 2020/10/27 3:59 下午
# @Author  : zoey
# @File    : fibfile.py
# @Software: PyCharm
from fabric.api import *

# 配置远程服务器
env.hosts = ['172.31.112.10']
# 端口
env.port = '22'
# 用户
env.user = 'deploy'
# 密码
env.password = 'niuniuniu168'


@task
def deploy():
    run('uname -s')
    # run('echo niuniuniu168| sudo -S docker network create --gateway 172.16.1.1 --subnet 172.16.1.0/24 app_bridge')
    run("echo niuniuniu168| sudo -S docker pull harbor.jlgltech.com/qa/zero:latest")
    run("echo niuniuniu168| sudo -S docker stop --time=20 $(sudo -S docker ps -a |grep zero |awk '{print $1}')")
    run("echo niuniuniu168| sudo -S docker rm $(sudo -S docker ps -a |grep zero |awk '{print $1}')")
    run("echo niuniuniu168| sudo -S docker rmi $(sudo -S docker images |grep none |awk '{print $3}')")
    # run('rm -rf /home/deploy/log/zero/*')
    run('echo niuniuniu168| sudo -S docker run --restart unless-stopped --network=host -v /home/deploy/log/zero:/home/deploy/log/zero -v /home/deploy/.ssh:/root/.ssh --name zero_server -p 8000:8000 -d harbor.jlgltech.com/qa/zero:latest /bin/bash deploy/deploy_server.sh')
    run('echo niuniuniu168| sudo -S docker run --restart unless-stopped --network=host -v /home/deploy/log/zero:/home/deploy/log/zero -v /data/jacoco/report:/data/jacoco/report --name zero_worker -d harbor.jlgltech.com/qa/zero:latest /bin/bash deploy/deploy_worker.sh')
    run('echo niuniuniu168| sudo -S docker run --restart unless-stopped --network=host -v /home/deploy/log/zero:/home/deploy/log/zero --name zero_beat -d harbor.jlgltech.com/qa/zero:latest /bin/bash deploy/deploy_beat.sh')
    run('echo niuniuniu168| sudo -S docker run --restart unless-stopped --network=host -v /home/deploy/log/zero:/home/deploy/log/zero --name zero_flower -p 5555:5555 -d harbor.jlgltech.com/qa/zero:latest /bin/bash deploy/deploy_flower.sh')
