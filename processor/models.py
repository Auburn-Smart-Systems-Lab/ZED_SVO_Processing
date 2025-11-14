from django.db import models
from django.utils import timezone
import os

class SVO2Upload(models.Model):
    file = models.FileField(upload_to='svo2_files/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    
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
        ('NEURAL', 'Neural'),
        ('ULTRA', 'Ultra'),
        ('QUALITY', 'Quality'),
        ('PERFORMANCE', 'Performance'),
    ]
    
    svo2_files = models.ManyToManyField(SVO2Upload)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Extraction options
    extract_rgb_left = models.BooleanField(default=False)
    extract_rgb_right = models.BooleanField(default=False)
    extract_depth = models.BooleanField(default=False)
    extract_point_cloud = models.BooleanField(default=False)
    extract_confidence = models.BooleanField(default=False)
    extract_normals = models.BooleanField(default=False)
    extract_imu = models.BooleanField(default=False)
    
    # Processing options
    depth_mode = models.CharField(max_length=20, choices=DEPTH_MODE_CHOICES, default='ULTRA')
    frame_start = models.IntegerField(default=0)
    frame_end = models.IntegerField(null=True, blank=True)
    frame_step = models.IntegerField(default=1)
    
    # Results
    output_path = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    progress = models.FloatField(default=0.0)
    
    def __str__(self):
        return f"Job {self.id} - {self.status}"

# NEW MODEL for tracking progress per file
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
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.svo2_file.filename} - {self.progress:.1f}%"

class ExtractionResult(models.Model):
    job = models.ForeignKey(ExtractionJob, on_delete=models.CASCADE, related_name='results')
    svo2_file = models.ForeignKey(SVO2Upload, on_delete=models.CASCADE)
    result_file = models.FileField(upload_to='extraction_results/')
    data_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.svo2_file.filename} - {self.data_type}"