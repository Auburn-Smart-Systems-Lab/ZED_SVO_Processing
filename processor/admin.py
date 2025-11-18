from django.contrib import admin
from .models import SVO2Upload, ExtractionJob, FileProgress, ExtractionResult, ExtractedFile

@admin.register(SVO2Upload)
class SVO2UploadAdmin(admin.ModelAdmin):
    list_display = ['filename', 'file_size', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['filename']
    readonly_fields = ['uploaded_at']

@admin.register(ExtractionJob)
class ExtractionJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'progress', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'depth_mode']
    search_fields = ['id']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['svo2_files']
    
    fieldsets = (
        ('Status', {
            'fields': ('status', 'progress', 'error_message')
        }),
        ('Extraction Options', {
            'fields': (
                'extract_rgb_left',
                'extract_rgb_right',
                'extract_depth',
                'extract_point_cloud',
                'extract_confidence',
                'extract_normals',
                'extract_imu',
            )
        }),
        ('Processing Options', {
            'fields': (
                'depth_mode',
                'frame_start',
                'frame_end',
                'frame_step',
            )
        }),
        ('Output', {
            'fields': ('output_path',)
        }),
        ('Files', {
            'fields': ('svo2_files',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(FileProgress)
class FileProgressAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'svo2_file', 'status', 'progress', 'current_frame', 'total_frames']
    list_filter = ['status']
    search_fields = ['svo2_file__filename']
    readonly_fields = ['current_frame', 'total_frames']

@admin.register(ExtractionResult)
class ExtractionResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'result_type', 'file_count']
    list_filter = ['result_type']
    search_fields = ['job__id', 'result_type']
    readonly_fields = ['file_path', 'file_count']

@admin.register(ExtractedFile)
class ExtractedFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'svo2_file', 'category', 'file_type', 'filename', 'frame_number', 'file_size', 'created_at']
    list_filter = ['category', 'file_type', 'created_at']
    search_fields = ['filename', 'job__id', 'svo2_file__filename']
    readonly_fields = ['created_at', 'file_size']
    
    fieldsets = (
        ('File Information', {
            'fields': ('job', 'svo2_file', 'category', 'file_type', 'filename', 'frame_number')
        }),
        ('File Details', {
            'fields': ('file_path', 'file_size', 'created_at')
        }),
    )