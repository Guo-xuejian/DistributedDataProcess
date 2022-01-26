from django.db import models


UPDATE_CHOICE = ((u'本科', u'本科'), (u'硕士', u'硕士'), (u'博士', u'博士'))


class Site(models.Model):
    site_ip_domain_name = models.CharField(max_length=50, verbose_name=u'接口')
    url = models.URLField(verbose_name=u'网址')

    def __str__(self):
        return self.site_ip_domain_name

    class Meta:
        verbose_name = u'云内容更新接口'
        verbose_name_plural = verbose_name
        managed = True
        db_table = u'site'

