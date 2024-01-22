# Generated by Django 2.2 on 2021-09-15 14:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BuriedTestProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='项目名称,^_^dev结尾', max_length=64)),
                ('api_key', models.CharField(help_text='api_key', max_length=64, unique=True)),
                ('api_key_desc', models.CharField(help_text='api_key desc', max_length=255)),
                ('platform', models.CharField(help_text='平台', max_length=48)),
                ('version', models.CharField(help_text='项目当前版本', max_length=48)),
                ('deleted', models.IntegerField(default=0, help_text='是否删除')),
                ('is_cross_project', models.BooleanField(default=False, help_text='是否组合项目')),
                ('create_at', models.DateTimeField(auto_now_add=True)),
                ('update_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'lesson_central_buriedtestproject',
            },
        ),
        migrations.CreateModel(
            name='RPCEnv',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='名称', max_length=32, null=True)),
                ('env', models.CharField(help_text='url地址', max_length=32, null=True)),
            ],
            options={
                'db_table': 'rpc_env',
            },
        ),
        migrations.CreateModel(
            name='RPCServer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='名称', max_length=64)),
                ('server', models.CharField(help_text='url地址', max_length=128)),
            ],
            options={
                'db_table': 'rpc_server',
            },
        ),
        migrations.CreateModel(
            name='RPCUri',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='名称', max_length=64, null=True)),
                ('uri', models.CharField(help_text='url地址', max_length=128)),
                ('operation', models.CharField(help_text='用户操作，lesson开头', max_length=128, null=True)),
            ],
            options={
                'db_table': 'rpc_uri',
            },
        ),
        migrations.CreateModel(
            name='LessonScore',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('server', models.CharField(default='course.course.atom', help_text='服务器', max_length=32)),
                ('env', models.CharField(default='env', help_text='环境配置', max_length=32)),
                ('params', models.TextField(help_text='接口参数', null=True)),
                ('data', models.TextField(help_text='查询结果', null=True)),
                ('uri', models.ForeignKey(help_text='url', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='lesson_central.RPCUri')),
            ],
            options={
                'db_table': 'lesson_score',
            },
        ),
    ]