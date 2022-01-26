from django.contrib import admin
from .models import Site


class SiteAdmin(admin.ModelAdmin):
    list_display = ['site_ip_domain_name', 'url']


admin.site.register(Site, SiteAdmin)
