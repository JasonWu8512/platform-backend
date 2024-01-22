#! /usr/bin/env bash

gunicorn zero.wsgi -c gunicorn_config.py 