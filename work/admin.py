from django.contrib import admin
from work.models import *
from work.views import *

"""
    每一个class的格式基本固定，参照下面就可以知道
    其中的一些方法和属性包括
        list_display        元组中字段来自models.py
                            选定在admin后台中展示的字段信息，比如点击后台左侧导航栏中”任务“后看到的各个字段，如果没有这个方法，那么就只会展示主键
        list_filter         元组中字段来自models.py
                            也就是选择器，选定了哪些字段用于从若干记录检索到需要的那一条数据
        list_editable       元组中字段来自models.py
                            也就是可编辑，和models.py中的editable不一样，这里的是指可以直接在点击”任务“之后的一级页面上对记录做修改，在”任务“中有三个可以直接修改，单任务数据量，函数，分配状态
        exclude             元组中字段来自models.py
                            选定了哪些字段是不展示在后台的的，其实也就是保证那些数据不能被直接更改，比如一个用户的创建时间，我们自然不希望被更改
        actions             列表中函数来自views.py
                            指定了在增加和删除按钮旁会有哪些自定义的按钮，”任务“一级页面中除了增加删除和保存，其余的都是我在views.py中写好的函数然后加入actions这个方法的列表中的
                            每一个按钮在点击时都是至少需要选定一条记录的，直接点击会提示
        
        change_list_template        这个指定了一个html文件，这个html位于venv1\Lib\site-packages\django\contrib\admin\templates\admin\中，其实就是完全自定义的一些内容，
                                    simpleui也不是完全个性化的，通过在前面的路径下创建html文件，继承统一的内容（看下那个文件就知道了）,在admin.py中对应的class中设定这个属性
                                    比如”任务“一级页面中的上传文件的按钮，为什么不放在增加删除那一列呢，是因为在那个地方的所有按钮在点击时都需要选择一条记录才可以正常点击，其余的倒是无所谓，
                                    上传需要上传按钮和确定按钮，想想算了，还不如就放在上面，如果后面要加上一些比较花哨的动态图表，也是通过这样的方法
"""


# 注册用户类
class UserAdmin(admin.ModelAdmin):
    exclude = ('created_date', )
    list_display = ('IP', 'user_capability_level', 'upload_times', 'upload_times_today', 'created_date', 'status',)
    list_filter = ('IP', 'user_capability_level', 'upload_times', 'upload_times_today', 'created_date', 'status',)
    list_editable = ('status', )

    def save_model(self, request, obj, form, change):
        obj.creator = request.user
        super().save_model(request, obj, form, change)


# 数据分组情况类，也就是Task中点击了数据分组之后产生的数据集
class OriginalAdmin(admin.ModelAdmin):
    list_display = ('data_set', 'task_belong', 'func_capability_level', 'status', 'upload', 'assignment_over', 'created_date', )
    list_filter = ('data_set', 'task_belong', 'func_capability_level', 'status', 'upload', 'assignment_over', 'created_date', )
    list_editable = ('status', )

    # change_list_template = 'admin/original_changelist.html'


# 任务类
class TaskAdmin(admin.ModelAdmin):
    exclude = ('task_create_date', )
    list_display = ('task_name', 'provider_name', 'task_capability_level', 'num', 'func_name', 'split_status', 'status', 'assignment_over', 'task_over', 'task_create_date', 'cloud_update', )
    list_filter = ('task_name', 'provider_name', 'task_capability_level', 'num', 'func_name', 'split_status', 'status', 'assignment_over', 'task_over', 'task_create_date', 'cloud_update', )
    list_editable = ('status', 'task_capability_level', 'num', 'func_name', )

    # 依次是数据分组、文件聚合、下载预测、创建日期文件夹（data/这个目录）、文件转任务
    actions = [file_aggregate, predict_download, ]
    # 修改按钮的样式，来自于simpleui，
    """
        action.confirm = ''     点击按钮后的提示内容
        action.style = ''       参照下面，基本的属性都能用
        action.icon = ''        显示在文字部分之前的小图标，主要是为了美化
    """
    # shuffle_teams.confirm = '请确认目前的选择!'
    # shuffle_teams.style = 'color:white;background-color:black;'
    # shuffle_teams.icon = 'fas fa-spinner'

    # change_list_template = 'admin/task_changelist.html'

    def save_model(self, request, obj, form, change):
        obj.creator = request.user
        super().save_model(request, obj, form, change)


# 数据分配情况（IP数据集申请情况）
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'task_belong', 'data_set', 'upload', 'created_time', 'upload_time')
    list_filter = ('name', 'task_belong', 'data_set', 'upload', 'created_time', 'upload_time')


# 文件上传类
class DataUploadAdmin(admin.ModelAdmin):
    list_display = ('IP', 'task_belong', 'data_set', 'upload_date', 'upload_times', )
    list_filter = ('IP', 'task_belong', 'data_set', 'upload_date', 'upload_times', )


# 函数类
class FunctionAdmin(admin.ModelAdmin):
    list_display = ('func_name', 'provider_name', 'single_data_set_num', 'status', 'func_capability_level', 'created_time', 'invoke_times',)
    list_filter = ('func_name', 'provider_name', 'single_data_set_num', 'status', 'func_capability_level', 'created_time', 'invoke_times',)
    list_editable = ('single_data_set_num', 'func_capability_level', )

    # change_list_template = 'admin/function_changelist.html'

    # actions = [zip_choose_functions, functions_to_true, functions_to_false, file_to_function, ]
    # actions = [file_to_function, ]
    # file_to_function.confirm = '确认当前选择'


# 注册，不然即使写了内容也不会在admin后台展示
admin.site.register(User, UserAdmin)
admin.site.register(Original, OriginalAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Assignment, AssignmentAdmin)
admin.site.register(DataUpload, DataUploadAdmin)
admin.site.register(Function, FunctionAdmin)

# 修改网页title和站点header。
admin.site.site_title = "大数据分机处理后台"
admin.site.site_header = "大数据分机处理后台"
