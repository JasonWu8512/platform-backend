# -*- coding: utf-8 -*-
# @Time    : 2021/2/23 2:19 下午
# @Author  : zoey
# @File    : coverage.py
# @Software: PyCharm
import zero.utils.superResponse as Response
from django.db.models import Q
from zero.api import BaseViewSet
from rest_framework.decorators import list_route, detail_route
from zero.coverage.siris import *
from zero.coverage.commands import jenkinsTool, JenkinsTaskStatus
from zero.auto.commands import gitTool
from zero.coverage.tasks import trigger_coverage_job, recovery_deploy_server, trigger_deploy_job
from zero.utils.format import get_data
from zero.api.decorators import schema
from zero.api.decorators import login_or_permission_required
from urllib.error import HTTPError
import json


class GitProjectViewSet(BaseViewSet):
    queryset = GitProject.objects.all()
    serializer_class = GitProjectSerializer

    def list(self, request, *args, **kwargs):
        query = self.get_queryset()
        data = GitProjectSerializer(query, many=True).data
        return Response.success(data=data)



class FullCoverageViewSet(BaseViewSet):
    queryset = FullCoverage.objects.all()
    serializer_class = FullCoverageSerializer
    lookup_field = 'coverage_uid'

    def get(self, request, pk=None):
        pass

    @schema(GetCoverageReport)
    def list(self, request, *args, **kwargs):
        offset, limit, project_name = get_data(self.filtered, 'offset', 'limit', 'project_name')
        query = FullCoverage.objects.filter(project_name__contains=project_name)
        data = FullCoverageSerializer(query[offset: offset + limit], many=True).data
        return Response.success(data=data)

    @list_route(methods=['get'], url_path='trend')
    def get_coverage_trend(self, request):
        proj_id = request.query_params['proj_id']
        commit_id = request.query_params.get('commit_id')
        query = Q(project_id=proj_id)
        if commit_id:
            coverage_ids = list(JenkinsBuildTask.objects.filter(end_commit=commit_id).values_list('id', flat=True))
            if not coverage_ids:
                return Response.bad_request(message=f'该流水线没有过{commit_id}的覆盖率构建')
            query &= Q(coverage_id__in=coverage_ids)
        data = FullCoverageSerializer(FullCoverage.objects.filter(query).order_by('-line_rate')[:10], many=True).data
        data.sort(key=lambda x: x['created_at'])
        xAxis_data = [item['created_at'].split('.')[0] for item in data]
        series = [round(float(item['line_rate']) * 100, 1) for item in data]
        res_data = {'xAxis': xAxis_data, 'series': series}
        return Response.success(data=res_data)


class DiffCoverageViewSet(BaseViewSet):
    queryset = DiffCoverage.objects.all()
    serializer_class = DiffCoverageSerializer

    def get(self, request, pk=None):
        pass

    @schema(GetCoverageReport)
    def list(self, request, *args, **kwargs):
        offset, limit, project_name = get_data(self.filtered, 'offset', 'limit', 'project_name')
        query = DiffCoverage.objects.filter(project_name__contains=project_name)
        data = DiffCoverageSerializer(query[offset: offset + limit], many=True).data
        return Response.success(data=data)


class JenkinsProjectCommitViewSet(BaseViewSet):
    """jenkins commit 发版记录"""
    queryset = JenkinsProjectCommit.objects.all()
    serializer_class = JenkinsProjectCommitSerializer

    def create(self, request, *args, **kwargs):
        '''提交一个jenkins发版服务的commit记录，为了覆盖率统计使用'''
        git_url = request.data.get('gitUrl')
        project_id = None
        git_project = GitProject.objects.filter(ssh_url=git_url)
        if len(git_project):
            project_id = git_project.first().id
        short_commit = request.data.get('short_commit')
        project_name = git_url.split('/')[-1][:-4]
        JenkinsProjectCommit.objects.create(short_commit=short_commit, project_name=project_name, project_id=project_id)
        return Response.success()


class JenkinsTaskViewSet(BaseViewSet):
    queryset = JenkinsBuildTask.objects.all()
    serializer_class = JenkinsTaskSerializer

    @login_or_permission_required('qa.edit')
    @schema(CreateJenkinsTask)
    def create(self, request, *args, **kwargs):
        '''触发一个构建任务'''
        project_git, compare_branch, pipeline_id = get_data(self.filtered, 'project_git', 'compare_branch', 'pipeline_id')
        # project_name = project_git.split('/')[-1][:-4]
        compare_branch = compare_branch or 'origin/master'
        if not project_git:
            return Response.bad_request(message='project_git 必填')
        try:
            pipeline = CoveragePipeline.objects.get(id=pipeline_id)
            end_commit = \
            JenkinsProjectCommit.objects.filter(project_id=pipeline.project_id).order_by('-id').values_list(
                'short_commit', 'project_id')[0]
        except IndexError:
            return Response.bad_request(message='该工程id没有对应的commit记录')
        except CoveragePipeline.DoesNotExist:
            return Response.server_error(message='该流水线不存在')
        task = JenkinsBuildTask.objects.create(project_git=project_git, end_commit=end_commit[0],
                                                compare_branch=compare_branch,
                                               username=self.username, pipeline_id=pipeline_id, pipeline_name=pipeline.name)
        # 触发coverage_job执行
        trigger_coverage_job(task_id=task.id, project_id=end_commit[1], open_id=self.open_id)
        return Response.success()

    @schema(GetJenkinsTaskList)
    def list(self, request, *args, **kwargs):
        '''查看某个流水线的覆盖率构建记录'''
        offset, limit, pipeline_name = get_data(self.filtered, 'offset', 'limit', 'pipeline_name')
        query = Q()
        if pipeline_name:
            query &= Q(pipeline_name__contains=pipeline_name)
        elif request.query_params.get('pipeline_id'):
            query &= Q(pipeline_id=request.query_params.get('pipeline_id'))
        queryset = JenkinsBuildTask.objects.filter(query).order_by('-id')
        data = JenkinsTaskSerializer(queryset[offset: offset + limit], many=True).data
        return Response.success(data={'data': data, 'total': len(queryset)})

    @login_or_permission_required('qa.edit')
    @list_route(methods=['post'], url_path='server/deploy')
    def trigger_server_jenkins_build(self, request):
        """触发服务端发版"""
        project_name = request.data.get('project_name')
        pipeline_id = request.data.get('pipeline_id')
        commit_id = request.data.get('commit_id')
        try:
            job_name = GitProject.objects.get(name=project_name).fat_job_name
        except GitProject.DoesNotExist:
            return Response.bad_request(message='该工程不存在')
        # 抛出任务异步执行jenkinsjob
        query = CoveragePipeline.objects.filter(id=pipeline_id)
        pipeline = query.first()
        query.update(deploy_status=JenkinsTaskStatus.PENDING.value, coverage_status=JenkinsTaskStatus.PENDING.value)
        mark = json.loads(pipeline.mark)
        project_git = json.loads(pipeline.coverage_params).get('project_git')
        # 如果流水线有覆盖率步骤，则先执行覆盖率再发版
        if pipeline.step2:
            try:
                end_commit = \
                    JenkinsProjectCommit.objects.filter(project_id=pipeline.project_id).order_by('-id').values_list(
                        'short_commit',
                        'project_id')[0]
                task = JenkinsBuildTask.objects.create(project_git=project_git, end_commit=end_commit[0],
                                                       compare_branch='origin/master',
                                                       username=self.username, pipeline_id=pipeline_id,
                                                       pipeline_name=pipeline.name)
                trigger_coverage_job(open_id=self.open_id, project_id=pipeline.project_id, task_id=task.id)
            except IndexError as e:
                mark['coverage'] = '该工程id没有对应的commit记录'
                coverage_status = JenkinsTaskStatus.FAIL.value
                query.update(deploy_status=JenkinsTaskStatus.PENDING.value,
                             coverage_status=coverage_status, mark=json.dumps(mark))
            except Exception as e:
                mark['coverage'] = e.args[0] if e.args else 'jenkins构建触发失败'
                coverage_status = JenkinsTaskStatus.FAIL.value
                query.update(deploy_status=JenkinsTaskStatus.PENDING.value,
                             coverage_status=coverage_status, mark=json.dumps(mark))
        # 添加一条发版log，等覆盖率执行后触发
        CoverageServerDeployHistory.objects.create(project_name=pipeline.project_name, username=self.username,
                                                   pipeline_id=pipeline.id, status=JenkinsTaskStatus.PENDING.value,
                                                   job_name=job_name, commit_id=commit_id)
        return Response.success()

    @list_route(methods=['post'], url_path='server/sonar')
    def trigger_server_sonar_build(self, request):
        pipeline_id = request.data.get('pipeline_id')
        commit_id = request.data.get('commit_id')
        try:
            pipeline = CoveragePipeline.objects.get(id=pipeline_id)

            build_params = {
                'end_commit': commit_id,
                'project_git': json.loads(pipeline.coverage_params).get('project_git'),
                'proj_lang': json.loads(pipeline.coverage_params).get('proj_lang'),
                'proj_key': json.loads(pipeline.coverage_params).get('proj_key'),
            }
            free_job = jenkinsTool.get_free_job(['test/sonar1', 'test/sonar2', 'test/sonar3'])
            build_number = jenkinsTool.get_build_number(free_job)
            result = jenkinsTool.build_job(free_job, params=build_params)
            pipeline.sonar_id = build_number
            pipeline.sonar_job = free_job
            pipeline.sonar_status = result
            pipeline.recover_times = 0
            pipeline.save()
        except CoveragePipeline.DoesNotExist:
            return Response.bad_request(message='该流水线不存在')
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=str(e))
        return Response.success()


class CoveragePiplineViewSet(BaseViewSet):
    queryset = CoveragePipeline.objects.filter().all()
    serializer_class = CoveragePiplineSerializer

    def get(self, request, pk=None):
        pass

    @schema(CreateCoveragePipline)
    def create(self, request, *args, **kwargs):
        '''创建一个流水线'''
        name, coverage_params, project_id, owner, notify_chat_ids, step1, step2 = get_data(self.filtered, 'name', 'coverage_params', 'project_id', 'owner', 'notify_chat_ids', 'step1', 'step2')
        pipline = CoveragePipeline.objects.filter((Q(project_id=project_id) | Q(name=name)))
        project = GitProject.objects.get(id=project_id)
        coverage_params['proj_lang'] = 'java' if step2 else ''
        if len(pipline):
            return Response.bad_request(message='该流水线名称/工程已创建过流水线')
        try:
            CoveragePipeline.objects.create(name=name, project_name=project.name, owner=owner,
                                            project_id=project_id, step1=step1,
                                            step2=step2,
                                            notify_chat_ids=','.join(notify_chat_ids),
                                            coverage_params=json.dumps(coverage_params))
        except Exception as e:
            raise e
        return Response.success()

    def partial_update(self, request, *args, **kwargs):
        """更新流水线"""
        id = kwargs.get('pk')
        data = request.data
        project = GitProject.objects.get(id=data['project_id'])
        data['project_name'] = project.name
        if 'coverage_params' in data.keys():
            data['coverage_params']['proj_lang'] = 'java' if data['step2'] else ''
            data['coverage_params'] = json.dumps(data['coverage_params'])
        if 'notify_chat_ids' in data.keys():
            data['notify_chat_ids'] = ','.join(data['notify_chat_ids'])
        CoveragePipeline.objects.filter(id=id).update(**data)
        return Response.success()

    @schema(OffsetLimitSiri)
    def list(self, request, *args, **kwargs):
        '''查看流水线列表'''
        offset, limit = get_data(self.filtered, 'offset', 'limit')
        name = request.query_params.get('name', '')
        businesses, terminals = request.query_params.getlist('business'), request.query_params.getlist('terminal')
        query = Q(name__contains=name)
        if businesses:
            query &= Q(business__in=businesses)
        if terminals:
            query &= Q(terminal__in=terminals)
        queryset = CoveragePipeline.objects.filter(query)
        data = CoveragePiplineSerializer(queryset[offset: offset+limit], many=True).data
        return Response.success(data={'data': data, 'total': len(queryset)})

    def destroy(self, request, *args, **kwargs):
        """删除流水线"""
        id = kwargs.get('pk')
        CoveragePipeline.objects.filter(id=id).delete()
        return Response.success()

    @detail_route(methods=['get'], url_path='deploy/console')
    def get_build_console(self, request, pk=None):
        """获取发版构建日志"""
        pipeline = CoveragePipeline.objects.get(id=pk)
        project = GitProject.objects.get(id=pipeline.project_id)
        build_id = request.query_params.get('build_id')
        if build_id:
            console_text = jenkinsTool.get_build_console_output(job_name=project.fat_job_name, build_id=build_id)
            is_building = jenkinsTool.get_is_building(job_name=project.fat_job_name, build_id=build_id)
        else:
            if not pipeline.deploy_id:
                return Response.bad_request(message="该流水线没有过服务端发版记录")
            console_text = jenkinsTool.get_build_console_output(job_name=project.fat_job_name, build_id=pipeline.deploy_id)
            is_building = jenkinsTool.get_is_building(job_name=project.fat_job_name, build_id=pipeline.deploy_id)
        return Response.success(data={'text': console_text, 'is_building': is_building})

    @detail_route(methods=['get'], url_path='coverage/console')
    def get_coverage_console(self, request, pk=None):
        """覆盖率收集构建日志"""
        jenkinsTask = JenkinsBuildTask.objects.filter(pipeline_id=pk).order_by('-id').first()
        console_text = jenkinsTool.get_build_console_output(jenkinsTask.coverage_job_name, jenkinsTask.build_number)
        is_building = jenkinsTool.get_is_building(job_name=jenkinsTask.coverage_job_name, build_id=jenkinsTask.build_number) or 'Error 404 Not Found' in console_text
        return Response.success(data={'text': console_text, 'is_building': is_building})


class ServerDeployHistoryViewSet(BaseViewSet):
    queryset = CoverageServerDeployHistory.objects.filter()
    serializer_class = DeployServerHistorySerializer

    @schema(OffsetLimitSiri)
    def list(self, request, *args, **kwargs):
        '''查看服务发版历史'''
        offset, limit = get_data(self.filtered, 'offset', 'limit')
        pipeline_id = request.query_params.get('pipeline_id')
        job_name = request.query_params.get('job_name')
        query = Q()
        if pipeline_id:
            query &= Q(pipeline_id=pipeline_id)
        if job_name:
            query &= Q(job_name__contains=job_name)
        queryset = CoverageServerDeployHistory.objects.filter(query).order_by('-id')
        data = DeployServerHistorySerializer(queryset[offset: offset + limit], many=True).data
        return Response.success(data={'data': data, 'total': len(queryset)})


class GitLabApiViewSet(BaseViewSet):
    queryset = GitProject.objects.filter()
    serializer_class = GitProjectSerializer

    @list_route(methods=['get'], url_path='projects')
    def get_projects(self, request):
        search = request.query_params.get('search')
        projects = gitTool.get_projects(search=search)
        return Response.success(data=projects)

    @list_route(methods=['get', 'post', 'delete'], url_path='project/(?P<pid>[^/]+)/branch')
    def project_branches(self, request, pid=None):
        if request.method.lower() == 'get':
            search = request.query_params.get('search')
            try:
                data = gitTool.get_project_branches(pid, search)
                return Response.success(data)
            except Exception as e:
                return Response.server_error(message=f"gitlab 调用出错:{e.args[0]}")
        elif request.method.lower() == 'post':
            branch_name = request.data.get('branch')
            ref = request.data.get('ref') or 'master'
            try:
                data = gitTool.create_branches(pid, branch_name=branch_name, ref=ref)
                return Response.success()
            except Exception as e:
                return Response.server_error(message=f"gitlab 调用出错:{e.args[0]}")
        else:
            branch_name = request.query_params.get('branch')
            try:
                data = gitTool.delete_branches(pid, branch_name)
                return Response.success()
            except Exception as e:
                return Response.server_error(message=f"gitlab 调用出错:{e.args[0]}")

    @schema(GitWebHookSchema)
    @list_route(methods=['post'], url_path='project/webhook')
    def git_ci_webhook(self, request):
        git_url, commit_id = get_data(self.filtered, 'ssh_url', 'commit_id')
        git_project = GitProject.objects.get(ssh_url=git_url)
        try:
            pipeline = CoveragePipeline.objects.get(project_id=git_project.id)
            build_params = {
                'end_commit': commit_id,
                'project_git': git_url,
                'proj_lang': json.loads(pipeline.coverage_params).get('proj_lang'),
                'proj_key': json.loads(pipeline.coverage_params).get('proj_key'),
            }
            free_job = jenkinsTool.get_free_job(['test/sonar1', 'test/sonar2', 'test/sonar3'])
            build_number = jenkinsTool.get_build_number(free_job)
            result = jenkinsTool.build_job(free_job, params=build_params)
            pipeline.sonar_id = build_number
            pipeline.sonar_job = free_job
            pipeline.sonar_status = result
            pipeline.recover_times = 0
            pipeline.save()
        except CoveragePipeline.DoesNotExist:
            return Response.bad_request(message='该流水线不存在')
        except ValueError as e:
            return Response.bad_request(message=e.args[0])
        except Exception as e:
            return Response.server_error(message=str(e))
        return Response.success()






