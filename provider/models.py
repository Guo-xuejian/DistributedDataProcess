# -*- coding:utf-8 -*-
from django.db import models


# 数据提供者
class Provider(models.Model):
    provider_ip = models.CharField(max_length=20, unique=True, verbose_name=u'IP')
    provider_name = models.CharField(max_length=50, verbose_name=u'备注名')
    upload_times = models.IntegerField(default=0, verbose_name=u'上传次数')
    recent_file_upload_time = models.DateTimeField(auto_now=True, verbose_name=u'上次上传时间')
    created_date = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    modify_date = models.DateTimeField(auto_now=True, verbose_name=u'修改日期')
    last_login = models.DateTimeField(auto_now=True, verbose_name=u'上次登录')

    def __str__(self):
        return self.provider_ip

    class Meta:
        verbose_name = u'提供者'
        verbose_name_plural = verbose_name
        managed = True
        db_table = u'provider'


# 上传文件
class File(models.Model):
    # TASK_STATUS = ((1, u'未生成'), (2, u'已生成'), (3, u'分配中'), (4, u'结果生成'), (5, u'已下载'))
    # FILE_TYPE = ((1, u'函数'), (2, u'数据'),)
    file_name = models.CharField(max_length=120, verbose_name=u'文件名')
    provider_name = models.CharField(max_length=20, verbose_name=u'提供者')
    created_date = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    task_status = models.CharField(max_length=20, verbose_name=u'任务状态')
    file_type = models.CharField(max_length=20, verbose_name=u'文件类型')

    def __str__(self):
        return self.file_name

    class Meta:
        verbose_name = u'上传文件'
        verbose_name_plural = verbose_name
        managed = True
        db_table = u'file'
