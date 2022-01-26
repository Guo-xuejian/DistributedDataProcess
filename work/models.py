import datetime

from django.db import models
from provider.models import *


# 注册Ip
class User(models.Model):
    # 基础信息
    IP = models.GenericIPAddressField(unique=True)
    created_date = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    status = models.BooleanField(default=True, verbose_name=u'空闲')
    upload_times = models.IntegerField(default=0, verbose_name=u'申请总次数')
    upload_times_today = models.IntegerField(default=0, verbose_name=u'今日申请次数')
    user_capability_level = models.IntegerField(default=3, verbose_name='用户端能力等级')
    cloud_update = models.BooleanField(default=False, verbose_name=u'同步至云网站')

    def __str__(self):
        return self.IP

    class Meta:
        verbose_name = u'用户'
        verbose_name_plural = verbose_name
        managed = True
        db_table = u'user'


# 系统所使用的函数
class Function(models.Model):
    func_name = models.CharField(max_length=50, verbose_name=u'函数名')
    provider_name = models.CharField(max_length=50, verbose_name=u'提供者')
    single_data_set_num = models.IntegerField(default=8000, verbose_name=u'单任务数据量')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    func_capability_level = models.IntegerField(default=3, verbose_name=u'函数要求客户端能力')
    """
        status用来区别正在工作的函数，也即是目前分发任务所使用的函数，这个status在一开始就是False，需要用户在使用的时候指定今天的任务所需要的函数
        如果没有就通过该页面的上传功能上传到相应目录
    """
    status = models.BooleanField(default=False, verbose_name=u'今日工作函数')
    invoke_times = models.IntegerField(default=0, verbose_name=u'当前被调用次数')

    def __str__(self):
        return self.func_name

    class Meta:
        verbose_name = u'函数'
        verbose_name_plural = verbose_name
        managed = True
        db_table = u'function'


# 设定任务
class Task(models.Model):
    provider_name = models.ForeignKey(Provider, on_delete=models.CASCADE, verbose_name=u'提供者')
    task_name = models.CharField(default='任务', max_length=50, unique=True, verbose_name=u'任务名')
    status = models.BooleanField(default=False, verbose_name=u'分配状态')
    split_status = models.BooleanField(default=False, verbose_name=u'是否分组')
    num = models.IntegerField(default=8000, verbose_name=u'单任务数据量')
    task_create_date = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    task_over = models.BooleanField(default=False, verbose_name=u'任务完结', )
    assignment_over = models.BooleanField(default=False, verbose_name=u'分配完毕', )
    func_name = models.ForeignKey(Function, on_delete=models.CASCADE, verbose_name=u'函数')
    task_capability_level = models.IntegerField(default=3, verbose_name=u'任务要求客户端能力')
    cloud_update = models.BooleanField(default=False, verbose_name=u'同步至云网站')

    def __str__(self):
        return self.task_name

    class Meta:
        verbose_name = u'任务'
        verbose_name_plural = verbose_name
        managed = True
        db_table = u'task'


# 数据分组--一堆的数据集，数量取决于文件大小和该任务所设定的单任务数据量num
class Original(models.Model):
    data_set = models.CharField(max_length=50, verbose_name=u'数据集')
    status = models.BooleanField(default=False, verbose_name=u'分配状态')
    created_date = models.DateTimeField(auto_now_add=True, verbose_name=u'创建时间')
    upload = models.BooleanField(default=False, verbose_name=u'是否上传')
    task_belong = models.ForeignKey(Task, on_delete=models.CASCADE, verbose_name=u'所属任务')
    assignment_over = models.BooleanField(default=False, verbose_name=u'任务完结',
                                          help_text='任务完结后监控界面不在接受该任务所有数据')
    func_capability_level = models.IntegerField(default=3, verbose_name=u'任务要求客户端能力')

    def __str__(self):
        return self.data_set

    class Meta:
        verbose_name = u'数据'
        verbose_name_plural = verbose_name
        managed = True
        db_table = u'original'


# 数据分配情况
class Assignment(models.Model):
    name = models.CharField(max_length=50, default='任务', verbose_name=u'记录IP')
    IP = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=u'IP地址')
    task_belong = models.ForeignKey(Task, on_delete=models.CASCADE, verbose_name=u'所属任务')
    data_set = models.ForeignKey(Original, on_delete=models.CASCADE, unique=True, verbose_name=u'分配数据集')
    created_time = models.DateTimeField(auto_now=True, verbose_name=u'任务创建时间')
    upload_time = models.DateTimeField(default=datetime.datetime.now() + datetime.timedelta(seconds=30),
                                       verbose_name=u'预定数据上交时间')
    upload = models.BooleanField(default=False, verbose_name=u'是否上传')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = u'分配'
        verbose_name_plural = verbose_name
        managed = True
        db_table = u'assignment'


# IP上传数据
class DataUpload(models.Model):
    IP = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=u'上传IP')
    task_belong = models.ForeignKey(Task, on_delete=models.CASCADE, verbose_name=u'对应任务')
    data_set = models.ForeignKey(Original, on_delete=models.CASCADE, unique=True, verbose_name=u'对应数据集')
    upload_data = models.TextField(max_length=9999999999, blank=True, verbose_name=u'上传数据内容')
    upload_date = models.DateTimeField(auto_now=True, verbose_name=u'上次上传时间')
    upload_times = models.IntegerField(default=0, blank=True, verbose_name=u'上传次数')

    # def __str__(self):
    #     return self.task_belong

    class Meta:
        verbose_name = u'上传'
        verbose_name_plural = verbose_name
        managed = True
        db_table = u'data_upload'
