#! /usr/bin/env bash


#celery multi start w1 -A zero -l info  --logfile=$HOME/log/zero/celery_woker.log --pidfile=$HOME/run/celery/%n.pid
celery worker --app=zero -Q celery,high_celery --loglevel=info --logfile=/home/deploy/log/zero/celery_worker.log