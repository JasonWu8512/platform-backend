# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
import mongoengine as mongo
from zero.utils.format import second_2_days, get_point_by_buglevel
from zero.jira.commands import JiraIssueStatus
from zero.libs.baseModel import BaseDocument, BaseModel
from zero.organization.models import AceAccount
import shortuuid

class SprintEstimate(BaseDocument):
    '''迭代的工时报表'''
    id = mongo.StringField(primary_key=True, default=shortuuid.uuid)
    sprint_id = mongo.StringField()
    terminal = mongo.StringField()
    people_count = mongo.IntField(required=False)
    people = mongo.StringField()
    team_people = mongo.DecimalField(required=False, default=0, force_string=True, precision=1)
    real_people = mongo.DecimalField(required=False, default=0, force_string=True, precision=1)
    jira_people_count = mongo.IntField(required=False)
    dev_qa_days = mongo.DecimalField(required=False, default=0, force_string=True, precision=3)
    target_days = mongo.DecimalField(required=False, default=0, force_string=True, precision=3)
    business_story_estimate = mongo.IntField()
    business_story_count = mongo.IntField()
    tech_story_estimate = mongo.IntField()
    tech_story_count = mongo.IntField()
    change_story_estimate = mongo.IntField()
    change_story_count = mongo.IntField()
    regression_estimate = mongo.IntField()
    resource_depletion_estimate = mongo.IntField()
    bugs = mongo.IntField()
    sprint_time = mongo.StringField()
    sprint_days = mongo.IntField()
    saturation = mongo.StringField(required=False, default='0')
    target_days_diff = mongo.DecimalField(required=False, default=0, force_string=True, precision=3)
    mark = mongo.StringField(required=False, null=True)
    edited = mongo.BooleanField()
    sum_story_count = mongo.IntField()
    terminal_id = mongo.IntField()
    delay_tasks = mongo.ListField()
    delay_story = mongo.ListField()

    meta = {'collection': 'sprint_estimate',
            "indexes": ["sprint_id", "terminal", "edited"]}


class DepartmentEstimate(BaseDocument):
    """技术部各部门每月的工时报表"""
    id = mongo.StringField(primary_key=True, default=shortuuid.uuid)
    depart_name = mongo.StringField()
    month = mongo.StringField()
    leader = mongo.StringField()
    people_count = mongo.IntField()
    work_days = mongo.IntField()
    total_working_days = mongo.IntField()
    pre_department_days = mongo.FloatField()
    current_department_days = mongo.FloatField()
    next_department_days = mongo.FloatField()
    target_days_diff = mongo.IntField()
    productivity = mongo.FloatField()
    edited = mongo.BooleanField()
    mark = mongo.StringField(required=False, null=True)

    meta = {'collection': 'department_estimate',
            "indexes": ["depart_name", "month", "edited"]}


class AppUser(models.Model):
    id = models.DecimalField(db_column='ID', primary_key=True, max_digits=18, decimal_places=0)  # Field name made lowercase.
    user_key = models.CharField(unique=True, max_length=255, blank=True, null=True)
    lower_user_name = models.CharField(unique=True, max_length=255, blank=True, null=True)
    objects = models.Manager()

    class Meta:
        app_label = "zero.jira"
        db_table = 'app_user'


class CwdUser(models.Model):
    id = models.DecimalField(db_column='ID', primary_key=True, max_digits=18,
                             decimal_places=0)  # Field name made lowercase.
    directory_id = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    lower_user_name = models.CharField(max_length=255, blank=True, null=True)
    active = models.DecimalField(max_digits=9, decimal_places=0, blank=True, null=True)
    created_date = models.DateTimeField(blank=True, null=True)
    updated_date = models.DateTimeField(blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    lower_first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    lower_last_name = models.CharField(max_length=255, blank=True, null=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    lower_display_name = models.CharField(max_length=255, blank=True, null=True)
    email_address = models.CharField(max_length=255, blank=True, null=True)
    lower_email_address = models.CharField(max_length=255, blank=True, null=True)
    credential = models.CharField(db_column='CREDENTIAL', max_length=255, blank=True,
                                  null=True)  # Field name made lowercase.
    deleted_externally = models.DecimalField(max_digits=9, decimal_places=0, blank=True, null=True)
    external_id = models.CharField(db_column='EXTERNAL_ID', max_length=255, blank=True,
                                   null=True)  # Field name made lowercase.
    objects = models.Manager()

    class Meta:
        app_label = "zero.jira"
        db_table = 'cwd_user'
        unique_together = (('lower_user_name', 'directory_id'),)

    @property
    def ace_account_id(self):
        account = AceAccount.objects.filter(email=str(self.email_address).lower())
        if len(account):
            return account.first().id

    @property
    def ace_open_id(self):
        account = AceAccount.objects.filter(email=str(self.email_address).lower())
        if len(account):
            return account.first().lark_open_id


class Ao60Db71Rapidview(models.Model):
    card_color_strategy = models.CharField(db_column='CARD_COLOR_STRATEGY', max_length=255, blank=True,
                                           null=True)  # Field name made lowercase.
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    kan_plan_enabled = models.IntegerField(db_column='KAN_PLAN_ENABLED', blank=True,
                                           null=True)  # Field name made lowercase.
    name = models.CharField(db_column='NAME', max_length=255)  # Field name made lowercase.
    old_done_issues_cutoff = models.CharField(db_column='OLD_DONE_ISSUES_CUTOFF', max_length=255, blank=True,
                                              null=True)  # Field name made lowercase.
    owner_user_name = models.CharField(db_column='OWNER_USER_NAME', max_length=255)  # Field name made lowercase.
    saved_filter_id = models.BigIntegerField(db_column='SAVED_FILTER_ID')  # Field name made lowercase.
    show_days_in_column = models.IntegerField(db_column='SHOW_DAYS_IN_COLUMN', blank=True,
                                              null=True)  # Field name made lowercase.
    show_epic_as_panel = models.IntegerField(db_column='SHOW_EPIC_AS_PANEL', blank=True,
                                             null=True)  # Field name made lowercase.
    sprints_enabled = models.IntegerField(db_column='SPRINTS_ENABLED', blank=True,
                                          null=True)  # Field name made lowercase.
    swimlane_strategy = models.CharField(db_column='SWIMLANE_STRATEGY', max_length=255, blank=True,
                                         null=True)  # Field name made lowercase.

    objects = models.Manager()

    class Meta:
        app_label = "zero.jira"
        db_table = 'AO_60DB71_RAPIDVIEW'


class Ao60Db71Sprint(models.Model):
    closed = models.IntegerField(db_column='CLOSED')  # Field name made lowercase.
    complete_date = models.BigIntegerField(db_column='COMPLETE_DATE', blank=True,
                                           null=True)  # Field name made lowercase.
    end_date = models.BigIntegerField(db_column='END_DATE', blank=True, null=True)  # Field name made lowercase.
    goal = models.TextField(db_column='GOAL', blank=True, null=True)  # Field name made lowercase.
    id = models.BigAutoField(db_column='ID', primary_key=True)  # Field name made lowercase.
    name = models.CharField(db_column='NAME', max_length=255)  # Field name made lowercase.
    rapid_view_id = models.BigIntegerField(db_column='RAPID_VIEW_ID', blank=True,
                                           null=True)  # Field name made lowercase.
    sequence = models.BigIntegerField(db_column='SEQUENCE', blank=True, null=True)  # Field name made lowercase.
    started = models.IntegerField(db_column='STARTED', blank=True, null=True)  # Field name made lowercase.
    start_date = models.BigIntegerField(db_column='START_DATE', blank=True, null=True)  # Field name made lowercase.

    objects = models.Manager()

    class Meta:
        app_label = "zero.jira"
        db_table = 'AO_60DB71_SPRINT'


class Projectversion(models.Model):
    id = models.DecimalField(db_column='ID', primary_key=True, max_digits=18,
                             decimal_places=0)  # Field name made lowercase.
    project = models.DecimalField(db_column='PROJECT', max_digits=18, decimal_places=0, blank=True,
                                  null=True)  # Field name made lowercase.
    vname = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(db_column='DESCRIPTION', blank=True, null=True)  # Field name made lowercase.
    sequence = models.DecimalField(db_column='SEQUENCE', max_digits=18, decimal_places=0, blank=True,
                                   null=True)  # Field name made lowercase.
    released = models.CharField(db_column='RELEASED', max_length=10, blank=True,
                                null=True)  # Field name made lowercase.
    archived = models.CharField(db_column='ARCHIVED', max_length=10, blank=True,
                                null=True)  # Field name made lowercase.
    url = models.CharField(db_column='URL', max_length=255, blank=True, null=True)  # Field name made lowercase.
    startdate = models.DateTimeField(db_column='STARTDATE', blank=True, null=True)  # Field name made lowercase.
    releasedate = models.DateTimeField(db_column='RELEASEDATE', blank=True, null=True)  # Field name made lowercase.

    objects = models.Manager()

    class Meta:
        app_label = "zero.jira"
        db_table = 'projectversion'


class Project(models.Model):
    id = models.DecimalField(db_column='ID', primary_key=True, max_digits=18,
                             decimal_places=0)  # Field name made lowercase.
    pname = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(db_column='URL', max_length=255, blank=True, null=True)  # Field name made lowercase.
    lead = models.CharField(db_column='LEAD', max_length=255, blank=True, null=True)  # Field name made lowercase.
    description = models.TextField(db_column='DESCRIPTION', blank=True, null=True)  # Field name made lowercase.
    pkey = models.CharField(unique=True, max_length=255, blank=True, null=True)
    pcounter = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    assigneetype = models.DecimalField(db_column='ASSIGNEETYPE', max_digits=18, decimal_places=0, blank=True,
                                       null=True)  # Field name made lowercase.
    avatar = models.DecimalField(db_column='AVATAR', max_digits=18, decimal_places=0, blank=True,
                                 null=True)  # Field name made lowercase.
    originalkey = models.CharField(db_column='ORIGINALKEY', max_length=255, blank=True,
                                   null=True)  # Field name made lowercase.
    projecttype = models.CharField(db_column='PROJECTTYPE', max_length=255, blank=True,
                                   null=True)  # Field name made lowercase.

    objects = models.Manager()

    class Meta:
        app_label = "zero.jira"
        db_table = 'project'


class JiraissueOrigin(models.Model):
    id = models.DecimalField(db_column='ID', primary_key=True, max_digits=18, decimal_places=0)  # Field name made lowercase.
    pkey = models.CharField(max_length=255, blank=True, null=True)
    issuenum = models.DecimalField(max_digits=18, decimal_places=0, blank=True, null=True)
    project = models.DecimalField(db_column='PROJECT', max_digits=18, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    reporter = models.CharField(db_column='REPORTER', max_length=255, blank=True, null=True)  # Field name made lowercase.
    assignee = models.CharField(db_column='ASSIGNEE', max_length=255, blank=True, null=True)  # Field name made lowercase.
    creator = models.CharField(db_column='CREATOR', max_length=255, blank=True, null=True)  # Field name made lowercase.
    issuetype = models.CharField(max_length=255, blank=True, null=True)
    summary = models.CharField(db_column='SUMMARY', max_length=255, blank=True, null=True)  # Field name made lowercase.
    description = models.TextField(db_column='DESCRIPTION', blank=True, null=True)  # Field name made lowercase.
    environment = models.TextField(db_column='ENVIRONMENT', blank=True, null=True)  # Field name made lowercase.
    priority = models.CharField(db_column='PRIORITY', max_length=255, blank=True, null=True)  # Field name made lowercase.
    resolution = models.CharField(db_column='RESOLUTION', max_length=255, blank=True, null=True)  # Field name made lowercase.
    issuestatus = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(db_column='CREATED', blank=True, null=True)  # Field name made lowercase.
    updated = models.DateTimeField(db_column='UPDATED', blank=True, null=True)  # Field name made lowercase.
    duedate = models.DateTimeField(db_column='DUEDATE', blank=True, null=True)  # Field name made lowercase.
    resolutiondate = models.DateTimeField(db_column='RESOLUTIONDATE', blank=True, null=True)  # Field name made lowercase.
    votes = models.DecimalField(db_column='VOTES', max_digits=18, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    watches = models.DecimalField(db_column='WATCHES', max_digits=18, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    timeoriginalestimate = models.DecimalField(db_column='TIMEORIGINALESTIMATE', max_digits=18, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    timeestimate = models.DecimalField(db_column='TIMEESTIMATE', max_digits=18, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    timespent = models.DecimalField(db_column='TIMESPENT', max_digits=18, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    workflow_id = models.DecimalField(db_column='WORKFLOW_ID', max_digits=18, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    security = models.DecimalField(db_column='SECURITY', max_digits=18, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    fixfor = models.DecimalField(db_column='FIXFOR', max_digits=18, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    component = models.DecimalField(db_column='COMPONENT', max_digits=18, decimal_places=0, blank=True, null=True)  # Field name made lowercase.
    archived = models.CharField(db_column='ARCHIVED', max_length=1, blank=True, null=True)  # Field name made lowercase.
    archivedby = models.CharField(db_column='ARCHIVEDBY', max_length=255, blank=True, null=True)  # Field name made lowercase.
    archiveddate = models.DateTimeField(db_column='ARCHIVEDDATE', blank=True, null=True)  # Field name made lowercase.

    objects = models.Manager()

    class Meta:
        app_label = "zero.jira"
        db_table = 'jiraissue'


class JiraProject(BaseModel):
    id = models.CharField(primary_key=True, max_length=15)
    key = models.CharField(max_length=255, blank=True, null=False)
    name = models.CharField(max_length=255, blank=True, null=False)
    lead = models.CharField(max_length=32, blank=True, null=True)
    description = models.TextField(blank=True, null=True)  # Field name made lowercase.

    class Meta:
        db_table = 'jira_project'

    @property
    def sprints(self):
        return JiraSprint.objects.filter(proj_id=self.id).order_by('-start_date').all()


class JiraBoards(BaseModel):
    id = models.CharField(db_column='ID', primary_key=True, max_length=15)
    proj_id = models.IntegerField(blank=True, null=False)
    proj_key = models.CharField(max_length=255, blank=True, null=False)
    name = models.CharField(max_length=255, blank=True, null=False)

    class Meta:
        db_table = 'jira_board'


class JiraSprint(BaseModel):
    id = models.CharField(primary_key=True, max_length=15, verbose_name='sprintid', help_text='sprintid')
    name = models.CharField(max_length=255, verbose_name='迭代名称', help_text='迭代名称')  # Field name made lowercase.
    board_id = models.IntegerField(verbose_name='关联看板id', help_text='关联看板id')
    proj_id = models.CharField(max_length=255, blank=True, null=False, verbose_name='关联的项目id', help_text='关联的项目id')
    proj_key = models.CharField(max_length=255, blank=True, null=False, verbose_name='关联的项目前缀', help_text='关联的项目前缀')
    goal = models.TextField(blank=True, null=True, verbose_name='目标', help_text='目标')
    end_date = models.DateField(blank=True, null=True, verbose_name='结束时间',
                                help_text='结束时间')  # Field name made lowercase.
    closed = models.IntegerField(verbose_name='关闭标识', help_text='关闭标识')  # Field name made lowercase.
    complete_date = models.DateField(blank=True, null=True, verbose_name='完成时间', help_text='完成时间')
    started = models.IntegerField(verbose_name='开始标识', help_text='开始标识')
    start_date = models.DateField(blank=True, null=True, verbose_name='开始时间', help_text='开始时间')

    class Meta:
        db_table = 'jira_sprint'


class JiraFixVersions(BaseModel):
    id = models.CharField(db_column='ID', primary_key=True, max_length=15, verbose_name="版本id", help_text='版本id')
    name = models.CharField(max_length=255, verbose_name='版本名称', help_text='版本名称')
    proj_id = models.CharField(max_length=255, blank=True, null=False, verbose_name='关联的项目id', help_text='关联的项目id')
    proj_key = models.CharField(max_length=255, blank=True, null=False, verbose_name='关联的项目前缀', help_text='关联的项目前缀')
    sprint_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='关联的迭代id', help_text='关联的迭代id')
    start_date = models.DateTimeField(blank=True, null=True, verbose_name='开始时间', help_text='开始时间')
    release_date = models.DateTimeField(blank=True, null=True, verbose_name='发版时间', help_text='发版时间')
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'jira_fixversion'


class JiraIssue(BaseModel):
    id = models.CharField(db_column='ID', primary_key=True, max_length=255, verbose_name='issueid', help_text='issueid')
    key = models.CharField(max_length=255, blank=True, verbose_name='issue编号', help_text='issue编号')
    type = models.CharField(max_length=255, blank=True, verbose_name='issue类型', help_text='issue类型')
    proj_id = models.IntegerField(blank=True, null=False, verbose_name='关联的项目id', help_text='关联的项目id')
    proj_key = models.CharField(max_length=255, blank=True, verbose_name='关联的项目前缀', help_text='关联的项目前缀')
    resolution = models.CharField(max_length=255, blank=True, verbose_name='解决结果', help_text='解决结果')
    resolution_date = models.DateTimeField(blank=True, null=True, verbose_name='解决日期', help_text='解决日期')
    priority = models.CharField(max_length=10, blank=True, null=True, verbose_name='优先级', help_text='优先级')
    assignee = models.CharField(max_length=255, blank=True, null=True, verbose_name='指派人', help_text='指派人')
    created = models.CharField(max_length=255, blank=True, verbose_name='创建时间', help_text='创建时间')
    updated = models.DateTimeField(blank=True, null=False, verbose_name='更新时间', help_text='更新时间')
    status = models.CharField(max_length=255, blank=True, null=True, verbose_name='issue状态', help_text='issue状态')
    summary = models.CharField(max_length=255, blank=True, null=True, verbose_name='issue标题', help_text='issue标题')
    description = models.TextField(blank=True, null=True, verbose_name='issue描述', help_text='issue描述')
    creator = models.CharField(max_length=255, blank=True, verbose_name='issue创建者', help_text='issue创建者')
    original_time_estimate = models.IntegerField(blank=True, null=True, verbose_name='估时', help_text='估时')
    bugOwner = models.CharField(max_length=255, blank=True, null=True, verbose_name='bugOwner', help_text='bugOwner')
    env = models.CharField(max_length=255, blank=True, null=True, verbose_name='测试环境', help_text='测试环境')
    platform = models.CharField(max_length=255, blank=True, null=True, verbose_name='issue所属端/平台',
                                help_text='issue所属端/平台')
    bug_level = models.CharField(max_length=255, blank=True, null=True, verbose_name='bug等级-线上/线下',
                                 help_text='bug等级-线上/线下')
    sub_bug_level = models.CharField(max_length=255, blank=True, null=True, verbose_name='bug子等级-S0/1/2/3',
                                     help_text='bug子等级-S0/1/2/3')
    fix_version = models.CharField(max_length=255, blank=True, null=True, verbose_name='修复的版本', help_text='修复的版本')
    target_start = models.DateTimeField(null=True, verbose_name='目标开始时间', help_text='目标开始时间')
    target_end = models.DateTimeField(null=True, verbose_name='目标结束时间', help_text='目标结束时间')
    issue_links = models.TextField(max_length=65535, null=True, verbose_name="关联issue", help_text="关联issue")
    parent_key = models.CharField(max_length=255, blank=True, null=True, verbose_name='修复的版本', help_text='修复的版本')
    sprint_id = models.CharField(max_length=255, null=True, verbose_name="所属sprint", help_text="所属sprint")
    epic_key = models.CharField(max_length=255, null=True, verbose_name="所属epic", help_text="所属epic")
    fix_time = models.IntegerField(blank=True, null=True, verbose_name="解决时长(s)", help_text="解决时长(s)")
    close_time = models.IntegerField(blank=True, null=True, verbose_name="关闭时长(s)", help_text="关闭时长(s)")
    reopen_count = models.IntegerField(blank=True, null=True, verbose_name='reopen次数', help_text="reopen次数")

    class Meta:
        db_table = 'jira_issue'

    @property
    def day(self):
        return second_2_days(self.original_time_estimate)

    @property
    def point(self):
        return get_point_by_buglevel(self.sub_bug_level)

    @property
    def status_chinese(self):
        return JiraIssueStatus.get_value(self.status)


class JiraBusinessCycle(BaseModel):
    project_id = models.CharField(max_length=20, null=False, verbose_name='项目id')
    project_name = models.CharField(max_length=255, null=False, verbose_name='项目名称')
    delivery_cycle = models.FloatField(null=True, verbose_name='交付周期')
    develop_cycle = models.FloatField(null=True, verbose_name='开发交付周期')
    start_date = models.DateField(null=False, verbose_name='开始时间')
    end_date = models.DateField(null=False, verbose_name='截止时间')

    class Meta:
        unique_together = (("project_id", "end_date"),)
        db_table = 'jira_business_cycle'
