from django.contrib import admin

from django.contrib import admin
from zero.coverage.models import GitProject


class GitProjectAdmin(admin.ModelAdmin):
    fields = ('name', 'ssh_url', 'server_ip', 'server_port', 'fat_job_name')
    list_display = ('updated_at', 'id', 'name', 'ssh_url', 'server_ip', 'server_port', 'fat_job_name')
    list_filter = ['name']
    search_fields = ['name']


admin.site.register(GitProject, GitProjectAdmin)
