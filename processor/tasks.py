from .models import ExtractionJob, FileProgress, ExtractedFile, SVO2Upload
from .svo2_processor import SVO2Processor
from django.conf import settings
import os
import zipfile
import shutil

def process_svo2_files_sync(job_id):
    """Process SVO2 files synchronously"""
    try:
        job = ExtractionJob.objects.get(id=job_id)
        job.status = 'processing'
        job.save()
        
        svo2_files = job.svo2_files.all()
        total_files = svo2_files.count()
        
        # Create output directory
        output_base = os.path.join(settings.MEDIA_ROOT, 'extraction_results', f'job_{job_id}')
        os.makedirs(output_base, exist_ok=True)
        
        for idx, svo_file in enumerate(svo2_files):
            # Create or get file progress
            file_progress, created = FileProgress.objects.get_or_create(
                job=job,
                svo2_file=svo_file,
                defaults={'status': 'processing'}
            )
            file_progress.status = 'processing'
            file_progress.save()
            
            try:
                # Create output directory for this file
                file_output_dir = os.path.join(output_base, f'file_{svo_file.id}_{svo_file.filename.replace(".svo2", "")}')
                os.makedirs(file_output_dir, exist_ok=True)
                
                # Prepare extraction options
                options = {
                    'extract_rgb_left': job.extract_rgb_left,
                    'extract_rgb_right': job.extract_rgb_right,
                    'extract_depth': job.extract_depth,
                    'extract_point_cloud': job.extract_point_cloud,
                    'extract_confidence': job.extract_confidence,
                    'extract_normals': job.extract_normals,
                    'extract_imu': job.extract_imu,
                    'depth_mode': job.depth_mode,
                    'frame_start': job.frame_start,
                    'frame_end': job.frame_end,
                    'frame_step': job.frame_step,
                }
                
                # Initialize processor
                processor = SVO2Processor(svo_file.file.path, file_output_dir, options)
                processor.open()
                
                total_frames = processor.get_total_frames()
                file_progress.total_frames = total_frames
                file_progress.save()
                
                # Progress callback
                def progress_callback(progress, current_frame, total):
                    file_progress.progress = progress
                    file_progress.current_frame = current_frame
                    file_progress.save()
                    
                    # Update overall job progress
                    overall_progress = ((idx + (progress / 100)) / total_files) * 100
                    job.progress = overall_progress
                    job.save()
                
                # Process the file
                processor.process(progress_callback=progress_callback)
                
                # Save extracted files to database
                extracted_files_data = processor.get_extracted_files()
                print(f"Saving {len(extracted_files_data)} extracted files to database...")
                
                for file_data in extracted_files_data:
                    ExtractedFile.objects.create(
                        job=job,
                        svo2_file=svo_file,
                        category=file_data['category'],
                        file_type=file_data['file_type'],
                        file_path=file_data['file_path'],
                        filename=file_data['filename'],
                        frame_number=file_data['frame_number'],
                        file_size=file_data['file_size']
                    )
                    print(f"Saved: {file_data['category']} - {file_data['filename']}")
                
                processor.close()
                
                file_progress.status = 'completed'
                file_progress.progress = 100.0
                file_progress.save()
                
                print(f"Completed processing {svo_file.filename}")
                
            except Exception as e:
                print(f"Error processing {svo_file.filename}: {str(e)}")
                import traceback
                traceback.print_exc()
                file_progress.status = 'failed'
                file_progress.error_message = str(e)
                file_progress.save()
                raise
        
        # Create ZIP file
        print("Creating ZIP file...")
        zip_path = os.path.join(settings.MEDIA_ROOT, 'extraction_results', f'job_{job_id}_results.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_base):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_base)
                    zipf.write(file_path, arcname)
        
        print(f"ZIP created at: {zip_path}")
        
        job.output_path = zip_path
        job.status = 'completed'
        job.progress = 100.0
        job.save()
        
        # Verify database records
        extracted_count = ExtractedFile.objects.filter(job=job).count()
        print(f"Total extracted files in database: {extracted_count}")
        
    except Exception as e:
        print(f"Job {job_id} failed: {str(e)}")
        import traceback
        traceback.print_exc()
        job.status = 'failed'
        job.error_message = str(e)
        job.save()