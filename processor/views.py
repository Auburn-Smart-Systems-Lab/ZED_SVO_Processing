from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from .models import SVO2Upload, ExtractionJob, ExtractionResult, FileProgress
from .forms import ExtractionOptionsForm
from .tasks import process_svo2_files_sync
from .svo2_preview import SVO2Preview
from django.conf import settings
import os
import shutil
import threading
import json

def home(request):
    """Home page with upload form"""
    return render(request, 'processor/home.html')

def upload_files(request):
    """Handle multiple file uploads"""
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        
        if not files:
            messages.error(request, 'No files selected')
            return redirect('home')
        
        uploaded_ids = []
        for file in files:
            # Validate file extension
            if not file.name.endswith('.svo2'):
                messages.warning(request, f'{file.name} is not an SVO2 file, skipped')
                continue
            
            # Create upload record
            svo2_upload = SVO2Upload.objects.create(
                file=file,
                filename=file.name,
                file_size=file.size
            )
            uploaded_ids.append(svo2_upload.id)
        
        if uploaded_ids:
            messages.success(request, f'Successfully uploaded {len(uploaded_ids)} file(s)')
            # Store uploaded IDs in session for next step
            request.session['uploaded_ids'] = uploaded_ids
            return redirect('configure_extraction')
        else:
            messages.error(request, 'No valid SVO2 files uploaded')
            return redirect('home')
    
    return render(request, 'processor/upload.html')

def configure_extraction(request):
    """Configure extraction options for uploaded files"""
    uploaded_ids = request.session.get('uploaded_ids', [])
    
    if not uploaded_ids:
        messages.error(request, 'No files uploaded yet')
        return redirect('upload_files')
    
    uploaded_files = SVO2Upload.objects.filter(id__in=uploaded_ids)
    
    # Check if we're reconfiguring an existing job
    rerun_job_id = request.GET.get('rerun_job')
    initial_data = {}
    
    if rerun_job_id:
        try:
            rerun_job = ExtractionJob.objects.get(id=rerun_job_id)
            initial_data = {
                'extract_rgb_left': rerun_job.extract_rgb_left,
                'extract_rgb_right': rerun_job.extract_rgb_right,
                'extract_depth': rerun_job.extract_depth,
                'extract_point_cloud': rerun_job.extract_point_cloud,
                'extract_confidence': rerun_job.extract_confidence,
                'extract_normals': rerun_job.extract_normals,
                'extract_imu': rerun_job.extract_imu,
                'depth_mode': rerun_job.depth_mode,
                'frame_start': rerun_job.frame_start,
                'frame_end': rerun_job.frame_end,
                'frame_step': rerun_job.frame_step,
            }
            messages.info(request, f'Reconfiguring settings from Job #{rerun_job_id}')
        except ExtractionJob.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = ExtractionOptionsForm(request.POST)
        if form.is_valid():
            # Create extraction job
            job = form.save(commit=False)
            job.save()
            
            # Associate uploaded files with the job
            job.svo2_files.set(uploaded_files)
            
            # Clear session
            del request.session['uploaded_ids']
            
            # Start processing in background thread
            thread = threading.Thread(target=process_svo2_files_sync, args=(job.id,))
            thread.daemon = True
            thread.start()
            
            messages.success(request, f'Extraction job #{job.id} started')
            return redirect('job_status', job_id=job.id)
    else:
        form = ExtractionOptionsForm(initial=initial_data)
    
    return render(request, 'processor/configure.html', {
        'form': form,
        'uploaded_files': uploaded_files
    })

def rerun_job(request, job_id):
    """Rerun an existing job with potentially different settings"""
    job = get_object_or_404(ExtractionJob, id=job_id)
    
    # Get the files from the existing job
    svo2_files = job.svo2_files.all()
    
    if not svo2_files.exists():
        messages.error(request, 'No files found for this job')
        return redirect('job_list')
    
    # Store file IDs in session
    request.session['uploaded_ids'] = list(svo2_files.values_list('id', flat=True))
    
    # Redirect to configure with rerun parameter
    messages.info(request, f'Rerunning Job #{job_id} - Modify settings as needed')
    return redirect(f'/configure/?rerun_job={job_id}')

def preview_svo2_info(request, file_id):
    """Get SVO2 file information (total frames, etc.)"""
    svo_file = get_object_or_404(SVO2Upload, id=file_id)
    
    try:
        preview = SVO2Preview(svo_file.file.path)
        preview.open()
        
        total_frames = preview.get_total_frames()
        
        preview.close()
        
        return JsonResponse({
            'success': True,
            'filename': svo_file.filename,
            'total_frames': total_frames
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def preview_svo2_frame(request, file_id):
    """Get a specific frame from SVO2 file with different view types"""
    svo_file = get_object_or_404(SVO2Upload, id=file_id)
    frame_number = int(request.GET.get('frame', 0))
    view_type = request.GET.get('view_type', 'rgb_left')
    depth_mode = request.GET.get('depth_mode', 'ULTRA')
    
    try:
        preview = SVO2Preview(svo_file.file.path)
        preview.set_depth_mode(depth_mode)
        preview.open()
        
        total_frames = preview.get_total_frames()
        
        # Ensure frame number is valid
        if frame_number >= total_frames:
            frame_number = total_frames - 1
        if frame_number < 0:
            frame_number = 0
        
        img_base64 = preview.get_frame(frame_number, view_type, depth_mode)
        
        preview.close()
        
        if img_base64:
            return JsonResponse({
                'success': True,
                'image': f'data:image/jpeg;base64,{img_base64}',
                'frame': frame_number,
                'total_frames': total_frames,
                'view_type': view_type,
                'depth_mode': depth_mode
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to retrieve frame'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def preview_svo2_imu(request, file_id):
    """Get IMU data for a specific frame"""
    svo_file = get_object_or_404(SVO2Upload, id=file_id)
    frame_number = int(request.GET.get('frame', 0))
    
    try:
        preview = SVO2Preview(svo_file.file.path)
        preview.open()
        
        total_frames = preview.get_total_frames()
        
        if frame_number >= total_frames:
            frame_number = total_frames - 1
        if frame_number < 0:
            frame_number = 0
        
        imu_data = preview.get_imu_data(frame_number)
        
        preview.close()
        
        if imu_data:
            return JsonResponse({
                'success': True,
                'imu_data': imu_data,
                'frame': frame_number
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to retrieve IMU data'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def preview_svo2_thumbnail(request, file_id):
    """Get thumbnail for SVO2 file"""
    svo_file = get_object_or_404(SVO2Upload, id=file_id)
    
    try:
        preview = SVO2Preview(svo_file.file.path)
        preview.open()
        
        img_base64 = preview.get_thumbnail()
        
        preview.close()
        
        if img_base64:
            return JsonResponse({
                'success': True,
                'image': f'data:image/jpeg;base64,{img_base64}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to generate thumbnail'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def job_status(request, job_id):
    """View job status and results"""
    job = get_object_or_404(ExtractionJob, id=job_id)
    file_progress = job.file_progress.all()
    return render(request, 'processor/job_status.html', {
        'job': job,
        'file_progress': file_progress
    })

def job_progress(request, job_id):
    """AJAX endpoint for detailed job progress"""
    job = get_object_or_404(ExtractionJob, id=job_id)
    file_progress = job.file_progress.all()
    
    files_data = []
    for fp in file_progress:
        files_data.append({
            'filename': fp.svo2_file.filename,
            'status': fp.status,
            'progress': fp.progress,
            'current_frame': fp.current_frame,
            'total_frames': fp.total_frames,
            'error_message': fp.error_message
        })
    
    return JsonResponse({
        'status': job.status,
        'progress': job.progress,
        'error_message': job.error_message,
        'files': files_data
    })

def download_results(request, job_id):
    """Download extraction results as ZIP"""
    job = get_object_or_404(ExtractionJob, id=job_id)
    
    if job.status != 'completed':
        messages.error(request, 'Job not completed yet')
        return redirect('job_status', job_id=job_id)
    
    if not os.path.exists(job.output_path):
        messages.error(request, 'Result file not found')
        return redirect('job_status', job_id=job_id)
    
    response = FileResponse(open(job.output_path, 'rb'), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="job_{job_id}_results.zip"'
    return response

def job_list(request):
    """List all extraction jobs"""
    jobs = ExtractionJob.objects.all().order_by('-created_at')
    return render(request, 'processor/job_list.html', {'jobs': jobs})

def delete_job(request, job_id):
    """Delete a job and ALL its associated files"""
    job = get_object_or_404(ExtractionJob, id=job_id)
    
    deleted_files_count = 0
    deleted_dirs_count = 0
    
    try:
        # 1. Delete the output ZIP file
        if job.output_path and os.path.exists(job.output_path):
            os.remove(job.output_path)
            deleted_files_count += 1
        
        # 2. Delete the extraction results directory
        extraction_dir = os.path.join(settings.MEDIA_ROOT, 'extraction_results', f'job_{job_id}')
        if os.path.exists(extraction_dir):
            shutil.rmtree(extraction_dir)
            deleted_dirs_count += 1
        
        # 3. Get all uploaded SVO2 files associated with this job
        svo2_files = job.svo2_files.all()
        
        # 4. Delete the physical SVO2 files from disk
        for svo_file in svo2_files:
            if svo_file.file and os.path.exists(svo_file.file.path):
                os.remove(svo_file.file.path)
                deleted_files_count += 1
        
        # 5. Delete FileProgress records
        file_progress_count = job.file_progress.count()
        
        # 6. Delete ExtractionResult records
        extraction_results_count = job.results.count()
        
        # 7. Delete the SVO2Upload records
        svo2_files_count = svo2_files.count()
        svo2_files.delete()
        
        # 8. Finally, delete the job itself
        job.delete()
        
        messages.success(
            request, 
            f'Successfully deleted Job #{job_id}: '
            f'{deleted_files_count} files, {deleted_dirs_count} directories, '
            f'{svo2_files_count} SVO2 records'
        )
        
    except Exception as e:
        messages.error(request, f'Error deleting job: {str(e)}')
    
    return redirect('job_list')

# Add these imports at the top
from .models import ExtractedFile
import mimetypes

# Add these new views at the end of the file

def browse_files(request, job_id):
    """Browse extracted files for a job"""
    job = get_object_or_404(ExtractionJob, id=job_id)
    
    if job.status != 'completed':
        messages.warning(request, 'Job not completed yet')
        return redirect('job_status', job_id=job_id)
    
    # Debug: Check if files exist
    total_files = ExtractedFile.objects.filter(job=job).count()
    print(f"Total extracted files for job {job_id}: {total_files}")
    
    # Get all extracted files grouped by category
    categories = {}
    for category_value, category_label in ExtractedFile.CATEGORY_CHOICES:
        files = ExtractedFile.objects.filter(job=job, category=category_value).order_by('frame_number', 'filename')
        print(f"Category {category_value}: {files.count()} files")
        if files.exists():
            categories[category_value] = {
                'label': category_label,
                'files': files,
                'count': files.count()
            }
    
    print(f"Categories with files: {list(categories.keys())}")
    
    return render(request, 'processor/browse_files.html', {
        'job': job,
        'categories': categories
    })

def view_file(request, file_id):
    """View individual extracted file"""
    extracted_file = get_object_or_404(ExtractedFile, id=file_id)
    
    # Determine viewer type based on file type
    viewer_template = None
    file_data = None
    
    if extracted_file.file_type == 'image':
        viewer_template = 'processor/viewers/image_viewer.html'
    elif extracted_file.file_type == 'point_cloud':
        viewer_template = 'processor/viewers/pointcloud_viewer.html'
    elif extracted_file.file_type == 'csv':
        viewer_template = 'processor/viewers/csv_viewer.html'
        # Read CSV data
        import csv
        with open(extracted_file.file_path, 'r') as f:
            reader = csv.DictReader(f)
            file_data = list(reader)
    elif extracted_file.file_type == 'depth':
        viewer_template = 'processor/viewers/depth_viewer.html'
    
    return render(request, viewer_template, {
        'file': extracted_file,
        'file_data': file_data
    })

def serve_extracted_file(request, file_id):
    """Serve extracted file for viewing/downloading"""
    extracted_file = get_object_or_404(ExtractedFile, id=file_id)
    
    if not os.path.exists(extracted_file.file_path):
        return HttpResponse('File not found', status=404)
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(extracted_file.filename)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    response = FileResponse(open(extracted_file.file_path, 'rb'), content_type=content_type)
    
    # For images, display inline; for others, download
    if extracted_file.file_type == 'image':
        response['Content-Disposition'] = f'inline; filename="{extracted_file.filename}"'
    else:
        response['Content-Disposition'] = f'attachment; filename="{extracted_file.filename}"'
    
    return response

def gallery_view(request, job_id, category):
    """Gallery view for a specific category"""
    job = get_object_or_404(ExtractionJob, id=job_id)
    files = ExtractedFile.objects.filter(job=job, category=category).order_by('frame_number', 'filename')
    
    category_label = dict(ExtractedFile.CATEGORY_CHOICES).get(category, category)
    
    return render(request, 'processor/gallery.html', {
        'job': job,
        'category': category,
        'category_label': category_label,
        'files': files
    })