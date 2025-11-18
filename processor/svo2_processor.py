import pyzed.sl as sl
import cv2
import numpy as np
import os
import csv
from datetime import datetime

class SVO2Processor:
    def __init__(self, svo_path, output_dir, options):
        self.svo_path = svo_path
        self.output_dir = output_dir
        self.options = options
        self.camera = sl.Camera()
        self.extracted_files = []  # Track all extracted files
        
        # Create category subfolders
        self.folders = {}
        if options['extract_rgb_left']:
            self.folders['rgb_left'] = os.path.join(output_dir, '1_RGB_Left')
            os.makedirs(self.folders['rgb_left'], exist_ok=True)
        if options['extract_rgb_right']:
            self.folders['rgb_right'] = os.path.join(output_dir, '2_RGB_Right')
            os.makedirs(self.folders['rgb_right'], exist_ok=True)
        if options['extract_depth']:
            self.folders['depth'] = os.path.join(output_dir, '3_Depth')
            os.makedirs(self.folders['depth'], exist_ok=True)
        if options['extract_point_cloud']:
            self.folders['point_cloud'] = os.path.join(output_dir, '4_PointCloud')
            os.makedirs(self.folders['point_cloud'], exist_ok=True)
        if options['extract_confidence']:
            self.folders['confidence'] = os.path.join(output_dir, '5_Confidence')
            os.makedirs(self.folders['confidence'], exist_ok=True)
        if options['extract_normals']:
            self.folders['normals'] = os.path.join(output_dir, '6_Normals')
            os.makedirs(self.folders['normals'], exist_ok=True)
        if options['extract_imu']:
            self.folders['imu'] = os.path.join(output_dir, '7_IMU')
            os.makedirs(self.folders['imu'], exist_ok=True)
        
    def open(self):
        """Open the SVO file"""
        init_params = sl.InitParameters()
        init_params.set_from_svo_file(self.svo_path)
        init_params.svo_real_time_mode = False
        
        # Set depth mode
        depth_mode_map = {
            'PERFORMANCE': sl.DEPTH_MODE.PERFORMANCE,
            'QUALITY': sl.DEPTH_MODE.QUALITY,
            'ULTRA': sl.DEPTH_MODE.ULTRA,
            'NEURAL': sl.DEPTH_MODE.NEURAL
        }
        init_params.depth_mode = depth_mode_map.get(
            self.options.get('depth_mode', 'ULTRA'),
            sl.DEPTH_MODE.ULTRA
        )
        
        init_params.coordinate_units = sl.UNIT.METER
        
        status = self.camera.open(init_params)
        if status != sl.ERROR_CODE.SUCCESS:
            raise Exception(f"Failed to open SVO file: {status}")
        
        return True
    
    def get_total_frames(self):
        """Get total number of frames in the SVO file"""
        return self.camera.get_svo_number_of_frames()
    
    def process(self, progress_callback=None):
        """Process the SVO file and extract data"""
        total_frames = self.get_total_frames()
        frame_start = self.options.get('frame_start', 0)
        frame_end = self.options.get('frame_end', total_frames)
        frame_step = self.options.get('frame_step', 1)
        
        if frame_end is None or frame_end > total_frames:
            frame_end = total_frames
        
        # Set starting position
        self.camera.set_svo_position(frame_start)
        
        # Prepare data containers
        rgb_left = sl.Mat()
        rgb_right = sl.Mat()
        depth_map = sl.Mat()
        point_cloud = sl.Mat()
        confidence_map = sl.Mat()
        normals_map = sl.Mat()
        
        # IMU data storage
        imu_data_list = []
        
        runtime_params = sl.RuntimeParameters()
        
        current_frame = frame_start
        processed_count = 0
        
        while current_frame < frame_end:
            # Grab frame
            if self.camera.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
                # Check if we should process this frame
                if (current_frame - frame_start) % frame_step == 0:
                    frame_index = processed_count
                    
                    # Extract RGB Left
                    if self.options['extract_rgb_left']:
                        self.camera.retrieve_image(rgb_left, sl.VIEW.LEFT)
                        img_path = os.path.join(self.folders['rgb_left'], f'frame_{frame_index:06d}.jpg')
                        cv2.imwrite(img_path, rgb_left.get_data())
                        self.extracted_files.append({
                            'category': 'rgb_left',
                            'file_type': 'image',
                            'file_path': img_path,
                            'filename': f'frame_{frame_index:06d}.jpg',
                            'frame_number': frame_index,
                            'file_size': os.path.getsize(img_path)
                        })
                    
                    # Extract RGB Right
                    if self.options['extract_rgb_right']:
                        self.camera.retrieve_image(rgb_right, sl.VIEW.RIGHT)
                        img_path = os.path.join(self.folders['rgb_right'], f'frame_{frame_index:06d}.jpg')
                        cv2.imwrite(img_path, rgb_right.get_data())
                        self.extracted_files.append({
                            'category': 'rgb_right',
                            'file_type': 'image',
                            'file_path': img_path,
                            'filename': f'frame_{frame_index:06d}.jpg',
                            'frame_number': frame_index,
                            'file_size': os.path.getsize(img_path)
                        })
                    
                    # Extract Depth
                    if self.options['extract_depth']:
                        self.camera.retrieve_measure(depth_map, sl.MEASURE.DEPTH)
                        depth_data = depth_map.get_data()
                        
                        # Save raw depth as numpy
                        depth_path = os.path.join(self.folders['depth'], f'frame_{frame_index:06d}.npy')
                        np.save(depth_path, depth_data)
                        
                        # Save colorized depth as image
                        depth_viz = self._colorize_depth(depth_data)
                        depth_img_path = os.path.join(self.folders['depth'], f'frame_{frame_index:06d}.jpg')
                        cv2.imwrite(depth_img_path, depth_viz)
                        
                        self.extracted_files.append({
                            'category': 'depth',
                            'file_type': 'depth',
                            'file_path': depth_path,
                            'filename': f'frame_{frame_index:06d}.npy',
                            'frame_number': frame_index,
                            'file_size': os.path.getsize(depth_path)
                        })
                        self.extracted_files.append({
                            'category': 'depth',
                            'file_type': 'image',
                            'file_path': depth_img_path,
                            'filename': f'frame_{frame_index:06d}.jpg',
                            'frame_number': frame_index,
                            'file_size': os.path.getsize(depth_img_path)
                        })
                    
                    # Extract Point Cloud
                    if self.options['extract_point_cloud']:
                        self.camera.retrieve_measure(point_cloud, sl.MEASURE.XYZRGBA)
                        pc_data = point_cloud.get_data()
                        
                        # Save as PLY
                        ply_path = os.path.join(self.folders['point_cloud'], f'frame_{frame_index:06d}.ply')
                        self._save_point_cloud_ply(pc_data, ply_path)
                        
                        self.extracted_files.append({
                            'category': 'point_cloud',
                            'file_type': 'point_cloud',
                            'file_path': ply_path,
                            'filename': f'frame_{frame_index:06d}.ply',
                            'frame_number': frame_index,
                            'file_size': os.path.getsize(ply_path)
                        })
                    
                    # Extract Confidence
                    if self.options['extract_confidence']:
                        self.camera.retrieve_measure(confidence_map, sl.MEASURE.CONFIDENCE)
                        conf_data = confidence_map.get_data()
                        conf_img = (conf_data * 255).astype(np.uint8)
                        conf_path = os.path.join(self.folders['confidence'], f'frame_{frame_index:06d}.jpg')
                        cv2.imwrite(conf_path, conf_img)
                        
                        self.extracted_files.append({
                            'category': 'confidence',
                            'file_type': 'image',
                            'file_path': conf_path,
                            'filename': f'frame_{frame_index:06d}.jpg',
                            'frame_number': frame_index,
                            'file_size': os.path.getsize(conf_path)
                        })
                    
                    # Extract Normals
                    if self.options['extract_normals']:
                        self.camera.retrieve_measure(normals_map, sl.MEASURE.NORMALS)
                        normals_data = normals_map.get_data()
                        normals_vis = self._visualize_normals(normals_data)
                        normals_path = os.path.join(self.folders['normals'], f'frame_{frame_index:06d}.jpg')
                        cv2.imwrite(normals_path, normals_vis)
                        
                        self.extracted_files.append({
                            'category': 'normals',
                            'file_type': 'image',
                            'file_path': normals_path,
                            'filename': f'frame_{frame_index:06d}.jpg',
                            'frame_number': frame_index,
                            'file_size': os.path.getsize(normals_path)
                        })
                    
                    # Extract IMU data
                    if self.options['extract_imu']:
                        imu_data = sl.SensorsData()
                        if self.camera.get_sensors_data(imu_data, sl.TIME_REFERENCE.IMAGE) == sl.ERROR_CODE.SUCCESS:
                            imu_dict = {
                                'frame': frame_index,
                                'timestamp': imu_data.get_imu_data().timestamp.get_milliseconds(),
                                'orientation_x': imu_data.get_imu_data().get_pose().get_orientation().get()[0],
                                'orientation_y': imu_data.get_imu_data().get_pose().get_orientation().get()[1],
                                'orientation_z': imu_data.get_imu_data().get_pose().get_orientation().get()[2],
                                'orientation_w': imu_data.get_imu_data().get_pose().get_orientation().get()[3],
                                'angular_velocity_x': imu_data.get_imu_data().get_angular_velocity()[0],
                                'angular_velocity_y': imu_data.get_imu_data().get_angular_velocity()[1],
                                'angular_velocity_z': imu_data.get_imu_data().get_angular_velocity()[2],
                                'linear_acceleration_x': imu_data.get_imu_data().get_linear_acceleration()[0],
                                'linear_acceleration_y': imu_data.get_imu_data().get_linear_acceleration()[1],
                                'linear_acceleration_z': imu_data.get_imu_data().get_linear_acceleration()[2],
                            }
                            imu_data_list.append(imu_dict)
                    
                    processed_count += 1
                    
                    # Progress callback
                    if progress_callback:
                        progress = (current_frame - frame_start) / (frame_end - frame_start) * 100
                        progress_callback(progress, current_frame, total_frames)
                
                current_frame += 1
            else:
                break
        
        # Save IMU data to CSV
        if self.options['extract_imu'] and imu_data_list:
            csv_path = os.path.join(self.folders['imu'], 'imu_data.csv')
            with open(csv_path, 'w', newline='') as csvfile:
                fieldnames = imu_data_list[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(imu_data_list)
            
            self.extracted_files.append({
                'category': 'imu',
                'file_type': 'csv',
                'file_path': csv_path,
                'filename': 'imu_data.csv',
                'frame_number': None,
                'file_size': os.path.getsize(csv_path)
            })
        
        return processed_count
    
    def _colorize_depth(self, depth_data):
        """Colorize depth map for visualization"""
        depth_normalized = cv2.normalize(depth_data, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
        return depth_colored
    
    def _visualize_normals(self, normals_data):
        """Visualize normals map"""
        normals_vis = ((normals_data[:, :, :3] + 1.0) * 127.5).astype(np.uint8)
        return cv2.cvtColor(normals_vis, cv2.COLOR_RGB2BGR)
    
    def _save_point_cloud_ply(self, point_cloud_data, output_path):
        """Save point cloud as PLY file"""
        height, width, _ = point_cloud_data.shape
        
        with open(output_path, 'w') as f:
            # First pass: count valid points
            valid_points = 0
            for y in range(height):
                for x in range(width):
                    point = point_cloud_data[y, x]
                    # Check if point coordinates are valid (not NaN or Inf)
                    if (not np.isnan(point[0]) and not np.isinf(point[0]) and
                        not np.isnan(point[1]) and not np.isinf(point[1]) and
                        not np.isnan(point[2]) and not np.isinf(point[2]) and
                        not np.isnan(point[3]) and not np.isinf(point[3])):
                        valid_points += 1
            
            # Write PLY header
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write(f"element vertex {valid_points}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
            f.write("end_header\n")
            
            # Second pass: write valid point data
            for y in range(height):
                for x in range(width):
                    point = point_cloud_data[y, x]
                    # Check if all components are valid
                    if (not np.isnan(point[0]) and not np.isinf(point[0]) and
                        not np.isnan(point[1]) and not np.isinf(point[1]) and
                        not np.isnan(point[2]) and not np.isinf(point[2]) and
                        not np.isnan(point[3]) and not np.isinf(point[3])):
                        
                        x_coord, y_coord, z_coord = point[:3]
                        
                        # RGBA is packed in the 4th component
                        # Handle potential NaN in RGBA by defaulting to white
                        try:
                            rgba = int(point[3])
                            r = (rgba >> 16) & 0xFF
                            g = (rgba >> 8) & 0xFF
                            b = rgba & 0xFF
                        except (ValueError, OverflowError):
                            # Default to white if RGBA is invalid
                            r, g, b = 255, 255, 255
                        
                        f.write(f"{x_coord} {y_coord} {z_coord} {r} {g} {b}\n")
    
    def get_extracted_files(self):
        """Get list of all extracted files"""
        return self.extracted_files
    
    def close(self):
        """Close the camera"""
        self.camera.close()