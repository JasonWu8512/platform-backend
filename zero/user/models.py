from django.db import models
from zero.jira.models import BaseModel
from django.contrib.auth.models import User, Group


class UserAuthGroup(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    class Meta:
        db_table = "auth_user_groups"


class UserSsoAccessToken(BaseModel):
    uid = models.CharField(primary_key=True, max_length=60, null=False, blank=False, verbose_name='sso user uid', help_text='sso user uid')
    access_token = models.CharField(max_length=60, null=False, blank=False, verbose_name='sso access_token', help_text='sso access_token')
    expire_time = models.IntegerField(verbose_name='过期时间', help_text='过期时间')

    class Meta:
        db_table = 'sso_access_token'