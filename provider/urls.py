from django.urls import path
from . import views


urlpatterns = [
    path('res_try', views.response_try, name='res_try'),
    path('qualify', views.qualify, name='qualify'),
    path('provide_file_upload', views.provide_file_upload, name='provide_file_upload'),
]
