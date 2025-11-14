from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_files, name='upload_files'),
    path('configure/', views.configure_extraction, name='configure_extraction'),
    path('jobs/', views.job_list, name='job_list'),
    path('job/<int:job_id>/', views.job_status, name='job_status'),
    path('job/<int:job_id>/progress/', views.job_progress, name='job_progress'),
    path('job/<int:job_id>/download/', views.download_results, name='download_results'),
    path('job/<int:job_id>/delete/', views.delete_job, name='delete_job'),
]