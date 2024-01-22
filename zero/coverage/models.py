import json
import socket

from django.db import models
from zero.libs.baseModel import BaseModel
from zero.coverage.commands import JenkinsTaskStatus, PipelineBusiness, Terminal


# Create your models here.

# jenkinsTaskStatus = (
#     ('pending', "等待执行"),
#     ('running', "执行中"),
#     ('success', "执行成功"),
#     ('fail', "执行失败"),
# )
# pipelineBusiness = (
#     ('trade', "交易中台"),
#     ('promoter', '转推'),
#     ('saturn', '下沉'),
#     ('reading', '呱呱阅读'),
#     ('crm', 'Crm'),
#     ('jlgl', '叽里呱啦')
# )


class GitProject(BaseModel):
    """git 工程"""
    name = models.CharField(max_length=32, help_text="git 工程名")
    ssh_url = models.CharField(unique=True, max_length=255, help_text="ssh git clone url")
    server_ip = models.CharField(blank=True, null=True, max_length=16, help_text='jacocoagent tcpserver ip')
    server_port = models.CharField(max_length=16, help_text='jacocoagent tcpserver port')
    fat_job_name = models.CharField(max_length=64, help_text='fat 环境该服务的发版jobname')

    class Meta:
        db_table = 'coverage_git_project'

    @classmethod
    def get_dynamic_server_ip(cls, ssh_url):
        """使用 socket.getaddrinfo() 方法获取动态 server_ip"""
        try:
            result = socket.getaddrinfo(ssh_url.split('@')[-1], None)
            return result[0][4][0]
        except Exception as e:
            print(e)
            return None


class JenkinsProjectCommit(BaseModel):
    """jenkins发版commit记录"""
    short_commit = models.CharField(max_length=16, help_text='jenkins的commit')
    project_name = models.CharField(max_length=32, help_text='git工程名')
    project_id = models.IntegerField(null=True, help_text='工程id')

    class Meta:
        db_table = 'coverage_jenkins_project_commit'


class FullCoverage(BaseModel):
    """"""
    project_id = models.IntegerField(help_text='工程id')
    project_name = models.CharField(max_length=32, help_text='git工程名')
    # version = models.CharField(max_length=16, help_text='发布版本')
    line_rate = models.DecimalField(max_digits=18, decimal_places=2, help_text='行覆盖率')
    line_all = models.IntegerField(help_text='总行数')
    line_cover = models.IntegerField(help_text='覆盖行数')
    branch_rate = models.DecimalField(max_digits=18, decimal_places=2, help_text='分支覆盖率')
    branch_all = models.IntegerField(help_text='总分支数')
    branch_cover = models.IntegerField(help_text='覆盖分支数')
    api_coverage = models.DecimalField(max_digits=18, decimal_places=2, help_text='接口覆盖率')
    coverage_id = models.CharField(max_length=32, help_text='构建生成报告的uid')

    class Meta:
        db_table = 'coverage_full'


class DiffCoverage(BaseModel):
    project_id = models.IntegerField(help_text='工程id')
    project_name = models.CharField(max_length=32, help_text='git工程名')
    line_rate = models.DecimalField(max_digits=18, decimal_places=2, help_text='行覆盖率')
    line_all = models.IntegerField(help_text='总行数')
    line_cover = models.IntegerField(help_text='覆盖行数')
    coverage_id = models.CharField(max_length=32, help_text='报告的uid')

    class Meta:
        db_table = 'coverage_diff'


class JenkinsBuildTask(BaseModel):
    build_number = models.IntegerField(help_text='jenkins build number', null=True)
    coverage_job_name = models.CharField(max_length=64, default='test/coverage', help_text='覆盖率构建job', null=True)
    build_status = models.CharField(max_length=16, help_text='jenkins 构建状态', choices=JenkinsTaskStatus.details(),
                                    default='pending')
    project_git = models.CharField(max_length=255, help_text='工程git地址后缀')
    end_commit = models.CharField(max_length=128, help_text='当前分支')
    compare_branch = models.CharField(max_length=16, default='origin/master', help_text='对比分支')
    pipeline_id = models.IntegerField(null=False, help_text='所属流水线')
    pipeline_name = models.CharField(null=True, blank=True, max_length=64, help_text='流水线名称')
    username = models.CharField(max_length=64, help_text='触发者', blank=True, null=True)
    diff_coverage_report = models.CharField(max_length=128, help_text='增量覆盖率报告url', null=True, blank=True)
    full_coverage_report = models.CharField(max_length=128, help_text='全量覆盖率报告url', null=True, blank=True)
    recover_times = models.IntegerField(default=0, help_text='重试次数')

    @property
    def status_chinese(self):
        return JenkinsTaskStatus.get_chinese(self.build_status)

    class Meta:
        db_table = 'coverage_jenkins_build'


class CoveragePipeline(BaseModel):
    name = models.CharField(unique=True, max_length=64, help_text='流水线名称')
    step1 = models.CharField(max_length=32, default='服务端发版', null=True, blank=True)
    step2 = models.CharField(max_length=32, default='覆盖率收集', null=True, blank=True)
    project_name = models.CharField(max_length=32, help_text='git工程名')
    project_id = models.IntegerField(unique=True, help_text='工程id')
    coverage_params = models.TextField(null=False, blank=False, help_text='覆盖率收集job构建关键参数')
    deploy_status = models.CharField(max_length=16, choices=JenkinsTaskStatus.details(), default='pending')
    coverage_status = models.CharField(max_length=16, choices=JenkinsTaskStatus.details(), default='pending')
    owner = models.CharField(max_length=16, null=True, blank=True)
    mark = models.TextField(null=False, blank=False, help_text='备注',
                            default=json.dumps({'coverage': '', 'deploy': ''}))
    notify_chat_ids = models.CharField(max_length=255, help_text='通知群')
    deploy_id = models.IntegerField(help_text='Jenkins构建号', null=True, default=None)
    sonar_id = models.IntegerField(help_text='Jenkins构建号', null=True, default=None)
    sonar_job = models.CharField(max_length=32, help_text='Jenkins构建job', null=True, default=None)
    sonar_status = models.CharField(max_length=16, help_text='sonar job构建状态', choices=JenkinsTaskStatus.details(),
                                    default='pending')
    recover_times = models.IntegerField(default=0, help_text='重试次数')
    business = models.CharField(max_length=16, help_text='业务线', choices=PipelineBusiness.details(), default='jlgl')
    terminal = models.CharField(max_length=16, help_text='技术端', choices=Terminal.details(), default='BE')

    @property
    def end_commit(self):
        query = JenkinsProjectCommit.objects.filter(project_name=self.project_name).order_by('-id')
        if len(query):
            return query.first().short_commit
        return

    class Meta:
        db_table = 'coverage_pipline'


class CoverageServerDeployHistory(BaseModel):
    pipeline_id = models.IntegerField(null=False, help_text='所属流水线')
    project_name = models.CharField(max_length=32, help_text='git工程名')
    username = models.CharField(max_length=64, help_text='触发者', blank=True, null=True)
    commit_id = models.CharField(max_length=128, help_text='当前构建分支')
    build_id = models.IntegerField(help_text='Jenkins构建号', null=True)
    job_name = models.CharField(max_length=64, help_text='fat 环境该服务的发版jobname')
    status = models.CharField(max_length=16, choices=JenkinsTaskStatus.details(), default='pending')
    recover_times = models.IntegerField(default=0, help_text='重试次数')

    @property
    def status_chinese(self):
        return JenkinsTaskStatus.get_chinese(self.status)

    class Meta:
        db_table = 'coverage_deploy_history'
