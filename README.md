# 帮助文档

# 先初始化venv，然后安装依赖
pip3 install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
# 安装依赖时如果碰到mysqlclient
本地先安装mysql：brew install mysql
# 运行server 必须先本地配好数据、mi好表连好VPN再起
python manage.py runserver
# 如果要debug，配置执行文件manage.py和参数runserver，点击调试按钮


# 运行celery worker
celery -A zero worker -l info
# 运行celery beat 
celery -A zero beat -l info
# 本地配置
可以根据自己部署的mysql、redis修改settings_local.py文件，记得把setting_local.py放入gitignore

# mi 表
python manage.py makemigrations <app>
python manage.py migrate
# 反向生成model,反向生成会覆盖重复导入入from django.db import models，所以建议生成路径取另一个，生成后的modelclass 复制到models.py文件就好
# 生成的model，都标记了manage=false，记得删掉
python manage.py inspectdb <table_name不指定就会反向生成数据库所有表> --database=jira > zero/jira/models_tmp.py 
