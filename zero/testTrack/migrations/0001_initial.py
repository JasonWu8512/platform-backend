# Generated by Django 2.2 on 2021-09-15 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ModuleTree',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='创建时间', verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='上次修改时间', verbose_name='上次修改时间')),
                ('name', models.CharField(max_length=255)),
                ('parent', models.CharField(blank=True, max_length=15, null=True)),
                ('proj_id', models.CharField(max_length=15)),
                ('deleted', models.BooleanField(default=False, serialize=False)),
            ],
            options={
                'db_table': 'module_tree',
            },
        ),
        migrations.CreateModel(
            name='TestPlanModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='创建时间', verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='上次修改时间', verbose_name='上次修改时间')),
                ('name', models.CharField(blank=True, max_length=255)),
                ('epic_ids', models.CharField(blank=True, max_length=255, serialize=False)),
                ('stories', models.CharField(blank=True, max_length=255, null=True, serialize=False)),
                ('sprint_id', models.CharField(max_length=32)),
                ('proj_id_list', models.CharField(default='[]', max_length=255, serialize=False)),
                ('proj_name_list', models.TextField(default='[]', max_length=65535, serialize=False)),
                ('stage', models.CharField(blank=True, max_length=255)),
                ('target_start', models.DateTimeField(help_text='目标开始时间', null=True, verbose_name='目标开始时间')),
                ('target_end', models.DateTimeField(help_text='目标结束时间', null=True, verbose_name='目标结束时间')),
                ('actual_start', models.DateTimeField(help_text='实际开始时间', null=True, verbose_name='实际开始时间')),
                ('actual_end', models.DateTimeField(help_text='实际结束时间', null=True, verbose_name='实际结束时间')),
                ('description', models.TextField(blank=True, null=True)),
                ('owner', models.CharField(max_length=255)),
                ('approval_instance', models.TextField(blank=True, max_length=65535, null=True)),
                ('status', models.CharField(default='init', max_length=255)),
                ('parent', models.IntegerField(default=None, null=True)),
                ('has_rejected', models.BooleanField(default=False, serialize=False)),
                ('report_components', models.CharField(default='1,2,3,4,5,6,7', max_length=255)),
                ('issue_jql', models.TextField(blank=True, null=True)),
                ('history_id', models.CharField(blank=True, help_text='自动化构建id', max_length=16, null=True)),
                ('deleted', models.BooleanField(default=False, serialize=False)),
                ('reject_count', models.IntegerField(blank=True, null=True)),
                ('pipelines', models.CharField(blank=True, help_text='关联流水线', max_length=64, null=True, serialize=False)),
            ],
            options={
                'db_table': 'test_plan',
            },
        ),
        migrations.CreateModel(
            name='TestReviewModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='创建时间', verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='上次修改时间', verbose_name='上次修改时间')),
                ('name', models.CharField(blank=True, max_length=255)),
                ('proj_id', models.IntegerField(blank=True)),
                ('proj_key', models.CharField(blank=True, max_length=255)),
                ('tree_id', models.CharField(blank=True, max_length=255, unique=True)),
                ('target_end', models.DateTimeField(help_text='目标结束时间', null=True, verbose_name='目标结束时间')),
                ('description', models.TextField(blank=True, null=True)),
                ('reviewer', models.CharField(blank=True, max_length=255, null=True, serialize=False)),
                ('creator', models.CharField(max_length=255, null=True)),
                ('status', models.CharField(default='init', max_length=15)),
                ('deleted', models.BooleanField(default=False, serialize=False)),
            ],
            options={
                'db_table': 'test_review',
            },
        ),
    ]