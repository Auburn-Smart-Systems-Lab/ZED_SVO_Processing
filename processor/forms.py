from django import forms
from .models import ExtractionJob

class ExtractionOptionsForm(forms.ModelForm):
    class Meta:
        model = ExtractionJob
        fields = [
            'extract_rgb_left',
            'extract_rgb_right',
            'extract_depth',
            'extract_point_cloud',
            'extract_confidence',
            'extract_normals',
            'extract_imu',
            'depth_mode',
            'frame_start',
            'frame_end',
            'frame_step',
        ]
        widgets = {
            'extract_rgb_left': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extract_rgb_right': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extract_depth': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extract_point_cloud': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extract_confidence': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extract_normals': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'extract_imu': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'depth_mode': forms.Select(attrs={'class': 'form-select'}),
            'frame_start': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'frame_end': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'frame_step': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
        }
        labels = {
            'extract_rgb_left': 'RGB Left Camera',
            'extract_rgb_right': 'RGB Right Camera',
            'extract_depth': 'Depth Maps',
            'extract_point_cloud': 'Point Clouds',
            'extract_confidence': 'Confidence Maps',
            'extract_normals': 'Normals Maps',
            'extract_imu': 'IMU Data',
            'depth_mode': 'Depth Mode',
            'frame_start': 'Start Frame',
            'frame_end': 'End Frame',
            'frame_step': 'Frame Step',
        }