from django.urls import path
from . import views


urlpatterns = [
    path('', views.home_try, name='site-home'),
    path('dashboard', views.home_try, name='dashboard'),
    path('error', views.error, name='error'),
    path('get_data', views.get_data, name='get_data'),
    path('upload', views.upload, name='upload'),
    path('data_download', views.data_download, name='data_download'),
    path('check_timeout', views.check_timeout, name='check_timeout'),
    path('file_aggregate', views.file_aggregate, name='file_aggregate'),
    path('upload_data_file', views.upload_data_file, name='upload_data_file'),
    path('predict_download', views.predict_download, name='predict_download'),
    path('update_data', views.update_data, name='update_data'),
    path('update_data_try', views.update_data_try, name='update_data_try'),
    path('create_function_dir', views.create_function_dir, name='create_function_dir'),
    path('upload_function_file', views.upload_function_file, name='upload_function_file'),
    path('file_to_function', views.file_to_function, name='file_to_function'),
    path('function_download', views.function_download, name='function_download'),
    path('update_to_cloud', views.update_to_cloud, name='update_to_cloud'),
    # 测试使用
    path('timer', views.date_set_timer, name='timer'),
    path('delete_all', views.delete_all, name='delete_all'),
]
