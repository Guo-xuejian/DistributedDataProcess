from django.contrib import admin
from .models import *

# Register your models here.


class ProviderAdmin(admin.ModelAdmin):
    list_display = ('provider_ip', 'provider_name', 'upload_times', 'recent_file_upload_time', )
    list_filter = ('provider_ip', 'provider_name', 'upload_times', )


class FileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'file_type', 'provider_name', 'created_date', )
    list_filter = ('provider_name', 'file_type', 'file_type', )


admin.site.register(Provider, ProviderAdmin)
admin.site.register(File, FileAdmin)
