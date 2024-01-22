#! /usr/bin/env bash

celery -A zero beat -l info --logfile=/home/deploy/log/zero/celery_beat.log --scheduler django_celery_beat.schedulers:DatabaseScheduler