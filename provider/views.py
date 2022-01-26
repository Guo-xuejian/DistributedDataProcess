# -*- coding:utf-8 -*-
import pathlib
from django.shortcuts import render, redirect
import json
import os
from django.core import serializers

from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse
from . import models
from datetime import datetime
from work.views import get_ip, file_check


# 获取当前时间
def get_time(chose_part):
    """
    获取当前的时间
        datetime.now().strftime("%Y-%m-%d")
    :param chose_part:
    :param request:
    :return:
    """
    if chose_part == 1:
        time_now = datetime.now().strftime("%Y-%m-%d")
    elif chose_part == 2:
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elif chose_part == 3:
        time_now = datetime.now().strftime("%m-%d-%H")
    else:
        time_now = datetime.now().strftime("%Y-%m-%d-%H")
    return time_now


# 一个尝试函数
def response_try(request):
    if request.method == 'POST':
        the_dict = request.POST.dict()
        key_list = request.POST.dict().keys()
        print(key_list)
        print(type(key_list))
        print(list(key_list))
        for key in the_dict:
            print(the_dict[key])
    result = {
        'status_code': 200,
        'content': '成功',
    }
    return HttpResponse(json.dumps(result, ensure_ascii=False), content_type="application/json,charset=utf-8")


def qualify(request):
    allInfo = models.File.objects.all()
    the_all_transform = json.loads(serializers.serialize("json", allInfo))
    print(the_all_transform[:7])
    if request.method == 'POST':
        # 获取键的列表
        key_list = list(request.POST.dict().keys())
        # 如果 ip 和 name 都在，那么正常进行，不在的话说明没有正确上传需求，返回警告信息
        if 'ip' not in key_list or 'name' not in key_list:
            response = {
                'status_code': 400,
                'msg': 'We need the key "ip" and "name"',
                'you_dict_key(s)': key_list,
            }
            print('列表信息不全，无法创建')
            return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")
        # 说明正常,直接创建一个提供者用户
        try:
            models.Provider.objects.create(
                provider_ip=request.POST.dict()['ip'],
                provider_name=request.POST.dict()['name'],
            )
            response = {
                'status_code': 200,
                'msg': '成功创建账户!'
            }
        except IntegrityError:
            # 说明已经有过这个账户，返回报错信息
            response = {
                'status_code': 400,
                'msg': '该账户已经存在，请勿重复创建账户!',
            }
        return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")


# 一个提供者上传相应的函数文件的函数
def provide_func_upload(request):
    print(get_ip(request))
    if request.method == 'POST':
        response = {
            'status_code': 200,
            'msg': '',
            'fail_list': []
        }
        # 还是一样的，先检查有没有这个账号
        if not models.Provider.objects.filter(provider_ip=request.POST.dict()['ip']):
            response['status_code'] = 400
            response['msg'] = '该账户没有注册'
            return HttpResponse(json.dumps(response, ensure_ascii=False), content_type="application/json,charset=utf-8")
            # 拿到上传的文件
        upload_func_file = request.FILES.dict()
        for key in upload_func_file:
            if str(upload_func_file[key].name).split('.')[1] == 'py':
                response['fail_list'].append(upload_func_file[key].name)
            # else:
                # 将不符合上述条件的文件写入functions文件夹下指定日期的文件夹中，日期文件夹下以用户IP为下一级文件夹
    return redirect('site-home')


# 写一个上传数据文件的函数
def provide_file_upload(request):
    print(get_ip(request))
    if request.method == 'POST':
        # 先确定一下目前的这个ip是不是有相应的账户
        upload_ip = request.POST.dict()['ip']
        print(upload_ip)
        if not models.Provider.objects.filter(provider_ip=upload_ip):
            response = {
                'status_code': 400,
                'msg': '该账号还未注册!',
            }
            return HttpResponse(json.dumps(response, ensure_ascii=False),
                                content_type="application/json,charset=utf-8")
        response = {
            # 'status_code': 400,
            'msg': '',
            'fail_list': [],
        }
        # 拿到上传的文件
        upload_file = request.FILES.dict()
        for key in upload_file:
            print(upload_file[key].name)
            if str(upload_file[key].name).split('.')[1] not in ['txt', 'pkl']:
                response['fail_list'].append(upload_file[key].name)
            print(type(upload_file[key]))

        return HttpResponse(json.dumps(response, ensure_ascii=False),
                            content_type="application/json,charset=utf-8")

