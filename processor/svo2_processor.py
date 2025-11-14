import pyzed.sl as sl
import cv2
import numpy as np
import os
from pathlib import Path

class SVO2Processor:
    def __init__(self, svo_path, output_dir):
        self.svo_path = svo_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.zed = sl.Camera()
        self.init_params = sl.InitParameters()
        self.init_params.set_from_svo_file(str(svo_path))
        self.init_params.svo_real_time_mode = False
        
    def set_depth_mode(self, mode_str):
        """Set depth mode: NEURAL, ULTRA, QUALITY, PERFORMANCE"""
        mode_map = {
            'NEURAL': sl.DEPTH_MODE.NEURAL,
            'ULTRA': sl.DEPTH_MODE.ULTRA,
            'QUALITY': sl.DEPTH_MODE.QUALITY,
            'PERFORMANCE': sl.DEPTH_MODE.PERFORMANCE,
        }
        self.init_params.depth_mode = mode_map.get(mode_str, sl.DEPTH_MODE.NEURAL)
    
    def open(self):
        err = self.zed.open(self.init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            raise Exception(f"Failed to open SVO file: {err}")
        return self.zed.get_camera_information().camera_configuration.fps
    
    def get_total_frames(self):
        """Get total number of frames in the SVO file"""
        return self.zed.get_svo_number_of_frames()
    
    def extract_frames(self, options, frame_start=0, frame_end=None, frame_step=1, progress_callback=None):
        """
        Extract data based on options dict with progress callbacks
        """
        runtime_params = sl.RuntimeParameters()
        
        # Prepare image containers
        image_left = sl.Mat()
        image_right = sl.Mat()
        depth_map = sl.Mat()
        point_cloud = sl.Mat()
        confidence_map = sl.Mat()
        normals_map = sl.Mat()
        
        total_frames = self.zed.get_svo_number_of_frames()
        if frame_end is None or frame_end > total_frames:
            frame_end = total_frames
        
        # Jump to start frame
        self.zed.set_svo_position(frame_start)
        
        imu_data_list = []
        extracted_frame_num = 0
        frames_to_process = (frame_end - frame_start) // frame_step
        
        for frame_idx in range(frame_start, frame_end, frame_step):
            err = self.zed.grab(runtime_params)
            if err != sl.ERROR_CODE.SUCCESS:
                break
            
            current_frame = self.zed.get_svo_position()
            
            # Extract RGB Left
            if options.get('rgb_left'):
                self.zed.retrieve_image(image_left, sl.VIEW.LEFT)
                img_left = image_left.get_data()
                cv2.imwrite(str(self.output_dir / f'rgb_left_{extracted_frame_num:06d}.png'), 
                           cv2.cvtColor(img_left, cv2.COLOR_RGBA2BGR))
            
            # Extract RGB Right
            if options.get('rgb_right'):
                self.zed.retrieve_image(image_right, sl.VIEW.RIGHT)
                img_right = image_right.get_data()
                cv2.imwrite(str(self.output_dir / f'rgb_right_{extracted_frame_num:06d}.png'),
                           cv2.cvtColor(img_right, cv2.COLOR_RGBA2BGR))
            
            # Extract Depth
            if options.get('depth'):
                self.zed.retrieve_measure(depth_map, sl.MEASURE.DEPTH)
                depth_data = depth_map.get_data()
                np.save(str(self.output_dir / f'depth_{extracted_frame_num:06d}.npy'), depth_data)
                
                # Also save visualization
                depth_viz = self.visualize_depth(depth_data)
                cv2.imwrite(str(self.output_dir / f'depth_{extracted_frame_num:06d}_viz.png'), depth_viz)
            
            # Extract Point Cloud
            if options.get('point_cloud'):
                self.zed.retrieve_measure(point_cloud, sl.MEASURE.XYZRGBA)
                pc_data = point_cloud.get_data()
                self.save_point_cloud(pc_data, self.output_dir / f'pointcloud_{extracted_frame_num:06d}.ply')
            
            # Extract Confidence
            if options.get('confidence'):
                self.zed.retrieve_measure(confidence_map, sl.MEASURE.CONFIDENCE)
                conf_data = confidence_map.get_data()
                np.save(str(self.output_dir / f'confidence_{extracted_frame_num:06d}.npy'), conf_data)
            
            # Extract Normals
            if options.get('normals'):
                self.zed.retrieve_measure(normals_map, sl.MEASURE.NORMALS)
                normals_data = normals_map.get_data()
                np.save(str(self.output_dir / f'normals_{extracted_frame_num:06d}.npy'), normals_data)
            
            # Extract IMU
            if options.get('imu'):
                sensors_data = sl.SensorsData()
                self.zed.get_sensors_data(sensors_data, sl.TIME_REFERENCE.IMAGE)
                imu = sensors_data.get_imu_data()
                imu_data_list.append({
                    'frame': extracted_frame_num,
                    'timestamp': imu.timestamp.get_milliseconds(),
                    'orientation': [imu.get_pose().get_orientation().get()],
                    'angular_velocity': [imu.get_angular_velocity()],
                    'linear_acceleration': [imu.get_linear_acceleration()],
                })
            
            extracted_frame_num += 1
            
            # Progress callback with current frame info
            if progress_callback:
                progress = (extracted_frame_num / frames_to_process) * 100
                progress_callback(progress, extracted_frame_num, frames_to_process)
        
        # Save IMU data if collected
        if imu_data_list:
            np.save(str(self.output_dir / 'imu_data.npy'), imu_data_list)
        
        return extracted_frame_num
    
    def visualize_depth(self, depth_data):
        """Create a colorized visualization of depth data"""
        depth_normalized = cv2.normalize(depth_data, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        return cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
    
    def save_point_cloud(self, pc_data, filepath):
        """Save point cloud as PLY file"""
        points = pc_data[:, :, :3].reshape(-1, 3)
        colors = pc_data[:, :, 3].reshape(-1, 1)
        
        # Extract RGB from packed RGBA
        colors_rgb = np.zeros((colors.shape[0], 3), dtype=np.uint8)
        colors_rgb[:, 0] = (colors[:, 0].view(np.uint32) >> 16) & 0xFF
        colors_rgb[:, 1] = (colors[:, 0].view(np.uint32) >> 8) & 0xFF
        colors_rgb[:, 2] = colors[:, 0].view(np.uint32) & 0xFF
        
        # Filter invalid points
        valid_mask = ~np.isnan(points).any(axis=1) & ~np.isinf(points).any(axis=1)
        points = points[valid_mask]
        colors_rgb = colors_rgb[valid_mask]
        
        # Write PLY
        with open(filepath, 'w') as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write(f"element vertex {len(points)}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
            f.write("end_header\n")
            
            for point, color in zip(points, colors_rgb):
                f.write(f"{point[0]} {point[1]} {point[2]} {color[0]} {color[1]} {color[2]}\n")
    
    def close(self):
        self.zed.close()