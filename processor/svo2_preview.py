import pyzed.sl as sl
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import json

class SVO2Preview:
    def __init__(self, svo_path):
        self.svo_path = svo_path
        self.zed = sl.Camera()
        self.init_params = sl.InitParameters()
        self.init_params.set_from_svo_file(str(svo_path))
        self.init_params.svo_real_time_mode = False
        self.current_depth_mode = 'ULTRA'
        
    def set_depth_mode(self, mode_str):
        """Set depth mode for preview"""
        mode_map = {
            'NEURAL': sl.DEPTH_MODE.NEURAL,
            'ULTRA': sl.DEPTH_MODE.ULTRA,
            'QUALITY': sl.DEPTH_MODE.QUALITY,
            'PERFORMANCE': sl.DEPTH_MODE.PERFORMANCE,
        }
        self.init_params.depth_mode = mode_map.get(mode_str, sl.DEPTH_MODE.ULTRA)
        self.current_depth_mode = mode_str
        
    def open(self):
        err = self.zed.open(self.init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            raise Exception(f"Failed to open SVO file: {err}")
        return True
    
    def reopen_with_depth_mode(self, depth_mode):
        """Reopen camera with new depth mode"""
        self.close()
        self.set_depth_mode(depth_mode)
        return self.open()
    
    def get_total_frames(self):
        return self.zed.get_svo_number_of_frames()
    
    def get_frame(self, frame_number, view_type='rgb_left', depth_mode=None):
        """
        Get a specific frame as base64 encoded image
        view_type: 'rgb_left', 'rgb_right', 'depth', 'depth_viz', 'confidence', 'normals'
        """
        # Change depth mode if requested
        if depth_mode and depth_mode != self.current_depth_mode:
            self.reopen_with_depth_mode(depth_mode)
        
        self.zed.set_svo_position(frame_number)
        
        runtime_params = sl.RuntimeParameters()
        err = self.zed.grab(runtime_params)
        
        if err != sl.ERROR_CODE.SUCCESS:
            return None
        
        img_rgb = None
        
        if view_type == 'rgb_left':
            image = sl.Mat()
            self.zed.retrieve_image(image, sl.VIEW.LEFT)
            img_data = image.get_data()
            img_rgb = cv2.cvtColor(img_data, cv2.COLOR_BGRA2RGB)
            
        elif view_type == 'rgb_right':
            image = sl.Mat()
            self.zed.retrieve_image(image, sl.VIEW.RIGHT)
            img_data = image.get_data()
            img_rgb = cv2.cvtColor(img_data, cv2.COLOR_BGRA2RGB)
            
        elif view_type == 'depth' or view_type == 'depth_viz':
            depth_map = sl.Mat()
            self.zed.retrieve_measure(depth_map, sl.MEASURE.DEPTH)
            depth_data = depth_map.get_data()
            
            # Visualize depth
            depth_viz = depth_data.copy()
            depth_viz[np.isnan(depth_viz)] = 0
            depth_viz[np.isinf(depth_viz)] = 0
            
            if depth_viz.max() > 0:
                depth_normalized = cv2.normalize(depth_viz, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
            else:
                depth_normalized = np.zeros_like(depth_viz, dtype=np.uint8)
            
            depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
            img_rgb = cv2.cvtColor(depth_colored, cv2.COLOR_BGR2RGB)
            
        elif view_type == 'confidence':
            confidence_map = sl.Mat()
            self.zed.retrieve_measure(confidence_map, sl.MEASURE.CONFIDENCE)
            conf_data = confidence_map.get_data()
            
            # Visualize confidence (0-100)
            conf_normalized = cv2.normalize(conf_data, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
            conf_colored = cv2.applyColorMap(conf_normalized, cv2.COLORMAP_VIRIDIS)
            img_rgb = cv2.cvtColor(conf_colored, cv2.COLOR_BGR2RGB)
            
        elif view_type == 'normals':
            normals_map = sl.Mat()
            self.zed.retrieve_measure(normals_map, sl.MEASURE.NORMALS)
            normals_data = normals_map.get_data()
            
            # Visualize normals (convert XYZ to RGB)
            normals_viz = ((normals_data + 1) * 127.5).astype(np.uint8)
            img_rgb = normals_viz[:, :, :3]
            
        elif view_type == 'point_cloud':
            # Render point cloud as depth visualization for now
            depth_map = sl.Mat()
            self.zed.retrieve_measure(depth_map, sl.MEASURE.DEPTH)
            depth_data = depth_map.get_data()
            
            depth_viz = depth_data.copy()
            depth_viz[np.isnan(depth_viz)] = 0
            depth_viz[np.isinf(depth_viz)] = 0
            
            if depth_viz.max() > 0:
                depth_normalized = cv2.normalize(depth_viz, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
            else:
                depth_normalized = np.zeros_like(depth_viz, dtype=np.uint8)
            
            depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_TURBO)
            img_rgb = cv2.cvtColor(depth_colored, cv2.COLOR_BGR2RGB)
        
        if img_rgb is None:
            return None
        
        # Resize for web display
        height, width = img_rgb.shape[:2]
        max_width = 800
        if width > max_width:
            scale = max_width / width
            new_width = max_width
            new_height = int(height * scale)
            img_rgb = cv2.resize(img_rgb, (new_width, new_height))
        
        # Convert to JPEG
        pil_img = Image.fromarray(img_rgb)
        buffer = BytesIO()
        pil_img.save(buffer, format='JPEG', quality=90)
        
        # Encode as base64
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return img_base64
    
    def get_imu_data(self, frame_number):
        """Get IMU data for a specific frame"""
        self.zed.set_svo_position(frame_number)
        
        runtime_params = sl.RuntimeParameters()
        err = self.zed.grab(runtime_params)
        
        if err != sl.ERROR_CODE.SUCCESS:
            return None
        
        sensors_data = sl.SensorsData()
        self.zed.get_sensors_data(sensors_data, sl.TIME_REFERENCE.IMAGE)
        imu = sensors_data.get_imu_data()
        
        orientation = imu.get_pose().get_orientation().get()
        angular_vel = imu.get_angular_velocity()
        linear_acc = imu.get_linear_acceleration()
        
        return {
            'orientation': {
                'x': float(orientation[0]),
                'y': float(orientation[1]),
                'z': float(orientation[2]),
                'w': float(orientation[3])
            },
            'angular_velocity': {
                'x': float(angular_vel[0]),
                'y': float(angular_vel[1]),
                'z': float(angular_vel[2])
            },
            'linear_acceleration': {
                'x': float(linear_acc[0]),
                'y': float(linear_acc[1]),
                'z': float(linear_acc[2])
            },
            'timestamp': imu.timestamp.get_milliseconds()
        }
    
    def get_thumbnail(self):
        """Get thumbnail from middle of video"""
        total_frames = self.get_total_frames()
        middle_frame = total_frames // 2
        return self.get_frame(middle_frame, 'rgb_left')
    
    def close(self):
        self.zed.close()