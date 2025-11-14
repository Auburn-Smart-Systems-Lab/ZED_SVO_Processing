from .models import ExtractionJob, SVO2Upload, ExtractionResult, FileProgress
from .svo2_processor import SVO2Processor
from django.conf import settings
from django.utils import timezone
import os
import zipfile

def process_svo2_files_sync(job_id):
    """
    Synchronous processing with per-file progress tracking
    """
    try:
        job = ExtractionJob.objects.get(id=job_id)
        job.status = 'processing'
        job.save()
        
        # Create output directory
        output_base = os.path.join(settings.MEDIA_ROOT, 'extraction_results', f'job_{job_id}')
        os.makedirs(output_base, exist_ok=True)
        
        # Get extraction options
        options = {
            'rgb_left': job.extract_rgb_left,
            'rgb_right': job.extract_rgb_right,
            'depth': job.extract_depth,
            'point_cloud': job.extract_point_cloud,
            'confidence': job.extract_confidence,
            'normals': job.extract_normals,
            'imu': job.extract_imu,
        }
        
        svo2_files = job.svo2_files.all()
        total_files = svo2_files.count()
        
        # Create FileProgress entries for each file
        for svo_file in svo2_files:
            FileProgress.objects.create(
                job=job,
                svo2_file=svo_file,
                status='pending'
            )
        
        # Process each file
        for idx, svo_file in enumerate(svo2_files):
            # Get the FileProgress object
            file_progress = FileProgress.objects.get(job=job, svo2_file=svo_file)
            file_progress.status = 'processing'
            file_progress.started_at = timezone.now()
            file_progress.save()
            
            try:
                file_output_dir = os.path.join(output_base, svo_file.filename.replace('.svo2', ''))
                os.makedirs(file_output_dir, exist_ok=True)
                
                # Process the file
                processor = SVO2Processor(svo_file.file.path, file_output_dir)
                processor.set_depth_mode(job.depth_mode)
                processor.open()
                
                # Get total frames
                total_frames = processor.get_total_frames()
                file_progress.total_frames = total_frames
                file_progress.save()
                
                def update_progress(frame_progress, current_frame, total_frames_to_process):
                    # Update file-specific progress
                    file_progress.progress = frame_progress
                    file_progress.current_frame = current_frame
                    file_progress.save()
                    
                    # Update overall job progress
                    file_weight = (idx / total_files) * 100
                    current_file_contribution = (frame_progress / total_files)
                    job.progress = file_weight + current_file_contribution
                    job.save()
                
                processor.extract_frames(
                    options,
                    frame_start=job.frame_start,
                    frame_end=job.frame_end,
                    frame_step=job.frame_step,
                    progress_callback=update_progress
                )
                processor.close()
                
                # Mark file as completed
                file_progress.status = 'completed'
                file_progress.progress = 100.0
                file_progress.completed_at = timezone.now()
                file_progress.save()
                
            except Exception as e:
                file_progress.status = 'failed'
                file_progress.error_message = str(e)
                file_progress.save()
                raise
        
        # Zip the results
        zip_path = os.path.join(settings.MEDIA_ROOT, 'extraction_results', f'job_{job_id}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_base):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_base)
                    zipf.write(file_path, arcname)
        
        job.output_path = zip_path
        job.status = 'completed'
        job.progress = 100.0
        job.save()
        
    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.save()