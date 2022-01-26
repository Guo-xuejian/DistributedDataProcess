import os
import json
import time
import numpy
import pandas
import shutil
import requests
from django.contrib import messages
from django.core import serializers
from django.db import IntegrityError
from django.db.models import Q
from django.http.response import JsonResponse, FileResponse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from threading import Timer

import pandas as pd
import pickle
import zipfile
import pathlib

from datetime import datetime
from distribute_project.settings import BASE_DIR
from provider import models as provider_models
from django.utils.encoding import escape_uri_path
from .forms import *
from . import models
from siteinfo.models import Site as Site_model

TASK_STATUS = ['未生成', '已生成', '分配中', '结果生成', '已下载']
FILE_TYPE = ['函数', '数据']


"""
    path = pathlib.Path('path/to/file')
    # 判断路径是否存在
    path.exists()
    # 判断是否为文件
    path.is_file()
    # 判断是否为目录
    path.is_dir()
"""


# 已经完善了，可以跨天完成任务
"""
    这个东西目前还是有缺陷的，只能在本天内完成任务，
    但是实际上不一定，在后面需要自己再优化一下，
    现在先把整体的逻辑跑完善
"""


"""
    重新规划一下老师的需求，自动化程度不够，现在的想法是用 request 方法从网页上请求数据
    计算之后通过 request 方法返回计算的结果
    
    关于界面
        这个工具实际上并不是为了看而制作的，至少从原理上出发，分配数据这个功能显得更加的重要
        所以其余的界面都可以舍弃掉，把所有的计算机分配能力都用在数据的分配和主页面的显示上
        注册这些功能呢就不要了，实际上是一些可以信任的机器在请求数据，罗老师的机房总不会黑回来
        分配数据，显示数据，接收数据，完成工作
            关于主界面
                1.目前正在工作的任务名
                2.这个任务中总的数据集数量
                3.当前还剩下多少数据集没有被请求,相应的，当前已经被请求的数据集数量
                4.每一条数据的请求情况，当前是否被请求，是否完成数据上交，请求的IP是哪一个？
                5.所有的数据都显示的话，是不是有一点浪费算力呢!就只显示那些还没有被请求的数据吧
                6.如果有需要查看的话，再从数据库中取出所有的数据来呈现，也许后台会更好？先做出一个函数来这么实现吧
            关于其余的功能
                1.没必要显示，后台？
                2.返回的页面都是 site-home（首页）
                3.考虑压力
                4.就是为了计算数据，似乎那些生成的文件也没有必要保留，就只保留一个上传的data.pkl文件吧
"""


"""
    新一轮的需求
        新增加了两类数据处理
            1.大整数分解
            2.文本特定字数字典统计
        大整数分解处理代码 https://www.jianshu.com/p/65b274df414c?utm_campaign
            整数分解，又称质因子分解。在数学中，整数分解问题是指: 给出一个正整数，将其写成几个素数的乘积的形式。
            (每个合数都可以写成几个质数相乘的形式，这几个质数就都叫做这个合数的质因数。)
            整数的拆解
            这个和之前的数据处理倒是很像，搞一个列表吧,pandas 读取之后分列就行，那么就是一样的处理逻辑
        文本特定字数字典统计
            这个应该就是很多个文件分配出去，计算所有的所需要的字数出现的次数，但是需要注意文件的大小，最好是上传之前就已经切分过了，我这里也写一个切分文件到适合大小的函数
"""


# 获取当前时间
def get_time(request, chose_part):
    """
    获取当前的时间
       datetime.datetim e.now().strftime("%Y-%m-%d")
    :param chose_part:
    :param request:
    :return:
    """
    if chose_part == 1:
        time_now = datetime.datetime.now().strftime("%Y-%m-%d")
    elif chose_part == 2:
        time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elif chose_part == 3:
        time_now = datetime.datetime.now().strftime("%m-%d-%H")
    else:
        time_now = datetime.datetime.now().strftime("%Y-%m-%d-%H")
    return time_now


# 获取申请者IP
def get_ip(request):
    # X-Forwarded-For:简称 XFF 头，它代表客户端，也就是 HTTP 的请求端真实的 IP，只有在通过了 HTTP 代理或者负载均衡服务器时才会添加该项。
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]  # 真实的ip
    else:
        ip = request.META.get('REMOTE_ADDR')  # 获得代理ip
    return ip


# 错误页面
def error(request):
    context = {
        'error': '出现了错误! 应该是没有可供分配的任务! '
    }
    return render(request, 'work/error.html', context)


# 首页ajax更新
def update_data(request):
    try:
        tasks_now = models.Task.objects.all()
    except Exception as e:
        print(e)
        return redirect('error')
    task_info = []
    the_list = []
    unallocated_num_list = []
    for task in tasks_now:
        # 将每个任务的相关信息以字典形式写入一个列表
        task_detail = {'task': task.task_name}
        # 总数
        data_set_in_task = models.Original.objects.filter(task_belong=models.Task.objects.get(task_name=task))
        data_set_in_task_number = data_set_in_task.count()
        task_detail['num_all'] = data_set_in_task_number
        # 未分配数量
        unallocated_data_sets = models.Original.objects.filter(status=True,
                                                               task_belong=models.Task.objects.get(task_name=task))
        data_sum = unallocated_data_sets.count()
        task_detail['unallocated'] = unallocated_data_sets
        # 每一个任务的数据集都存放在一个列表中，每个任务的全部数据集都是一个列表，有几个任务，the_list 中就有几个分列表
        the_list_not_full = []
        for data_set in unallocated_data_sets:
            the_list_not_full.append(data_set.data_set)
        the_list.append(the_list_not_full)
        task_detail['unallocated_num'] = data_sum
        unallocated_num_list.append(data_sum)
        # 已分配数量，同上
        allocated_data_set = data_set_in_task_number - data_sum
        task_detail['allocated'] = allocated_data_set
        # 参与该任务的所有 IP
        task_in_ips = models.Assignment.objects.filter(task_belong=models.Task.objects.get(task_name=task))
        ip_list = []
        for ip in task_in_ips:
            ip_list.append(ip.name)
        task_detail['ips'] = set(ip_list)
        # 将上面的信息字典写入列表
        """
        包含几个键
            task                任务
            num_all             总数
            unallocated         未分配数据集
            unallocated_num     未分配数据集数量
            allocated           已分配数量
            ips                 参与IP
        """
        task_info.append(task_detail)
    assign_true = serializers.serialize("json", models.Original.objects.filter(status=True))
    context = {
        'task_infos': [1, 2, 3, 4, 5, 6, 8, 9, 72],
        'assign': assign_true,
        'data_sets': the_list,
        'num_all': unallocated_num_list,
    }
    return JsonResponse(context)


# 首页
def home(request):
    """
        取得那些还没有被请求的数据
    """
    # 当前任务
    try:
        tasks_now = models.Task.objects.all()
        # 获取长度，为了 ajax 使用
    except Exception as e:
        print(e)
        return redirect('error')
    try:
        task_info = []
        task_count = 0
        for task in tasks_now:
            # 将每个任务的相关信息以字典形式写入一个列表
            task_detail = {'task': task.task_name,
                           'task_id': task_count
                           }
            task_count += 1
            # 总数
            data_set_in_task = models.Original.objects.filter(task_belong=models.Task.objects.get(task_name=task))
            data_set_in_task_number = data_set_in_task.count()
            task_detail['num_all'] = data_set_in_task_number
            # 未分配数量
            unallocated_data_sets = models.Original.objects.filter(status=True,
                                                                   task_belong=models.Task.objects.get(task_name=task))
            data_sum = unallocated_data_sets.count()
            # 直接把未分配的数据集搞成列表
            unallocated_data_sets_list = []
            for data_set in unallocated_data_sets:
                unallocated_data_sets_list.append(data_set.data_set)
            task_detail['unallocated'] = unallocated_data_sets_list
            task_detail['unallocated_num'] = data_sum
            # 已分配数量，同上
            allocated_data_set = data_set_in_task_number - data_sum
            task_detail['allocated'] = allocated_data_set
            # 参与该任务的所有 IP
            task_in_ips = models.Assignment.objects.filter(task_belong=models.Task.objects.get(task_name=task))
            ip_list = []
            for ip in task_in_ips:
                ip_list.append(ip.name)
            task_detail['ips'] = set(ip_list)
            # 将上面的信息字典写入列表
            """
            包含几个键
                task                任务
                num_all             总数
                unallocated         未分配数据集
                unallocated_num     未分配数据集数量
                allocated           已分配数量
                ips                 参与IP
            """
            task_info.append(task_detail)
        # 规范化，将信息写入 context
        context = {
            'task_infos': task_info,
        }
        return render(request, 'work/home.html', context)
    except Exception as e:
        print(e)
        messages.info(request, '数据并未进行分组操作，请进入后台查看')
        return redirect('error')


# 从一个目录中获取后缀为 py 和 pkl 的文件名列表
def file_check(path, chose, ):

    """
    得到每一个目录下的文件名和这个目录的名字
    做一个字典
    {
    目录名: 文件列表
        }
    生成 task 的时候就是task_name = 目录名+文件列表[i].split('.')[0]
    目录生成 task 怎么去确定函数呢
    :param chose:
    :param path:
    :return:
    """
    file_list = []
    count = 0
    the_dict = {}
    for root, ds, fs, in os.walk(path):
        if chose == 1:
            if count == 0:
                the_dict[root] = fs
            else:
                dir_name_now = root.split(path + '\\')[1]
                the_dict[dir_name_now.replace('\\', '_', -1)] = fs
            # root 是路径
            # ds 是文件夹列表
            # fs 是当前目录下的文件名列表
            count += 1
        elif chose == 2:
            for f in fs:
                if f.endswith('.pkl') or f.endswith('.py') or f.endswith('.txt'):
                    file_list.append(f)
    if chose == 1:
        return the_dict
    elif chose == 2:
        return file_list


# 创建函数日期文件夹
def create_function_dir(request):
    function_dir_path = 'functions/' + get_time(request, 1)
    path = pathlib.Path(function_dir_path)
    if path.is_dir():
        pass
        messages.info(request, '该目录已经创建')
    else:
        os.mkdir(function_dir_path)
        messages.success(request, '目录创建成功')
    return redirect('/admin/work/function')


# 检查一些目前还有哪些超时的项目，清除 assignment，并不影响正常使用，要记得把 Original 的相应数据集的 status 改为 True
def check_timeout(request):
    """
    获取 assignments 以及它们的预定上交时间
    """
    assignments = models.Assignment.objects.values_list()
    time_now = datetime.datetime.now()
    for obj in assignments:
        upload_time = obj[6]
        if upload_time < time_now:
            models.Assignment.objects.filter(pk=obj[0]).delete()
            the = models.Original.objects.filter(pk=obj[4])
            the.update(
                status=True
            )
            models.User.objects.filter(IP=obj[1]).update(
                status=True
            )
    return redirect('site-home')


# 计时器，检查超时项目并清除，检查各个任务上传文件数量是否已经达到预定标准，达到则生成聚合上传文件为最终预测文件
def timer(request):
    # 用 the_sign 用来作为循环条件
    the_sign = True
    while the_sign:
        # 获取所有的分配总数，用于后面的匹配
        # 获取所有的分配
        assignments = models.Assignment.objects.values_list().filter(upload=False)
        # 时间
        time_now = datetime.datetime.now()
        try:
            # 循环查询所有的分配，如果有超时，就删除
            for obj in assignments:
                # 获取该任务应该上传的时间
                upload_time = obj[6]
                if upload_time < time_now:
                    models.Assignment.objects.filter(pk=obj[0]).delete()
                    the = models.Original.objects.filter(pk=obj[4])
                    the.update(
                        status=True
                    )
                    models.User.objects.filter(IP=obj[1]).update(
                        status=True
                    )
            time.sleep(5)
        except:
            time.sleep(5)
        the_datetime = get_time(request, 1)
        task_now = models.Task.objects.filter(task_over=False)
        the_predict_path = 'predict_files/' + the_datetime
        predict_files_exist = []
        for _, _, fs, in os.walk(the_predict_path):
            for f in fs:
                if f.endswith('.csv'):
                    predict_files_exist.append(f.split('.')[0])
        aggregate_times = 0
        for task in task_now:
            # 先判断一下这个任务是不是已经生成了相应的预测文件,如果有，就跳出
            if task.task_name in predict_files_exist:
                continue
            # 如果没有，就继续接下来的代码，同时 aggregate_times 加上1
            aggregate_times += 1
            the_submit_path = 'submit_files/' + the_datetime + '/' + task.task_name
            name_list = []
            for _, _, fs, in os.walk(the_submit_path):
                for f in fs:
                    if f.endswith('.pkl'):
                        name_list.append(f)
            file_path = 'data/' + the_datetime + '/' + '{}.pkl'.format(task.task_name.split('-')[0])
            with open(file_path, 'rb') as f:
                data_now = pickle.load(f)
            """
                创建一个列表，其中包含两个字典，
                第一个字典存放任务信息
                    { 
                        '任务名': XXX,
                        '创建时间': XXXX-XX-XX,
                        '结束时间': XXXX-XX-XX,
                        '参与的IP数量': num
                    }  
                第二个字典存放数据的分配情况
                    {
                        'user1': [1,2,3,4.....n], 
                        'user2': [1,2,3,4.....n],
                        ......
                        'usern': [1,2,3,4.....n] 
                    }
            """
            data_size = data_now.shape[0]
            if (data_size % task.num) != 0:
                groups = (data_size // task.num) + 1
            else:
                groups = data_size // task.num
            # groups 是具体有多少个需要处理的数据集
            """
            如果该任务对应的上传文件的文件名列表 name_list 等于该任务根据单任务数据量所划分的数据集数量 groups
            那么就生成相应的最终预测文件
            逻辑为——
                根据之前的 name_list 获取到每一个文件的数据并存入一个列表
                将该列表转换为 DateFrame 类型
                检测是否存在日期文件夹，如果没有就生成一个用来存放这一天内的最终结果文件
                转换为老师需要的最终格式
                设定任务名为该最终结果文件的名字
                生成文件
                将相应的 Task 的 upload 属性改为 False
            """
            while len(name_list) == groups:
                the_all_data = []
                for name in name_list:
                    file_path = the_submit_path + '/' + name
                    with open(file_path, 'rb') as f:
                        data = pickle.load(f)
                    f.close()
                    the_all_data.append(data)
                the_new_list = []
                for use_data in the_all_data:
                    the_new_list.append(pd.DataFrame(use_data))
                try:
                    create_path_use = BASE_DIR + r'\predict_files'
                    predict_file_name = './' + the_datetime
                    os.mkdir(create_path_use + predict_file_name)
                except FileExistsError:
                    pass
                dm = pd.concat(the_new_list, ignore_index=True)
                csv_path = 'predict_files/' + the_datetime + '/' + task.task_name + '.csv'
                dm.to_csv(csv_path, encoding='gbk', index=False)
                models.Task.objects.filter(task_name=task.task_name).update(
                    upload=True
                )
                messages.success(request, '{}任务聚合成功!'.format(task.task_name))
                # 查询现在 Task 中还有没有 upload 属性为 False 的，如果有，那就意味着这个检查函数还不能终止，如果没有那就是都结束了，那就
                if models.Task.objects.filter(upload=False):
                    pass
                else:
                    the_sign = False
                    break
            time.sleep(8)
    return redirect('site-home')


# IP申请获得一个数据集
def get_data(request):
    response = {
        'status_code': 200,
        'msg': '',
        'fail_list': []
    }
    if request.method == "POST":
        ip = request.POST.dict()['ip']
        capability_level = int(request.POST.dict()['capability_level'])
    else:
        ip = get_ip(request)
    """
        设计一下最新的显示方式吧
        1.所有的数据尽量都在 home 这个页面tr呈现出来
        2.自动化作业，requests 这些库的使用吧
        3.哪些数据被请求到了在 home 呈现吧，这是个有用的小工具，没有必要搞得复杂，但是有必要精细，
            自己的第一个个人作品，至少要为以后的其它作品起到一定的参考作用
    """
    """
        先确定这个申请的 IP 上次的任务完成与否
        User 有一个 status 属性可以使用
    """
    # 下面这部分是解决单任务工作完成后无法自动将 task. status 和 task. assignment_over 更改成为指定状态
    task_status_true = models.Task.objects.filter(status=True, split_status=True)
    for task_status in task_status_true:
        if not models.Original.objects.filter(task_belong=task_status):
            # 如果没有对应任务的数据集，那么跳出此次循环，其实大概率不存在，难保后期老师加需求到可以先上传再决定是否进行数据分组
            continue
        if not models.Original.objects.filter(task_belong=task_status, status=True):
            # 如果的确有对应任务的数据集，但是已经完全分配完毕了，也就是 status=True 检索不到内容，
            # 那么将对应任务的可分配标识 status 更改为 False，分配完毕标识修改为 True
            models.Task.objects.filter(task_name=task_status.task_name).update(
                status=False,
                assignment_over=True,
            )
    """
        这里做一个标记，暂时不做修改，因为需要先对其他函数进行修改才可以进行下一步的修改工作
    """
    # 根据数据来吧，不根据任务来做下面的函数了，根据函数会有一个问题，当该任务并没有进行数据分组操作的时候，
    # 那么就会找不到相应的任务数据，也就无法完成IP的数据申请
    the_data_set_status_true = models.Original.objects.filter(Q(func_capability_level__lte=capability_level),
                                                              status=True).first()
    if not the_data_set_status_true:
        response['status_code'] = 200
        response['success'] = 'FALSE'
        response['msg'] = 'IP CAPABILITY--{}'.format(capability_level) + 'IS LOW FOR CURRENT TASKS,LOW'
        return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")
    the_task = the_data_set_status_true.task_belong
    task_name = str(the_task)
    try:
        # 如果存在的话判断其状态
        the_ip_status = models.User.objects.get(IP=ip).status
    except:
        # 没有的话就创建一个并取得其状态用于之后的判断
        models.User.objects.create(
            IP=ip,
            status=True
        )
        the_ip_status = True
    if not the_ip_status:
        response['success'] = 'LAST'
        response['msg'] = 'DATA_SETS NOT UPLOAD'
        return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")
    """
        dict.items()    所有的键值对
        dict.keys()     所有的键
        dict.values()   所有的值
    """
    """
        选取分配状态为True的数据集（Original）
        选取第一个并把status改为False
        知道这个数据集的编号
        计算得出在data.pkl文件中的区间
    """
    # data_true = models.Original.objects.values_list().filter(status=True,
    #                                                          task_belong=models.Task.objects.get(task_name=task_name))
    # 在 the_data_set_status_true 的基础上再加上 task_name 这一条件

    # 这里有大问题，这样做的前提是函数能够正常运行，很明显出现了问题，status 修改了，但是却没有创建对应的分配 assignment，但是好像没有好的解决办法，现在就在 timer 中做处理
    # 保证这个选取的数据处于占用状态
    models.Original.objects.filter(data_set=the_data_set_status_true.data_set).update(
        status=False
    )
    try:
        # 如果有，那么写入提示信息，跳出函数
        models.Assignment.objects.get(data_set=the_data_set_status_true)
        response['status_code'] = 200
        response['msg'] = 'TRY AGAIN PLEASE'
        response['success'] = 'RETRY'
    except Exception:
        # 如果没有，那么创建
        # 先把分配给创建好
        try:
            models.Assignment.objects.create(
                data_set=models.Original.objects.get(data_set=the_data_set_status_true.data_set),
                name=ip,
                IP=models.User.objects.get(IP=ip),
                task_belong=models.Task.objects.get(task_name=task_name),
            )
            # 要确保该数据集没有被申请才设定 status
            models.User.objects.filter(IP=ip).update(
                status=False,
                upload_times=models.User.objects.get(IP=ip).upload_times + 1,
                upload_times_today=models.User.objects.get(IP=ip).upload_times_today + 1
            )
            response['status_code'] = 200
            response['msg'] = 'SUCCESSFULLY APPLY DATA_SET---{}'.format(the_data_set_status_true.data_set)
            response['success'] = 'TRUE'
        except IntegrityError:
            response['status_code'] = 200
            response['msg'] = 'TRY AGAIN PLEASE'
            response['success'] = 'RETRY'
    return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")


# IP上传运算结果
def upload(request):
    # 获取还没有完结的 task 的列表
    tasks = models.Task.objects.filter(task_over=False)
    # 根据任务名得到相应的日期，这样就解决了不能跨天进行任务的问题
    name_list = []
    task_originals = 0
    for task in tasks:
        date = task.task_name.split('+')[1]
        the_submit_path = 'submit_files/' + date + '/' + task.task_name
        for _, _, fs, in os.walk(the_submit_path):
            for f in fs:
                if f.endswith('.pkl') or f.endswith('.txt'):
                    name_list.append(f)
        task_originals += models.Original.objects.filter(task_belong=task).count()
    if len(name_list) == task_originals:
        # 预定上传文件数量
        return redirect('site-home')
    if request.method == 'POST':
        # 字典方式获取 IP
        ip = request.POST.dict()['ip']
        the = request.FILES.dict()

        """
            用ip来搜索对应的数据集，
        """
        the_data_set_name = models.Assignment.objects.filter(name=ip).order_by('-created_time').first().data_set
        the_data_set = models.Original.objects.get(data_set=the_data_set_name).data_set
        the_task = models.Original.objects.get(data_set=the_data_set_name).task_belong
        try:
            write_in_data = pickle.load(the.get('file'))
        except EOFError:
            return redirect('site-home')
        the_time = get_time(request, 1)
        create_path_use = BASE_DIR + r'\submit_files'
        try:
            file_name = './' + the_time
            try:
                os.mkdir(create_path_use + file_name)
            except:
                pass
            the_new_path = create_path_use + r'\{}'.format(the_time)
            file_name = './' + the_task.task_name
            os.mkdir(the_new_path + file_name)
        except FileExistsError:
            pass
        submit_file_path = 'submit_files/' + the_time + '/' + the_task.task_name + '/' + the_data_set + '.pkl'
        try:
            file = open(submit_file_path, 'wb')
            pickle.dump(write_in_data, file)
            file.close()
        except OSError:
            with open(submit_file_path) as file:
                pickle.dump(write_in_data, file)
                file.close()
        messages.success(request, '上传成功!!')
        models.User.objects.filter(IP=ip).update(
            status=True
        )
        try:
            models.DataUpload.objects.create(
                IP=models.User.objects.get(IP=ip),
                task_belong=models.Task.objects.get(task_name=the_task),
                data_set=models.Original.objects.get(data_set=the_data_set_name)
            )
        except Exception as e:
            print(e)
            return redirect('site-home')
        models.Original.objects.filter(data_set=the_data_set).update(
            upload=True
        )
        models.Assignment.objects.filter(data_set=models.Original.objects.get(data_set=the_data_set)).update(
            upload=True
        )
        return HttpResponse('上传成功')
    else:
        return HttpResponse('请重新尝试')


# IP下载申请得到的数据集
def data_download(request):
    response = {
        'status_code': 200,
        'msg': '',
        'fail_list': []
    }
    if request.method == 'GET':
        ip = request.GET.dict()['ip']
        """
            先获取当前任务的 data_set,也就是 Assignment 中的一条记录，
            为什么一条，因为我们用 IP 去筛选记录的时候，该用户是无法同时申请两个数据集的
        """

        try:
            allocated_data_set = models.Assignment.objects.get(name=ip, upload=False)
        except Exception as e:
            print(e)
            response['status_code'] = 200
            response['msg'] = 'The IP Did Not Return The Last Data'
            response['download'] = 'FALSE'
            return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")
        task_name = allocated_data_set.task_belong.task_name
        provider_ip = str(models.Task.objects.get(task_name=task_name).provider_name)
        # provider_ip_pk = provider_models.Provider.objects.get(provider_ip=provider_ip).pk
        # 拿到日期文件夹的名字    1--electric+2021-05-30
        date = str(task_name).split('+')[1]
        # 拿到日期文件夹之后的文件路径
        path_below_date = str(task_name).split('+')[0].replace('--', '/').replace('_', '/')

        pre_path = 'data/' + date + '/' + path_below_date
        the_file_type_list = ['txt', 'pkl']
        for file_type in the_file_type_list:
            if os.path.isfile(pre_path + '.{}'.format(file_type)):
                break
        the_task_now = models.Task.objects.get(task_name=task_name)
        # 拿到数据集对应的 	1--electric+2021-05-31+1  也就是1
        the_id = int(str(allocated_data_set.data_set).split('+')[-1])
        # 比如编号为1，那么就是从the_start_point=0，the_end_point=0+8000（举例子），
        # 8000条数据，就是[0:8000],实际就是0--7999总计8000
        the_start_point = (the_id - 1) * the_task_now.num
        the_end_point = the_start_point + the_task_now.num
        data_path = pre_path + '.{}'.format(file_type)
        # 分别尝试，这样查询会快一些
        if file_type == 'txt':
            with open(data_path, 'r+', encoding='gbk', errors='ignore') as f:
                data_in_file = f.readlines()
            f.close()
            # 文本分析，readlines 返回的列表
            the_download_data = data_in_file[the_start_point:the_end_point]
        elif file_type == 'pkl':
            with open(data_path, 'rb') as f:
                data_in_file = pickle.load(f)
            f.close()
            if isinstance(data_in_file, list):
                # 大整数分解的数据，列表
                the_download_data = data_in_file[the_start_point:the_end_point]
            elif isinstance(data_in_file, pandas.core.frame.DataFrame):
                # 电力预测的数据，pandas.core.frame.DataFrame
                the_download_data = data_in_file.iloc[the_start_point: the_end_point, :]
        # 先写入文件
        the_data_set = allocated_data_set.data_set.data_set
        file_path = 'download_data/' + str(ip) + '.' + file_type
        if file_type == 'txt':
            with open(file_path, 'w') as f:
                for text_line in the_download_data:
                    f.write(text_line)
        else:
            with open(file_path, 'wb') as f:
                pickle.dump(the_download_data, f)
        f.close()
        # 从文件里再读出来
        the_file = open(file_path, 'rb')
        response = FileResponse(the_file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="{0}"'.format(
            escape_uri_path(the_data_set + '.' + file_type))
        response['task_capability_level'] = str(
            models.Original.objects.get(data_set=the_data_set).func_capability_level)
        response['func_ip'] = str(provider_ip)
        return response


# 后台使用，根据任务设定的单任务数据量将一个数据文件拆分为若干个数据集
def split_data_to_groups(request, task_name):
    count_fail = 0
    for name in task_name:
        # 有时候为了方便是全选 task，但是有感觉没必要一个个去看，或者说有可能错看，那么就会有一些已经完结的 task 进入上面的列表，
        # 做一个判定， 如果 Task.task_over=True，那么就跳出这个 name 的循环一次，直接开始下一次
        if models.Task.objects.get(task_name=name).task_over:
            continue
        name_for_create = str(name)
        name_for_file = str(name).split('+')[0]
        file_path_split = name_for_file.split('_')
        real_path = '/'
        for i in range(len(file_path_split)):
            if i == len(file_path_split) - 1:
                real_path += file_path_split[i]
            else:
                real_path += file_path_split[i] + '/'
        time_for_path = str(name).split('+')[1][:10]
        file_types = ['.pkl', '.txt']
        try:
            file_type_count = 0
            for file_type in file_types:
                file_path = 'data/' + time_for_path + real_path + file_type
                try:
                    if file_type == '.txt':
                        with open(file_path, 'rb') as f:
                            the_data = f.readlines()
                            f.close()
                            data_size = len(the_data)
                    elif file_type == '.pkl':
                        with open(file_path, 'rb', ) as f:
                            # 目前只能支持 list 和 pandas.core.frame.DataFrame
                            data_now = pickle.load(f)
                            if isinstance(data_now, list):
                                data_size = len(data_now)
                            elif isinstance(data_now, pandas.core.frame.DataFrame):
                                data_size = data_now.shape[0]
                    break
                except FileNotFoundError:
                    file_type_count += 1
                    continue
            # 如果 file_type_count 是 file_types 的长度，那么就意味着上面查找文件的进程没有找到文件，就跳出这个函数
            if file_type_count == len(file_types):
                messages.error(request, '未检测到相应数据文件!')
                messages.info(request, '请确认是否上传文件!')
                return redirect('/admin/work/original')
            """
                创建一个列表，其中包含两个字典，
                第一个字典存放任务信息
                    { 
                        '任务名': XXX,
                        '创建时间': XXXX-XX-XX,
                        '结束时间': XXXX-XX-XX,
                        '参与的IP数量': num
                    }  
                第二个字典存放数据的分配情况
                    {
                        'user1': [1,2,3,4.....n], 
                        'user2': [1,2,3,4.....n],
                        ......
                        'usern': [1,2,3,4.....n] 
                    }
            """
            # 既然现在不需要写入一个新的文件，那么就只读取数据量的大小
            # 然后根据给定的分配量划分出多少个数据集的名字就可以了，没必要遍历
            task_now = models.Task.objects.get(status=True, task_name=name)

            if data_size == 0:
                messages.info(request, '数据量为0，请检查文件!')
                return redirect('/admin/work/original')

            if (data_size % task_now.num) != 0:
                groups = (data_size // task_now.num) + 1
            else:
                groups = data_size // task_now.num
            for i in range(groups):
                num = i + 1
                user = name_for_create + '+' + str(num)
                try:
                    if models.Original.objects.filter(data_set=user):
                        messages.info(request, '{}已经创建'.format(user))
                        continue
                except Exception:
                    pass
                models.Original.objects.create(
                    data_set=user,
                    status=True,
                    task_belong=task_now,
                )
            messages.success(request, str(name) + '任务数据导入成功')
        except Exception:
            count_fail += 1
            messages.info(request, str(name) + '任务数据导入失败')
    messages.success(request, '创建数据结束, 失败' + str(count_fail) + '次')
    return redirect('/admin/work/task')


# 文件聚合， 后台使用，如果没有启动计时器自动生成预测文件，可以通过这个按钮手动生成相应项目的最终结果文件
def file_aggregate(modeladmin, request, queryset):
    """
    先获取总计有多少个数据集
    download_data文件夹中有具体一天内的所有信息，如果处理及时的话，所有的数据都应该在一天内处理完毕
    获取文件名
    """
    task_names = list(queryset)
    the_datetime = get_time(request, 1)
    for task_name in task_names:
        date = str(task_name).split('+')[1].split('-')
        # 获取路径中的日期
        date_for_dir = ''
        for i in range(len(date[:3])):
            if i <= 1:
                date_for_dir += date[:3][i] + '-'
            else:
                date_for_dir += date[:3][i]

        the_submit_path = 'submit_files/' + date_for_dir + '/' + str(task_name)
        # 拿到某一个任务的上传目录下的所有文件名
        name_list = file_check(the_submit_path, 2)
        # 如果是空的，那么跳出
        if not name_list:
            messages.error(request, '该日期文件夹下无文件，请确认是否成功上传!')
            return redirect('/admin/work/task')
        # 存储所有数据的一个列表
        the_all_data_list = []
        for name in name_list:
            file_path = the_submit_path + '/' + name
            with open(file_path, 'rb') as f:
                data = pickle.load(f, errors="strict")
            f.close()
            if isinstance(data, list):
                the_all_data_list.append(data)
            elif isinstance(data, numpy.ndarray):
                the_all_data_list.append(data)
            else:
                # 也就是文本处理的上传文件，文件内的格式应该是字典dict，这个需要进行进一步的计算
                the_all_data_dict = {}
                for key in data:
                    if the_all_data_dict.get(key):
                        the_all_data_dict[key] += data[key]
                    else:
                        the_all_data_dict[key] = data[key]
                pre_all_data_list = list(the_all_data_dict.values())
                if not the_all_data_list:
                    for i in range(len(pre_all_data_list)):
                        empty_list = [pre_all_data_list[i]]
                        the_all_data_list.append(empty_list)
                else:
                    for i in range(len(pre_all_data_list)):
                        the_all_data_list[i][0] += pre_all_data_list[i]
        the_new_list = []
        for use_data in the_all_data_list:
            the_new_list.append(pd.DataFrame(use_data))
        try:
            create_path_use = BASE_DIR + r'\predict_files'
            predict_file_name = './' + the_datetime
            os.mkdir(create_path_use + predict_file_name)
        except FileExistsError:
            pass
        dm = pd.concat(the_new_list, ignore_index=True)
        csv_path = 'predict_files/' + the_datetime + '/' + '{}.csv'.format(task_name)
        dm.to_csv(csv_path, encoding='gbk', index=False)
        models.Task.objects.filter(task_name=task_name).update(
            task_over=True,
        )
    messages.success(request, '聚合成功!')
    return redirect('/admin/work/task')


# 上传数据文件
def upload_data_file(request):
    """
    工作逻辑.py:
        检测文件是否为空
        检测日期文件夹和对应的 IP 数据文件夹是否存在
        检测文件格式是否是 txt 和 pkl 其中一种，如果不是，返回一个信息
        先将上传的文件存放到 data 文件夹下指定日期文件夹下指定 IP 数据文件夹下
        将存放的文件逐一生成数据库中的任务 Task，默认分组标识 split_status 为 False，可分配标识为 True，其余为 False
        上一步中同时将文件的真实路径和形成的 Task.task_name 组合成为字典中的一个个键值对，方便下一步的数据分组工作
        进行数据分组，完成之后将对应的 Task.split_status 更改为 True
    :param request:
    :return: HttpResponse
    """
    response = {
        'status_code': 200,
        'msg': '',
        'fail_list': []
    }
    file_for_upload = request.FILES.dict()  # 获取上传的文件，如果没有文件，默认为 None
    if not file_for_upload:
        response['msg'] = 'FILE NOT FOUND,PLEASE BE SURE ABOUT WHAT YOU ARE TRING TO UPLOAD'
        return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")
    ip = request.POST.dict()['ip']
    provider = provider_models.Provider.objects.get(provider_ip=ip)
    ip_id = provider.pk
    create_path_use = BASE_DIR + r'\data'
    the_time = get_time(request, 1)
    file_name_date = './' + the_time
    file_name = './' + the_time + '/' + str(ip_id)
    if not os.path.isdir(create_path_use + file_name_date):
        os.mkdir(create_path_use + file_name_date)
    if not os.path.isdir(create_path_use + file_name):
        os.mkdir(create_path_use + file_name)
    for key in file_for_upload:
        if str(file_for_upload[key].name).split('.')[1] not in ['txt', 'pkl', 'zip']:
            response['status_code'] = 400
            response['msg'] = 'txt、pkl、zip---TYPE ONLY'
        the_path = 'data/' + the_time + '/' + str(ip_id) + '/' + '{}'.format(file_for_upload[key].name)
        if os.access(the_path, os.F_OK):
            response['msg'] = 'FILE EXIST,DETAIL IN FAIL_LIST'
            response['fail_list'].append(str(file_for_upload[key]))
            continue
        the_upload_file = open(the_path, 'wb')
        for chunk in file_for_upload[key].chunks():
            the_upload_file.write(chunk)
        the_upload_file.close()
        if str(file_for_upload[key].name).split('.')[1] == 'zip':
            with zipfile.ZipFile(the_path) as zf:
                for fn in zf.namelist():
                    zf.extract(member=fn, path='data/' + the_time + '/' + str(ip_id))
                zf.close()
                os.remove(the_path)     # 解压文件之后删除压缩包
    # 上传成功之后更新一下Provider的今日上传文件次数和总的次数
    provider_for_update = provider_models.Provider.objects.get(provider_ip=ip)
    provider_for_update.upload_times += 1
    provider_for_update.save()
    """
        上传文件的工作完成，provider_models.File 的记录也写入，接下来忙其他的内容
        check_file 得到文件名清单并生成所有的任务，
        现在就不要求使用者再手工进行其余的任务了，完完全全由API接口来完成所有的工作
    """
    file_to_task_dict = file_check('data/' + the_time + '/' + str(ip_id), 1)
    # 现在我将文件名字典中的文件还原为真实的路径,在下面的函数中将真实路径记录在 files_real_path
    files_real_path = {}
    # 写入的这个字典中的第一个键值对的值没有对应的上级目录作为函数前缀，文件名本身就是函数，所有没有必要加上前缀
    file_to_task_count = 0
    for key in file_to_task_dict:
        if file_to_task_count == 0:     # 一级
            pre_path = key
            pre_path_to_file = key.split('/', 1)[1].replace('/', '+')
            if file_to_task_dict[key]:
                for file_name_now in file_to_task_dict[key]:
                    file_name = file_name_now + '+' + pre_path_to_file + '+' + key.replace('_', '+')
                    # 先把File的记录写好
                    provider_models.File.objects.create(
                        file_name=file_name,
                        provider_name=provider.provider_ip,
                        task_status=TASK_STATUS[0],
                        file_type=FILE_TYPE[1],
                    )
                    task_name_for_creating = str(ip_id) + '--' + str(file_name_now).split('.')[0] + '+' + the_time
                    # 写入真实路径
                    files_real_path[task_name_for_creating] = pre_path + '/' + file_name_now
                    # 一级的函数名就是文件名
                    func_name = str(file_name_now).split('.')[0]
                    models.Task.objects.create(
                        task_name=task_name_for_creating,
                        status=True,
                        provider_name=provider,
                        func_name=models.Function.objects.get(func_name=func_name, provider_name=ip),
                        task_capability_level=models.Function.objects.get(func_name=func_name,
                                                                          provider_name=ip).func_capability_level,
                        num=models.Function.objects.get(func_name=func_name, provider_name=ip).single_data_set_num,
                    )
                    update_function_status = models.Function.objects.get(func_name=func_name, provider_name=ip)
                    update_function_status.status = True
                    update_function_status.save()
            # 加一以避免再次进入上面的循环
            file_to_task_count += 1
        else:       # 二级
            if not file_to_task_dict[key]:
                # 列表为空，该目录下没有直接的数据文件，可能全部是文件夹
                continue
            """
                这部分需要用户上传的数据文件夹不能存在下划线
            """

            for file_name_now in file_to_task_dict[key]:
                file_name = file_name_now + '+' + pre_path_to_file + '+' + key.replace('_', '+')
                # 先把 File 的记录写好
                provider_models.File.objects.create(
                    file_name=file_name,
                    provider_name=provider,
                    task_status=TASK_STATUS[0],
                    file_type=FILE_TYPE[1],
                )
                task_name_for_creating = str(ip_id) + '--' + key + '_' + str(file_name_now).split('.')[
                    0] + '+' + the_time
                files_real_path[task_name_for_creating] = pre_path + '/' + key.replace('_', '/') + '/' + file_name_now
                # 其余地方的函数存储在键名中
                func_name = key.split('_')[0]
                models.Task.objects.create(
                    task_name=task_name_for_creating,
                    status=True,
                    provider_name=provider,
                    func_name=models.Function.objects.get(func_name=func_name, provider_name=ip),
                    task_capability_level=models.Function.objects.get(func_name=func_name,
                                                                      provider_name=ip).func_capability_level,
                    num=models.Function.objects.get(func_name=func_name, provider_name=ip).single_data_set_num,
                )
                update_function_status = models.Function.objects.get(func_name=func_name, provider_name=ip)
                # if not update_function_status:
                update_function_status.status = True
                update_function_status.save()
    # 现在我得到了一个记录有所有数据文件的字典 files_real_path
    for key in files_real_path:
        with open(files_real_path[key], 'rb') as f:
            if files_real_path[key].endswith('txt'):
                data_in_file = f.readlines()
                f.close()
                data_size = len(data_in_file)
            elif files_real_path[key].endswith('pkl'):
                data_in_file = pickle.load(f)
                f.close()
                if isinstance(data_in_file, list):
                    data_size = len(data_in_file)
                elif isinstance(data_in_file, pandas.core.frame.DataFrame):
                    data_size = data_in_file.shape[0]
            task_for_file = models.Task.objects.get(task_name=key,
                                                    provider_name=provider)
            # 检查一下文件的大小，为零的话给个提醒
            if data_size == 0:
                file_name = files_real_path[key].split('/')[-1]
                response['status_code'] = 400
                response['msg'] += '----{}文件无内容，请检查后重新上传该文件'.format(file_name)
                response['fail_list'].append(file_name)
                continue
            # 判断一下需不需要向上取整
            if (data_size % task_for_file.num) != 0:
                groups = (data_size // task_for_file.num) + 1
            else:
                groups = data_size // task_for_file.num
            for i in range(groups):
                num = i + 1
                data_set_name = key + '+' + str(num)
                try:
                    if models.Original.objects.filter(data_set=data_set_name):
                        continue
                except Exception as e:
                    print(e)
                # 创建数据
                models.Original.objects.create(
                    data_set=data_set_name,
                    status=True,
                    task_belong=task_for_file,
                    func_capability_level=task_for_file.task_capability_level
                )
            # 设定对应任务的是否分组标识修改为 True
            task_for_file.split_status = True
            task_for_file.save()
    return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")


def file_count(dirname, filter_types=None):
    """
        Count the files in a directory includes its subfolder's files
       You can set the filter types to count specific types of file
    """
    if filter_types is None:
        filter_types = None
    count_file = 0
    filter_is_on = False
    if filter_types:
        filter_is_on = True
    for item in os.listdir(dirname):
        abs_item = os.path.join(dirname, item)
        if os.path.isdir(abs_item):
            # Iteration for dir
            count_file += file_count(abs_item, filter_types)
        elif os.path.isfile(abs_item):
            if filter_is_on:
                # Get file's extension name
                extname = os.path.splitext(abs_item)[1]
                if extname in filter_types:
                    count_file += 1
            else:
                count_file += 1
    return count_file


def delete_all(request):
    dir_list = [
        'data',
        'download_data',
        'predict_files',
        'submit_files',
    ]
    for dirname in dir_list:
        shutil.rmtree(dirname)
        os.mkdir(dirname)
    the_original = models.Original.objects.all()
    count = 0
    for original in the_original:
        original.delete()
        count += 1
    the_users = models.User.objects.all()
    count = 0
    for user in the_users:
        user.delete()
        count += 1
    return redirect('site-home')


# 下载结果文件
def predict_download(modeladmin, request, queryset):
    tasks = list(queryset)
    the_datetime = get_time(request, 1)
    if len(tasks) >= 2:
        zip_path = 'predict_files/' + the_datetime + '/predict_download.zip'
        success = True
        count_use = 0
        for task in tasks:
            date = str(task.task_name).split('+')[1].split('-')
            date_for_dir = ''
            for i in range(len(date[:3])):
                if i <= 1:
                    date_for_dir += date[:3][i] + '-'
                else:
                    date_for_dir += date[:3][i]
            # 判断该文件是否已经写入过数据，避免数据直接被覆盖
            if count_use == 0:
                mode = 'w'
            else:
                mode = 'a'
            try:
                with zipfile.ZipFile(zip_path, mode=mode) as f:
                    the_predict_path = 'predict_files/' + date_for_dir + '/' + str(task) + '.csv'
                    try:
                        the_file = open(the_predict_path, 'rb')
                        f.write(the_predict_path)
                        count_use += 1
                        # 正常生成了文件，那么将相应的 Task 的 assignment_over 属性设置为 True
                        models.Task.objects.filter(task_name=task).update(
                            assignment_over=True
                        )
                    except FileNotFoundError:
                        messages.error(request, '没有' + str(task) + '文件')
                        f.close()
                        continue
            except FileNotFoundError:
                create_path_use = BASE_DIR + r'\predict_files'
                predict_file_name = './' + the_datetime
                os.mkdir(create_path_use + predict_file_name)
                messages.info(request, '没有相关文件，请重试')
                success = False
                break
        if success:
            the_file = open(zip_path, 'rb')
            response = FileResponse(the_file)
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename={}'.format(escape_uri_path('data.zip'))
            return response
        else:
            messages.error(request, '下载失败')
            return redirect('/admin/work/task')
    else:
        the_predict_path = 'predict_files/' + the_datetime + '/' + str(tasks[0]) + '.csv'
        try:
            the_file = open(the_predict_path, 'rb')
        except FileNotFoundError:
            messages.error(request, '请等待工作完成后再下载!')
            return redirect('/admin/work/task')
        response = FileResponse(the_file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = 'attachment;filename="{}.csv"'.format(
            escape_uri_path('{}'.format(str(tasks[0]))))
        return response


# 更新了 ajax 之前的数据内容
def home_try(request):
    """
        取得那些还没有被请求的数据
    """
    # 当前任务
    try:
        tasks_now = models.Task.objects.filter(task_over=False)
    except Exception as e:
        print(e)
        return redirect('error')
    task_info = []                      # 外层列表
    unallocated_data_sets_list = []     # 未分配的数据集
    allocated_data_sets_list = []       # 已经分配的数据集
    unallocated_sum = 0                 # 未分配数量
    allocated_num = 0                   # 分配数量
    upload_number = 0                   # 上传文件数量
    task_count = 0                      # 任务在此次查询中的编号
    assignment_all_number = 0           # 数据集总数
    try:
        # 先获取那些还没有分配完毕的任务，首先从 Task 开始，寻找 assignment_over 的
        for task in tasks_now:
            data_upload_the_task = models.DataUpload.objects.filter(task_belong=task)
            upload_number += data_upload_the_task.count()
            assignment_all_number += models.Original.objects.filter(task_belong=task).count()

            # 将第一个任务的相关信息以字典形式写入一个列表
            # 未分配数量
            unallocated_data_sets = models.Original.objects.filter(status=True,
                                                                   task_belong=task)
            allocated_data_sets = models.Original.objects.filter(status=False,
                                                                 task_belong=task).order_by('-created_date')
            unallocated_sum = unallocated_data_sets.count()
            allocated_num = allocated_data_sets.count()
            # 直接把未分配的数据集搞成列表
            for unallocated_data_set in unallocated_data_sets:
                unallocated_data_sets_list.append(unallocated_data_set.data_set)
            for allocated_data_set in allocated_data_sets:
                allocated_data_set_dict = {
                    'data_set_name': allocated_data_set.data_set,
                    'data_set_id': allocated_data_set.id,
                    'IP': models.Assignment.objects.get(
                        data_set=models.Original.objects.get(data_set=allocated_data_set.data_set)).name,
                }
                allocated_data_sets_list.append(allocated_data_set_dict)
                allocated_data_set_dict = {}
            # 将上面的信息字典写入列表
            """
            包含几个键
                task                任务
                num_all             总数
                unallocated         未分配数据集
                unallocated_num     未分配数据集数量
                allocated           已分配数量
                ips                 参与 IP
            """
        task_detail = {'upload_num': upload_number,
                       'assignment_all': assignment_all_number,
                       'task_id': task_count,
                       'unallocated_data_sets': unallocated_data_sets_list,
                       'allocated_data_sets': allocated_data_sets_list,
                       'unallocated_num': unallocated_sum,
                       'allocated_num': allocated_num, }
        # 已分配数量，同上
        task_info.append(task_detail)
        # 重新写一个全部 task 的列表
        task_all = models.Task.objects.filter(assignment_over=False)
        task_all_list = []
        # 参与的 IP 列表
        ip_list = []
        count = 1
        for task in task_all:
            # 每一个 Task 的数量
            task_num = models.Original.objects.filter(task_belong=task).count()
            task_allocated = models.Original.objects.filter(task_belong=task, status=False).count()
            task_upload = models.DataUpload.objects.filter(task_belong=task).count()
            # 参与该任务的所有 IP
            task_in_ips = models.Assignment.objects.filter(task_belong=task)
            for ip in task_in_ips:
                ip_list.append(ip.name)
            task_all_dict = {'task_name': task.task_name.replace('+', '_'),
                             'task_count': count,
                             'task_allocated': task_allocated,
                             'task_num': task_num,
                             'task_upload': task_upload,
                             }
            # 这里设定为 10 是因为前端的页面的 js 文件中有十个选项，自然是希望页面颜色丰富一些，所以做一个随机选择吧
            if count >= 10:
                count = 1
            else:
                count += 1
            task_all_list.append(task_all_dict)
        # 对获取的 ip_list 进行处理，获取每个 ip 的获取数据集次数
        ip_value_lists = models.User.objects.values_list('IP', 'upload_times_today', 'upload_times').order_by(
            '-upload_times_today')
        # 给一个字典记录每一个 IP 的名字和次数
        upload_dict_list = []
        for ip_upload_info in ip_value_lists:
            upload_dict = {
                'IP': ip_upload_info[0],
                'upload_times_today': ip_upload_info[1],
                'upload_times': ip_upload_info[2],
            }
            upload_dict_list.append(upload_dict)
        # 规范化，将信息写入 context
        context = {
            'task_infos': task_info,
            'task_all': task_all_list,
            'task_upload': upload_dict_list,
        }
        return render(request, 'work/monitor_page/pages/Datacages_Homeindex.html', context)
    except Exception as e:
        print(e)
        messages.info(request, '数据并未进行分组操作，请进入后台查看')
    return redirect('error')


# 更新监控界面的数据,Datacages_Homeindes.html 中的 ajax 部分
def update_data_try(request):
    """
        规划一下这个函数的内容
        分成两个部分吧
            1.当前任务
                还没有分发的数据集 unallocated_data_sets
                已经分发出去的数据集 allocated_data_sets
                当前任务的分发进度
                    这个任务的数据集总数 task_original_num
                    已经分发出去的数据集数量 task_assignment_num
                    展现形式
                        task_assignment_num / task_original_num
                总体任务的分发进度
                    所有任务的数据集总数 task_all_original_num
            2.所有任务
                
    """
    # 当前任务
    """
            取得那些还没有被请求的数据
        """
    # 当前任务
    try:
        tasks_now = models.Task.objects.filter(task_over=False)
        # 获取长度，为了 ajax 使用
    except Exception as e:
        print(e)
        return redirect('error')
    task_info = []                  # 外层列表
    unallocated_data_sets_list = [] # 未分配的数据集
    allocated_data_sets_list = []   # 已经分配的数据集
    upload_number = 0               # 上传文件数量
    try:
        # 先获取那些还没有分配完毕的任务，首先从 Task 开始，寻找 assignment_over 的

        # 为什么不直接根据新设定的 assignment_over 这个字段来筛选所有的数据
        '''
            assignment_over 获取所有的此次任务的数据集
            再根据 status=True or False 来判断这个数据集是不是已经分配
        '''
        data_sets_for_today = models.Original.objects.filter(assignment_over=False).order_by('-created_date')
        assignment_all_number = data_sets_for_today.count()
        unallocated_num = 0
        for data_set in data_sets_for_today:
            if data_set.status:
                unallocated_num += 1
                unallocated_data_sets_list.append(data_set.data_set)
            else:
                allocated_data_set_dict = {
                    'data_set_name': data_set.data_set,
                    'IP': models.Assignment.objects.get(
                        data_set=models.Original.objects.get(data_set=data_set.data_set)).name,
                    'data_set_id': data_set.id,
                }
                allocated_data_sets_list.append(allocated_data_set_dict)
        allocated_num = assignment_all_number - unallocated_num
        for task in tasks_now:
            data_upload_the_task = models.DataUpload.objects.filter(task_belong=task)
            upload_number += data_upload_the_task.count()
            # 将上面的信息字典写入列表
            """
            包含几个键
                task                任务
                num_all             总数
                unallocated         未分配数据集
                unallocated_num     未分配数据集数量
                allocated           已分配数量
                ips                 参与 IP
            """
        task_detail = {'upload_num': upload_number,
                       'assignment_all': assignment_all_number,
                       'unallocated_data_sets': unallocated_data_sets_list,
                       'allocated_data_sets': allocated_data_sets_list,
                       'unallocated_num': unallocated_num,
                       'allocated_num': allocated_num,
                       }
        # 已分配数量，同上
        task_info.append(task_detail)
        # 重新写一个全部 task 的列表
        task_all_list = []
        # 参与的 IP 列表
        ip_list = []
        count = 1
        for task in tasks_now:
            # 每一个 Task 的数量
            task_allocated = models.Original.objects.filter(task_belong=task, status=False).count()
            task_upload = models.DataUpload.objects.filter(task_belong=task).count()
            # 参与该任务的所有 IP
            task_in_ips = models.Assignment.objects.filter(task_belong=task)
            for ip in task_in_ips:
                ip_list.append(ip.name)
            # 由于 js 不认这个加号，所以对 task_name 做一下处理，换成 _ 就可以
            task_all_dict = {'task_name': task.task_name.replace('+', '_'),
                             'task_count': count,
                             'task_allocated': task_allocated,
                             'task_num': assignment_all_number,
                             'task_upload': task_upload,
                             }
            # 这里设定为 10 是因为前端的页面的 js 文件中有十个选项，自然是希望页面颜色丰富一些，所以做一个随机选择吧
            if count >= 10:
                count = 1
            else:
                count += 1
            task_all_list.append(task_all_dict)
        # 对获取的 ip_list 进行处理，获取每个ip的获取数据集次数
        ip_value_lists = models.User.objects.values_list('IP', 'upload_times_today', 'upload_times').order_by(
            '-upload_times_today')
        # 给一个字典记录每一个 IP 的名字和次数
        upload_dict_list = []
        for ip_upload_info in ip_value_lists:
            upload_dict = {
                'IP': ip_upload_info[0],
                'upload_times_today': ip_upload_info[1],
                'upload_times': ip_upload_info[2],
            }
            upload_dict_list.append(upload_dict)
        # 规范化，将信息写入 context
        context = {
            'task_infos': task_info,
            'task_all': task_all_list,
            'task_upload': upload_dict_list,
        }
        return JsonResponse(context)
    except Exception as e:
        print(e)
        messages.info(request, '数据并未进行分组操作，请进入后台查看')
        return redirect('error')


# 压缩选择的所有函数，但是经过讨论，还是选择客户端上传函数文件清单，服务端检查缺少的部分并打包下载的方式，所以目前这个函数没有作用
def zip_choose_functions(modeladmin, request, queryset):
    # 获取需要打包的函数-
    functions_names = list(queryset)
    # 获取时间
    date_now = get_time(request, 1)
    # 所有函数文件的公共路径
    path_for_files = 'functions/'
    # 压缩文件的路径
    zip_path = 'functions/' + date_now + '/' + 'functions.zip'
    # count_use 用来计数成功压缩的文件数量
    count_use = 0
    # 遍历函数名
    for func_name in functions_names:
        
        # 生成该函数名对应的完成路径
        complete_path = path_for_files + str(func_name) + '.py'
        # 如果 count_use == 0 的话就意味着是刚开始，或者说遍历刚开始，由于咱们并不需要保留之前的压缩文件，第一次直接覆盖原文件，第二次mode = ‘a’
        # mode = ’a‘ 添加文件而不直接覆盖
        if count_use == 0:
            mode = 'w'
        else:
            mode = 'a'
        # success 用来记录是否成功进行这个函数任务
        success = True
        while success:
            # try 语句测试日期文件是否存在，某天的第一次生成压缩文件，因为没有相应的日期文件夹，就会报错，那么生成之后再次执行压缩
            try:
                with zipfile.ZipFile(zip_path, mode) as f:
                    try:
                        # 尝试打开该文件，如果报错说明没有
                        the_file = open(complete_path, 'rb')
                        f.write(complete_path)
                        count_use += 1
                        f.close()
                    except FileNotFoundError:
                        messages.info(request, '{}--该函数没有对应文件'.format(func_name))
                        f.close()
                    # 成功创建或者没有找到相关文件，都应该跳出 while 循环
                    success = False
            except FileNotFoundError:
                create_path_use = BASE_DIR + r'\functions'
                predict_file_name = './' + date_now
                os.mkdir(create_path_use + predict_file_name)
                messages.success(request, '成功创建日期文件夹')
    if count_use > 0:
        messages.success(request, '打包{}个函数成功'.format(count_use))
        return redirect('/admin/work/function')
    else:
        messages.error(request, '打包失败，函数没有对应文件，请检查或者重新上传')
        return redirect('/admin/work/function')


# 下载函数
def function_download(request):
    """
        规划一下这个函数的设计
        各个 IP 直接下载一个后台上传之后聚合而成的一个函数库文件作为各 IP 计算数据的函数来源
        各个 IP 直接覆盖原本目录下的相应函数文件——暂定为本地上为 functions.py
        各个 IP 拷贝的文件中另写一个函数用来申请得到最新的函数库文件
        现在的设计是这样子——各个 IP 上传一个函数文件清单，服务端检查缺少的部分并打包下载
    :param request:
    :return:
    """
    """
        现在根据 Task 来筛选，Task 相对数据和分配还有上传而言，数量更少，筛选起来快一些
    """
    response = {
        'status_code': 200,
        'msg': '',
        'fail_list': []
    }

    if request.method == 'GET':
        ip = request.GET.dict()['ip']
        # 获取今天需要进行分配工作的所有 Task 任务对应的函数
        functions_status_true = models.Function.objects.filter(status=True)
        # 将这些函数还原成为真实的文件路径，方便后面打包
        real_file_path_list = [
            str(provider_models.Provider.objects.get(provider_ip=func.provider_name).provider_ip).replace('.',
                                                                                                          '-') + '/' + str(
                func.func_capability_level) + '-' + func.func_name + '.py'
            for func in functions_status_true]

        # 所有函数文件的公共路径
        path_for_files = 'functions/'
        # 压缩文件的路径
        zip_path = 'functions/' + 'functions.zip'
        # 即刻创建一个空的压缩包，保证某一个 IP 的函数清单与服务端一样时压缩包没有在下方的遍历中创建的尴尬
        with zipfile.ZipFile(zip_path, 'w') as f:
            f.close()
        # count_use 用来计数成功压缩的文件数量
        count_use = 0
        # 遍历函数名
        for real_file_path in real_file_path_list:
            
            # 生成该函数名对应的完成路径
            complete_path = path_for_files + str(real_file_path)
            # 如果 count_use == 0 的话就意味着是刚开始，或者说遍历刚开始，由于咱们并不需要保留之前的压缩文件，第一次直接覆盖原文件，第二次 mode = ‘a’
            # mode = ’a‘ 添加文件而不直接覆盖
            if count_use == 0:
                mode = 'w'
            else:
                mode = 'a'
            # success 用来记录是否成功进行这个函数任务
            success = True
            while success:
                # try 语句测试日期文件是否存在，某天的第一次生成压缩文件，因为没有相应的日期文件夹，就会报错，那么生成之后再次执行压缩
                with zipfile.ZipFile(zip_path, mode) as f:
                    f.write(complete_path)
                    count_use += 1
                    f.close()
                    # 成功创建或者没有找到相关文件，都应该跳出 while 循环
                    success = False
        """ 
            写一个try来测试一下这个IP是不是已经注册过，粗暴一点，直接注册，报错就说明已经有了，就pass
        """
        try:
            models.User.objects.create(
                IP=ip,
            )
        except Exception:
            models.User.objects.filter(IP=ip).update(
                upload_times=0,
                status=True,
            )
        try:
            # FileResponse 写入
            response = FileResponse(open(zip_path, 'rb'))
            # stream 写入，让浏览器知道这是一个文件
            response['Content-Type'] = 'application/octet-stream'
            # 写入文件名
            response['Content-Disposition'] = 'attachment;filename="functions.zip"'
            # 相应的下载函数次数加一
            for file_path in real_file_path_list:
                provider = provider_models.Provider.objects.get(provider_ip=file_path.split('/')[0].replace('-', '.'))
                function_now = models.Function.objects.get(
                    func_name=file_path.split('/')[-1].split('.')[0].split('-')[1],
                    provider_name=str(provider.provider_ip))
                function_now.invoke_times += 1
                function_now.save()
            return response
        except FileNotFoundError:
            response['msg'] = 'FILE NOT FOUND'
            return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")


# 上传函数文件
def upload_function_file(request):
    response = {
        'status_code': 200,
        'msg': '',
        'fail_list': []
    }
    ip = request.POST.dict()['ip']
    if not provider_models.Provider.objects.filter(provider_ip=ip):
        response['status_code'] = 400
        response['msg'] = 'Sign First!'
        return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")
    ip_id = provider_models.Provider.objects.get(provider_ip=ip).pk
    # 拿到上传的文件
    file_for_upload = request.FILES.dict()
    # 检测文件是否存在
    if not file_for_upload:
        response['status_code'] = 400
        response['msg'] = 'FILE NOT FOUND'
        return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")
    # 给出路径，检测日期文件夹是否存在
    create_path_use = BASE_DIR + r'\functions'
    file_name = './' + str(ip).replace('.', '-')
    # 检查存在与否
    if not os.path.isdir(create_path_use + file_name):
        os.mkdir(create_path_use + file_name)

    for key in file_for_upload:
        if file_for_upload[key].name.split('.')[1] != 'py' or not file_for_upload[key].name.split('-')[0]:
            response['msg'] = 'FILE TYPE NOT RIGHT'
            response['fail_list'].append(file_for_upload[key].name)
            continue
        # 将文件放到 functions 文件夹下，该文件夹下有所有的函数文件和对应日期的日期文件夹，
        # 日期文件夹中存放的是当天打包好的函数文件压缩包
        test_exist_path = 'functions/' + str(ip).replace('.', '-') + '/' + '{}'.format(file_for_upload[key].name)
        """
            还是不判定是否已经存在相应的文件了，直接覆盖原来的函数文件就可以，
            客户端那里写清楚就可以了，没有必要多写那么多东西
        """
        the_upload_file = open(test_exist_path, 'wb')
        for chunk in file_for_upload[key].chunks():
            the_upload_file.write(chunk)
        the_upload_file.close()
        provider_models.File.objects.create(
            file_name=file_for_upload[key].name,
            provider_name=provider_models.Provider.objects.get(provider_ip=ip).provider_ip,
            task_status=TASK_STATUS[0],
            file_type=FILE_TYPE[0],
        )
    file_to_function(request, dir_name=str(ip).replace('.', '-'))
    response['status_code'] = 200
    response['msg'] = 'FUNCTION FILE UPLOAD SUCCESSFULLY'
    response['fail_list'] = []
    return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")


# 函数文件转化 function 实例
def file_to_function(request, dir_name, ):
    # dir_name 也就是 ip_id
    # 获取函数文件列表
    file_list = file_check('functions/{}'.format(dir_name), 2)
    # file_list_use 保存经过切分的文件名列表，
    file_list_use = [name.split('.')[0] for name in file_list]
    functions = models.Function.objects.filter(provider_name=request.POST.dict()['ip'])
    if functions:
        func_use = [func.func_name for func in functions]
        # 找出那些还没有被转化为 function 的文件
        unconverted_func_file = list(set(file_list_use) - set(func_use))
    else:
        unconverted_func_file = file_list_use
    for file_name in unconverted_func_file:
        # 检查一下是否已经存在该 IP 定义的同名函数
        try:
            models.Function.objects.get(provider_name=request.POST.dict()['ip'], func_name=file_name.split('-')[1])
            continue
        except Exception:
            pass
        # 逐一创建没有转换的函数
        models.Function.objects.create(
            func_name=file_name.split('-')[1],
            provider_name=request.POST.dict()['ip'],
            func_capability_level=int(file_name.split('-')[0]),
        )
    return True


# 以 0.5Mb 为基础，也就是文本处理类型的任务的每个数据集的大小应该是 0.5Mb， 小于的一个文件就是一个数据集，大于的就可以分成几个数据集
def read_in_chunks(file_path, chunk_size=1024 * 512):
    """
    Lazy function (generator) to read a file piece by piece.
    Default chunk size: 1M
    You can set your own chunk size
    """
    file_object = open(file_path)
    while True:
        chunk_data = file_object.read(chunk_size)
        if not chunk_data:
            break
        yield chunk_data


# 一个前期写的计时器，关于 timer 工具的
def print_time(request, inc, count):
    count += 1
    """
    Timer的参数说明
    inc: 表示时间的间隔
    print_time: 执行的函数
    （inc，）传递给执行函数的参数
    """
    t = Timer(inc, print_time, (inc, count))
    if count > 5:
        return redirect('site-home')
    else:
        pass
    t.start()


def date_set_timer(request):
    while True:
        # 为了解决数据集分配状态修改但是实际上没有创建 assignment 的尴尬局面，对所有 status=False 和 upload=False 的做处理
        error_data_sets = models.Original.objects.filter(status=False, upload=False)
        for error_data_set in error_data_sets:
            if not models.Assignment.objects.filter(
                    data_set=models.Original.objects.get(data_set=error_data_set.data_set)):
                error_data_set.status = True
                error_data_set.save()
        # 先判定一下是不是所有的任务都已经完成
        if models.Task.objects.filter(task_over=False):
            pass
        else:
            if not models.Task.objects.all():
                # 更新 timer_status.py 文件中的状态为 False
                status_file = open('work/timer_status.py', 'w', encoding='utf-8')
                status_file.write('TIMER_STATUS = False')
                update_to_cloud(request)
                return JsonResponse('TASK NOT FOUND! MAKE SURE YOU HAVE UPLOADED DATA FILE AND FUNCTION FILE!', safe=False)
        # 获取所有的分配总数，用于后面的匹配
        assignments = models.Assignment.objects.values_list().filter(upload=False)
        time_now = datetime.datetime.now()
        # 居然出现了一种还没有出现过的问题，assignment 没有记录，但是 original 显示已经分配了
        try:
            # 循环查询所有的分配，如果有超时，就删除
            for obj in assignments:
                # 获取该任务应该上传的时间
                upload_time = obj[6]
                if time_now > upload_time:
                    models.Assignment.objects.filter(pk=obj[0]).delete()
                    the = models.Original.objects.filter(pk=obj[4])
                    the.update(
                        status=True
                    )
                    models.User.objects.filter(IP=obj[1]).update(
                        status=True
                    )
            time.sleep(5)
        except:
            time.sleep(10)


# 存在一个问题，如何同步数据，先握个手把云端的任务列表和工作 IP 列表弄到手，做一下筛选吧
# 不如这样，我设计了一个 update_cloud 字段在 task 和注册 IP 中，根据这个筛选就完事
# 那么就等到 timer 循环结束，也就是所有的工作都完成得时候，做同步


# 同步数据到云网站上
def update_to_cloud(request):
    """
    更新内容包括task中的所有，更新的是update_cloud字段为False的所有的task
    任务名     任务创建时间      任务类型    任务数据集数量     函数名     上传IP
    """
    # 筛选出所有所有还没有上传的任务,写入字典
    not_update_to_cloud = models.Task.objects.filter(cloud_update=False).order_by('pk')
    dict_list = []
    for task in not_update_to_cloud:
        task_dict = {
            'task_name': task.task_name,
            'task_created_time': str(task.task_create_date),
            'task_data_sets_num': models.Original.objects.filter(task_belong__task_name=task.task_name).count(),
            'func_name': str(task.func_name),
            'provider': str(task.provider_name),
        }
        task.cloud_update = True
        task.save()
        dict_list.append(task_dict)
    # 同步参与计算的 IP 数据
    all_users = models.User.objects.filter(cloud_update=False)
    user_dict_list = []
    for user_one in all_users:
        user_dict_list.append({
            'user_name': str(user_one.IP),
            'times': user_one.upload_times,
            'user_capability_level': user_one.user_capability_level,
        })
        user_one.cloud_update = True
        user_one.save()
    all_list = [dict_list, user_dict_list]
    file_for_update = open('file_for_update.txt', 'w', encoding='utf-8')
    json.dump(all_list, file_for_update)
    file_for_update.close()
    files = {
        'file_for_update': open('file_for_update.txt', 'rb')
    }
    cloud_url = Site_model.objects.all().first().url
    response = requests.post(url=cloud_url, files=files)
    text = response.text
    data_dict = json.loads(text)
    return JsonResponse('success', safe=False)

# 各个按钮在后台的呈现名字
# 有用的
file_aggregate.short_description = u'文件聚合'
predict_download.short_description = u'下载预测'

# 没有用的
split_data_to_groups.short_description = u'数据分组'
zip_choose_functions.short_description = u'ZIP'
file_to_function.short_description = u'文件转函数'
