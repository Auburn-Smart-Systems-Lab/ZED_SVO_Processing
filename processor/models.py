from django.db import models
import os

class SVO2Upload(models.Model):
    file = models.FileField(upload_to='svo2_files/')
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.filename

class ExtractionJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    DEPTH_MODE_CHOICES = [
        ('PERFORMANCE', 'Performance'),
        ('QUALITY', 'Quality'),
        ('ULTRA', 'Ultra'),
        ('NEURAL', 'Neural'),
    ]
    
    svo2_files = models.ManyToManyField(SVO2Upload, related_name='jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.FloatField(default=0.0)
    
    # Extraction options
    extract_rgb_left = models.BooleanField(default=True)
    extract_rgb_right = models.BooleanField(default=False)
    extract_depth = models.BooleanField(default=True)
    extract_point_cloud = models.BooleanField(default=False)
    extract_confidence = models.BooleanField(default=False)
    extract_normals = models.BooleanField(default=False)
    extract_imu = models.BooleanField(default=False)
    
    # Processing options
    depth_mode = models.CharField(max_length=20, choices=DEPTH_MODE_CHOICES, default='ULTRA')
    frame_start = models.IntegerField(default=0)
    frame_end = models.IntegerField(null=True, blank=True)
    frame_step = models.IntegerField(default=1)
    
    # Output
    output_path = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Job {self.id} - {self.status}"

class FileProgress(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    job = models.ForeignKey(ExtractionJob, on_delete=models.CASCADE, related_name='file_progress')
    svo2_file = models.ForeignKey(SVO2Upload, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.FloatField(default=0.0)
    current_frame = models.IntegerField(default=0)
    total_frames = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.svo2_file.filename} - {self.progress}%"

class ExtractionResult(models.Model):
    job = models.ForeignKey(ExtractionJob, on_delete=models.CASCADE, related_name='results')
    result_type = models.CharField(max_length=50)
    file_path = models.CharField(max_length=500)
    file_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.job.id} - {self.result_type}"

class ExtractedFile(models.Model):
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('point_cloud', 'Point Cloud'),
        ('csv', 'CSV Data'),
        ('depth', 'Depth Data'),
    ]
    
    CATEGORY_CHOICES = [
        ('rgb_left', 'RGB Left'),
        ('rgb_right', 'RGB Right'),
        ('depth', 'Depth'),
        ('point_cloud', 'Point Cloud'),
        ('confidence', 'Confidence'),
        ('normals', 'Normals'),
        ('imu', 'IMU Data'),
    ]
    
    job = models.ForeignKey(ExtractionJob, on_delete=models.CASCADE, related_name='extracted_files')
    svo2_file = models.ForeignKey(SVO2Upload, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file_path = models.CharField(max_length=500)
    filename = models.CharField(max_length=255)
    frame_number = models.IntegerField(null=True, blank=True)
    file_size = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'frame_number', 'filename']
    
    def __str__(self):
        return f"{self.category} - {self.filename}"
    
    def get_relative_path(self):
        """Get path relative to MEDIA_ROOT"""
        from django.conf import settings
        if self.file_path.startswith(settings.MEDIA_ROOT):
            return self.file_path[len(settings.MEDIA_ROOT):].lstrip('/')
        return self.file_path