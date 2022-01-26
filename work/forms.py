from django import forms
from work.models import *
from django.contrib.auth.forms import UserCreationForm


class UserRegisterForm(forms.Form):
    IP = forms.GenericIPAddressField(label="IP", max_length=15,
                                     widget=forms.TextInput(attrs={'class': 'form-control'}))

    password = forms.CharField(label="密码", max_length=256,
                               widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    password2 = forms.CharField(label="确认新密码", max_length=256,
                                widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    email = forms.EmailField(label="邮箱地址",
                             widget=forms.EmailInput(attrs={'class': 'form-control'}))

    phone = forms.IntegerField(label="电话", widget=forms.NumberInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['IP', 'password', 'email', 'phone']


class UserForm(forms.Form):
    IP = forms.GenericIPAddressField(label="IP", max_length=15,
                                     widget=forms.TextInput(attrs={'class': 'form-control'}))

    password = forms.CharField(label="密码", max_length=256,
                               widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class JForm(forms.Form):
    comment1 = forms.CharField(label="评论", max_length=240,
                               widget=forms.Textarea(attrs={'class': 'form-control'}))


class RegisterForm(forms.Form):
    gender = (
        ('male', "男"),
        ('female', "女"),
    )

    password1 = forms.CharField(label="旧密码", max_length=256,
                                widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    password2 = forms.CharField(label="新密码", max_length=256,
                                widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    password3 = forms.CharField(label="确认新密码", max_length=256,
                                widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    email = forms.EmailField(label="邮箱地址",
                             widget=forms.EmailInput(attrs={'class': 'form-control'}))


