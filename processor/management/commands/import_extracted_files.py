from django.core.management.base import BaseCommand
from processor.models import ExtractedFile, ExtractionJob
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Import existing extracted files into database'

    def add_arguments(self, parser):
        parser.add_argument('job_id', type=int, help='Job ID to import files for')

    def handle(self, *args, **options):
        job_id = options['job_id']
        
        try:
            job = ExtractionJob.objects.get(id=job_id)
        except ExtractionJob.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Job {job_id} not found'))
            return
        
        # Get job directory
        output_base = os.path.join(settings.MEDIA_ROOT, 'extraction_results', f'job_{job_id}')
        
        if not os.path.exists(output_base):
            self.stdout.write(self.style.ERROR(f'Output directory not found: {output_base}'))
            return
        
        # Get all SVO2 files for this job
        svo2_files = job.svo2_files.all()
        
        total_imported = 0
        
        for svo_file in svo2_files:
            file_output_dir = os.path.join(output_base, f'file_{svo_file.id}_{svo_file.filename.replace(".svo2", "")}')
            
            if not os.path.exists(file_output_dir):
                continue
            
            # Scan subdirectories
            for root, dirs, files in os.walk(file_output_dir):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    file_size = os.path.getsize(file_path)
                    
                    # Determine category from directory name
                    dir_name = os.path.basename(root)
                    category = None
                    file_type = None
                    frame_number = None
                    
                    if 'RGB_Left' in dir_name or '1_RGB_Left' in dir_name:
                        category = 'rgb_left'
                        file_type = 'image'
                    elif 'RGB_Right' in dir_name or '2_RGB_Right' in dir_name:
                        category = 'rgb_right'
                        file_type = 'image'
                    elif 'Depth' in dir_name or '3_Depth' in dir_name:
                        category = 'depth'
                        if filename.endswith('.npy'):
                            file_type = 'depth'
                        else:
                            file_type = 'image'
                    elif 'PointCloud' in dir_name or '4_PointCloud' in dir_name:
                        category = 'point_cloud'
                        file_type = 'point_cloud'
                    elif 'Confidence' in dir_name or '5_Confidence' in dir_name:
                        category = 'confidence'
                        file_type = 'image'
                    elif 'Normals' in dir_name or '6_Normals' in dir_name:
                        category = 'normals'
                        file_type = 'image'
                    elif 'IMU' in dir_name or '7_IMU' in dir_name:
                        category = 'imu'
                        file_type = 'csv'
                    
                    if category:
                        # Extract frame number if present
                        if 'frame_' in filename:
                            try:
                                frame_number = int(filename.split('frame_')[1].split('.')[0])
                            except:
                                pass
                        
                        # Create database record
                        ExtractedFile.objects.get_or_create(
                            job=job,
                            svo2_file=svo_file,
                            file_path=file_path,
                            defaults={
                                'category': category,
                                'file_type': file_type,
                                'filename': filename,
                                'frame_number': frame_number,
                                'file_size': file_size
                            }
                        )
                        total_imported += 1
                        self.stdout.write(f"Imported: {category} - {filename}")
        
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {total_imported} files for job {job_id}'))