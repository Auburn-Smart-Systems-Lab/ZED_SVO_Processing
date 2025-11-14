from django.contrib import admin
from .models import SVO2Upload, ExtractionJob, ExtractionResult, FileProgress

@admin.register(SVO2Upload)
class SVO2UploadAdmin(admin.ModelAdmin):
    list_display = ['filename', 'file_size', 'uploaded_at']
    search_fields = ['filename']
    list_filter = ['uploaded_at']

@admin.register(ExtractionJob)
class ExtractionJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'created_at', 'progress', 'depth_mode']
    list_filter = ['status', 'depth_mode', 'created_at']
    search_fields = ['id']
    readonly_fields = ['created_at', 'progress', 'error_message']

@admin.register(FileProgress)
class FileProgressAdmin(admin.ModelAdmin):
    list_display = ['svo2_file', 'job', 'status', 'progress', 'current_frame', 'total_frames']
    list_filter = ['status']
    search_fields = ['svo2_file__filename', 'job__id']

@admin.register(ExtractionResult)
class ExtractionResultAdmin(admin.ModelAdmin):
    list_display = ['job', 'svo2_file', 'data_type', 'created_at']
    list_filter = ['data_type', 'created_at']
    search_fields = ['job__id', 'svo2_file__filename']