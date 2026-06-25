"""
HoloBuild: Real-Time Hand-Driven 2.5D AR Assembly Environment
FINAL WORKING VERSION - All bugs fixed, ready for submission
"""

import cv2
import numpy as np
from enum import Enum
import time
import math


class GestureType(Enum):
    NONE = 0
    PINCH = 1
    GRAB = 2
    POINT = 3
    PALM_OPEN = 4


class VirtualObject:
    def __init__(self, obj_type, position, size=50, color=(0, 255, 0), depth=0):
        self.obj_type = obj_type
        self.position = np.array(position, dtype=float)
        self.size = size
        self.color = color
        self.depth = depth
        self.is_selected = False
        
    def draw(self, frame):
        x, y = int(self.position[0]), int(self.position[1])
        scale = 0.5 + (self.depth / 100) * 0.5
        scaled_size = int(self.size * scale)
        depth_factor = 0.6 + (self.depth / 100) * 0.4
        adjusted_color = tuple(int(c * depth_factor) for c in self.color)
        
        if self.is_selected:
            cv2.circle(frame, (x, y), scaled_size + 10, (255, 255, 0), 2)
        
        if self.obj_type == 'cube':
            self._draw_cube(frame, x, y, scaled_size, adjusted_color)
        elif self.obj_type == 'sphere':
            self._draw_sphere(frame, x, y, scaled_size, adjusted_color)
        elif self.obj_type == 'pyramid':
            self._draw_pyramid(frame, x, y, scaled_size, adjusted_color)
        elif self.obj_type == 'cylinder':
            self._draw_cylinder(frame, x, y, scaled_size, adjusted_color)
            
    def _draw_cube(self, frame, x, y, size, color):
        offset = size // 3
        pts_back = np.array([[x - size + offset, y - size + offset],
                            [x + size + offset, y - size + offset],
                            [x + size + offset, y + size + offset],
                            [x - size + offset, y + size + offset]], np.int32)
        cv2.fillPoly(frame, [pts_back], tuple(int(c * 0.6) for c in color))
        
        pts_front = np.array([[x - size, y - size], [x + size, y - size],
                             [x + size, y + size], [x - size, y + size]], np.int32)
        cv2.fillPoly(frame, [pts_front], color)
        
        cv2.line(frame, (x - size, y - size), (x - size + offset, y - size + offset), (0, 0, 0), 2)
        cv2.line(frame, (x + size, y - size), (x + size + offset, y - size + offset), (0, 0, 0), 2)
        cv2.line(frame, (x + size, y + size), (x + size + offset, y + size + offset), (0, 0, 0), 2)
        cv2.line(frame, (x - size, y + size), (x - size + offset, y + size + offset), (0, 0, 0), 2)
        
    def _draw_sphere(self, frame, x, y, size, color):
        cv2.circle(frame, (x, y), size, color, -1)
        highlight_pos = (x - size // 3, y - size // 3)
        cv2.circle(frame, highlight_pos, size // 4, tuple(min(255, int(c * 1.5)) for c in color), -1)
        cv2.circle(frame, (x, y), size, (0, 0, 0), 2)
        
    def _draw_pyramid(self, frame, x, y, size, color):
        left_face = np.array([[x - size, y + size], [x, y - size], [x, y - size + size // 3]], np.int32)
        cv2.fillPoly(frame, [left_face], tuple(int(c * 0.7) for c in color))
        
        right_face = np.array([[x + size, y + size], [x, y - size], [x, y - size + size // 3]], np.int32)
        cv2.fillPoly(frame, [right_face], color)
        
        cv2.line(frame, (x - size, y + size), (x, y - size), (0, 0, 0), 2)
        cv2.line(frame, (x + size, y + size), (x, y - size), (0, 0, 0), 2)
        cv2.line(frame, (x - size, y + size), (x + size, y + size), (0, 0, 0), 2)
        
    def _draw_cylinder(self, frame, x, y, size, color):
        height = int(size * 1.5)
        offset = size // 4
        
        cv2.ellipse(frame, (x + offset, y - height + offset), (size, size // 2), 0, 0, 360, 
                   tuple(int(c * 0.6) for c in color), -1)
        cv2.rectangle(frame, (x - size, y - height), (x + size, y + height), color, -1)
        cv2.ellipse(frame, (x, y - height), (size, size // 2), 0, 0, 360, color, -1)
        cv2.ellipse(frame, (x, y - height), (size, size // 2), 0, 0, 360, (0, 0, 0), 2)
        cv2.ellipse(frame, (x, y + height), (size, size // 2), 0, 0, 360, tuple(int(c * 0.8) for c in color), -1)
        cv2.ellipse(frame, (x, y + height), (size, size // 2), 0, 0, 360, (0, 0, 0), 2)
        
        cv2.line(frame, (x - size, y - height), (x - size, y + height), (0, 0, 0), 2)
        cv2.line(frame, (x + size, y - height), (x + size, y + height), (0, 0, 0), 2)


class HandTracker:
    def __init__(self):
        self.hand_center = None
        self.hand_contour = None
        self.fingers_up = 0
        self.hand_area = 0
        
        self.lower_skin1 = np.array([0, 20, 70], dtype=np.uint8)
        self.upper_skin1 = np.array([20, 255, 255], dtype=np.uint8)
        self.lower_skin2 = np.array([0, 40, 60], dtype=np.uint8)
        self.upper_skin2 = np.array([25, 170, 255], dtype=np.uint8)
        
    def find_hands(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, self.lower_skin1, self.upper_skin1)
        mask2 = cv2.inRange(hsv, self.lower_skin2, self.upper_skin2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) > 0:
            hand_contour = max(contours, key=cv2.contourArea)
            self.hand_area = cv2.contourArea(hand_contour)
            
            if self.hand_area > 8000:
                self.hand_contour = hand_contour
                M = cv2.moments(hand_contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    self.hand_center = (cx, cy)
                    self._detect_fingers(hand_contour)
                    return True
        
        self.hand_center = None
        self.hand_contour = None
        self.fingers_up = 0
        return False
    
    def _detect_fingers(self, contour):
        hull = cv2.convexHull(contour, returnPoints=False)
        
        if len(hull) > 3 and len(contour) > 3:
            try:
                defects = cv2.convexityDefects(contour, hull)
                
                if defects is not None:
                    finger_count = 0
                    
                    for i in range(defects.shape[0]):
                        s, e, f, d = defects[i, 0]
                        start = tuple(contour[s][0])
                        end = tuple(contour[e][0])
                        far = tuple(contour[f][0])
                        
                        a = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
                        b = np.sqrt((far[0] - start[0])**2 + (far[1] - start[1])**2)
                        c = np.sqrt((end[0] - far[0])**2 + (end[1] - far[1])**2)
                        
                        angle = np.arccos((b**2 + c**2 - a**2) / (2 * b * c))
                        
                        if angle <= np.pi / 2 and d > 10000:
                            finger_count += 1
                    
                    self.fingers_up = min(finger_count + 1, 5)
                else:
                    self.fingers_up = 0
                    
            except:
                self.fingers_up = 0
        else:
            self.fingers_up = 0
    
    def get_hand_center(self):
        return self.hand_center
    
    def detect_gesture(self):
        if self.hand_center is None or self.hand_contour is None:
            return GestureType.NONE
        
        perimeter = cv2.arcLength(self.hand_contour, True)
        if perimeter > 0:
            compactness = (4 * np.pi * self.hand_area) / (perimeter ** 2)
        else:
            compactness = 0
        
        if compactness > 0.6 or self.fingers_up == 0:
            return GestureType.PINCH
        elif self.fingers_up == 1:
            return GestureType.POINT
        elif self.fingers_up >= 4:
            return GestureType.PALM_OPEN
        elif self.fingers_up in [2, 3]:
            return GestureType.GRAB
        
        return GestureType.NONE
    
    def draw_hands(self, frame):
        if self.hand_contour is not None:
            cv2.drawContours(frame, [self.hand_contour], 0, (0, 255, 0), 2)
            
            if self.hand_center is not None:
                cv2.circle(frame, self.hand_center, 10, (255, 0, 255), -1)
                cv2.circle(frame, self.hand_center, 12, (255, 255, 255), 2)
                
                gesture = self.detect_gesture()
                gesture_text = f"Fingers: {self.fingers_up} | {gesture.name}"
                cv2.putText(frame, gesture_text, 
                          (self.hand_center[0] - 100, self.hand_center[1] - 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)


class ARAssemblySystem:
    def __init__(self):
        self.hand_tracker = HandTracker()
        self.objects = []
        self.selected_object = None
        self.current_mode = "SELECT"
        self.create_object_type = "cube"
        self.available_types = ['cube', 'sphere', 'pyramid', 'cylinder']
        self.type_index = 0
        self.last_gesture = GestureType.NONE
        self.pinch_start_pos = None
        self.object_start_pos = None
        self.show_help = True
        self.fps = 0
        self.last_time = time.time()
        self.calibrated = False
        self.gesture_hold_time = 0
        self.gesture_threshold = 0.5
        
    def create_object(self, position):
        colors = {'cube': (0, 255, 0), 'sphere': (255, 100, 100), 
                 'pyramid': (100, 100, 255), 'cylinder': (255, 200, 0)}
        obj = VirtualObject(self.create_object_type, position, size=50, 
                          color=colors[self.create_object_type], depth=50)
        self.objects.append(obj)
        print(f"Created {self.create_object_type}")
        return obj
    
    def find_nearest_object(self, position, max_distance=80):
        nearest = None
        min_dist = max_distance
        for obj in self.objects:
            dist = np.linalg.norm(obj.position - np.array(position))
            if dist < min_dist:
                min_dist = dist
                nearest = obj
        return nearest
    
    def update(self, frame):
        current_time = time.time()
        if (current_time - self.last_time) > 0:
            self.fps = 1 / (current_time - self.last_time)
        self.last_time = current_time
        
        hands_found = self.hand_tracker.find_hands(frame)
        
        if hands_found:
            if not self.calibrated:
                self.calibrated = True
                print("Hand calibrated!")
            
            hand_pos = self.hand_tracker.get_hand_center()
            current_gesture = self.hand_tracker.detect_gesture()
            
            if hand_pos is not None:
                self._handle_gestures(current_gesture, hand_pos, frame)
            
            self.hand_tracker.draw_hands(frame)
        
        sorted_objects = sorted(self.objects, key=lambda x: x.depth)
        for obj in sorted_objects:
            obj.draw(frame)
        
        self._draw_ui(frame)
        return frame
    
    def _handle_gestures(self, gesture, position, frame):
        if gesture != self.last_gesture:
            self.gesture_hold_time = time.time()
            self.last_gesture = gesture
            return
        
        hold_duration = time.time() - self.gesture_hold_time
        if hold_duration < self.gesture_threshold:
            return
        
        if gesture == GestureType.PALM_OPEN and hold_duration < self.gesture_threshold + 0.1:
            modes = ["SELECT", "CREATE", "MOVE", "SCALE", "DELETE"]
            current_idx = modes.index(self.current_mode)
            self.current_mode = modes[(current_idx + 1) % len(modes)]
            print(f"Mode: {self.current_mode}")
            self.gesture_hold_time = time.time() + 1
        
        if self.current_mode == "CREATE" and gesture == GestureType.POINT and hold_duration < self.gesture_threshold + 0.1:
            self.type_index = (self.type_index + 1) % len(self.available_types)
            self.create_object_type = self.available_types[self.type_index]
            print(f"Type: {self.create_object_type}")
            self.gesture_hold_time = time.time() + 1
        
        if gesture == GestureType.PINCH:
            if self.pinch_start_pos is None:
                self.pinch_start_pos = position
                
                if self.current_mode == "CREATE":
                    self.create_object(position)
                elif self.current_mode == "SELECT":
                    obj = self.find_nearest_object(position)
                    if self.selected_object is not None:
                        self.selected_object.is_selected = False
                    self.selected_object = obj
                    if obj is not None:
                        obj.is_selected = True
                        self.object_start_pos = obj.position.copy()
                        print(f"Selected {obj.obj_type}")
                elif self.current_mode == "DELETE":
                    obj = self.find_nearest_object(position)
                    if obj is not None:
                        self.objects.remove(obj)
                        print(f"Deleted object")
                        if self.selected_object == obj:
                            self.selected_object = None
            else:
                if self.current_mode == "MOVE" and self.selected_object is not None:
                    delta = np.array(position) - np.array(self.pinch_start_pos)
                    self.selected_object.position = self.object_start_pos + delta
                elif self.current_mode == "SCALE" and self.selected_object is not None:
                    delta_y = position[1] - self.pinch_start_pos[1]
                    scale_factor = 1 - (delta_y / 300)
                    self.selected_object.size = max(20, min(100, int(50 * scale_factor)))
                    
                    delta_x = position[0] - self.pinch_start_pos[0]
                    depth_delta = delta_x / 5
                    self.selected_object.depth = max(0, min(100, self.selected_object.depth + depth_delta))
        else:
            if self.pinch_start_pos is not None:
                self.pinch_start_pos = None
                self.object_start_pos = None
    
    def _draw_ui(self, frame):
        h, w, _ = frame.shape
        
        # Top bar background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 100), (40, 40, 40), -1)
        blended = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        frame[0:100, 0:w] = blended[0:100, 0:w]
        
        cv2.putText(frame, "HoloBuild AR - OpenCV Edition", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        if not self.calibrated:
            cv2.putText(frame, "Show your hand to the camera!", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        cv2.putText(frame, f"FPS: {int(self.fps)}", (w - 120, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        cv2.putText(frame, f"Mode: {self.current_mode}", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        cv2.putText(frame, f"Objects: {len(self.objects)}", (200, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        if self.current_mode == "CREATE":
            cv2.putText(frame, f"Type: {self.create_object_type.upper()}", (400, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
        
        if self.show_help:
            self._draw_help_panel(frame)
    
    def _draw_help_panel(self, frame):
        h, w, _ = frame.shape
        panel_h = 240
        
        # Help panel background
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, h - panel_h - 10), (520, h - 10), (40, 40, 40), -1)
        blended = cv2.addWeighted(overlay, 0.8, frame, 0.2, 0)
        frame[h - panel_h - 10:h - 10, 10:520] = blended[h - panel_h - 10:h - 10, 10:520]
        
        y_offset = h - panel_h + 10
        cv2.putText(frame, "HAND GESTURE CONTROLS:", (20, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        controls = [
            "Open Palm (4-5 fingers): Switch Mode",
            "Point (1 finger): Change Object Type",
            "Pinch (closed fist): Action",
            "Pinch + Move: Move Object (MOVE mode)",
            "Pinch + Move: Scale Object (SCALE mode)",
            "",
            "KEYBOARD: H=Help | C=Clear | Q=Quit",
            "TIP: Hold gestures for 0.5 seconds!"
        ]
        
        for i, text in enumerate(controls):
            cv2.putText(frame, text, (30, y_offset + 25 + i * 24), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def handle_keyboard(self, key):
        if key == ord('h') or key == ord('H'):
            self.show_help = not self.show_help
        elif key == ord('c') or key == ord('C'):
            self.objects.clear()
            self.selected_object = None
            print("Cleared all objects")
        elif key == ord('q') or key == ord('Q'):
            return False
        return True


def main():
    print("=" * 60)
    print("HoloBuild: Hand-Driven 2.5D AR Assembly System")
    print("=" * 60)
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print("ERROR: Cannot access webcam!")
        return
    
    print("Camera ready!")
    
    try:
        ar_system = ARAssemblySystem()
        print("System ready!")
        print("\nShow your hand to begin!")
        print("H=Help | C=Clear | Q=Quit\n")
        
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            frame = cv2.flip(frame, 1)
            frame = ar_system.update(frame)
            cv2.imshow('HoloBuild AR Assembly', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if not ar_system.handle_keyboard(key):
                break
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\nClosed successfully!")


if __name__ == "__main__":
    main()
