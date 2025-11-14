from django import forms
from .models import ExtractionJob

# Remove SVO2UploadForm completely - we'll handle file uploads directly in the view

class ExtractionOptionsForm(forms.ModelForm):
    class Meta:
        model = ExtractionJob
        fields = [
            'extract_rgb_left', 'extract_rgb_right', 'extract_depth',
            'extract_point_cloud', 'extract_confidence', 'extract_normals',
            'extract_imu', 'depth_mode', 'frame_start', 'frame_end', 'frame_step'
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
            'frame_start': forms.NumberInput(attrs={'class': 'form-control'}),
            'frame_end': forms.NumberInput(attrs={'class': 'form-control'}),
            'frame_step': forms.NumberInput(attrs={'class': 'form-control'}),
        }