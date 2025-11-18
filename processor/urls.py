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
    path('job/<int:job_id>/rerun/', views.rerun_job, name='rerun_job'),
    
    # File browsing
    path('job/<int:job_id>/browse/', views.browse_files, name='browse_files'),
    path('job/<int:job_id>/gallery/<str:category>/', views.gallery_view, name='gallery_view'),
    path('file/<int:file_id>/view/', views.view_file, name='view_file'),
    path('file/<int:file_id>/serve/', views.serve_extracted_file, name='serve_extracted_file'),
]