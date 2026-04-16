#!/usr/bin/env python3
"""
SayCheese - Camera Application for Linux
Developed by Jahanzaib Ashraf Mir
"""

import sys
import os
import cv2
import time
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# Check dependencies before importing
def check_dependencies():
    missing_deps = []
    
    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")
        
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:
        missing_deps.append("PyQt5")
        
    if missing_deps:
        print(" Missing dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n Install them using the setup script:")
        print("   chmod +x install_dependencies.sh && ./install_dependencies.sh")
        return False
        
    return True

if not check_dependencies():
    sys.exit(1)

# Import after dependency check
import cv2
from PyQt5.QtWidgets import (QApplication, QLabel, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QWidget, QMessageBox, QProgressDialog)
from PyQt5.QtGui import QImage, QPixmap, QColor, QPalette, QPainter, QFont
from PyQt5.QtCore import QTimer, Qt, QPoint, pyqtSignal

class SayCheeseApp(QWidget):
    thumbnail_updated = pyqtSignal(str, bool)
    
    def __init__(self):
        super().__init__()
        
        # Application info
        self.developer = "Jahanzaib Ashraf Mir"
        self.version = "1.0.0"
        
        # Check FFmpeg
        if not self.check_ffmpeg():
            self.show_ffmpeg_install_dialog()
            
        self.setup_directories()
        
        # Initialize camera
        progress = QProgressDialog("Initializing camera... Say Cheese! ", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        if not self.initialize_camera():
            progress.close()
            return
            
        progress.close()
        
        self.setup_application()
        self.initialize_ui()
        self.setup_timers()
        
    def check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
            
    def show_ffmpeg_install_dialog(self):
        """Show FFmpeg installation dialog"""
        reply = QMessageBox.question(
            self,
            "FFmpeg Required",
            "FFmpeg is required for video recording with audio.\n\n"
            "Would you like to install it now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            try:
                subprocess.run([
                    'sudo', 'apt', 'install', 'ffmpeg', '-y'
                ], check=True)
                QMessageBox.information(self, "Success", "FFmpeg installed successfully!")
            except subprocess.CalledProcessError:
                QMessageBox.warning(
                    self, 
                    "Installation Failed", 
                    "Failed to install FFmpeg. Please run:\n"
                    "sudo apt install ffmpeg"
                )
        
    def setup_directories(self):
        """Create necessary directories in user's Pictures folder"""
        self.pictures_dir = Path.home() / "Pictures" / "SayCheese"
        self.pictures_dir.mkdir(parents=True, exist_ok=True)
        self.save_directory = str(self.pictures_dir)
        print(f" Photos and videos will be saved to: {self.save_directory}")
        
    def initialize_camera(self):
        """Initialize camera with multiple fallbacks"""
        self.camera = None
        
        # Try different camera indices and backends
        for camera_index in [0, 1, 2]:
            for backend in [cv2.CAP_V4L2, cv2.CAP_ANY]:
                try:
                    self.camera = cv2.VideoCapture(camera_index, backend)
                    if self.camera.isOpened():
                        # Test if camera actually works
                        ret, frame = self.camera.read()
                        if ret and frame is not None:
                            print(f" Camera found at index {camera_index}")
                            
                            # Configure camera
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            
                            # Get FPS
                            fps = self.camera.get(cv2.CAP_PROP_FPS)
                            self.actual_fps = 30.0 if fps <= 0 else min(fps, 30.0)
                            self.frame_interval = 1.0 / self.actual_fps
                            
                            return True
                        else:
                            self.camera.release()
                except Exception as e:
                    if self.camera:
                        self.camera.release()
                    continue
                    
        # If we get here, no camera was found
        QMessageBox.critical(
            self,
            "Camera Not Found ",
            "No camera device could be found!\n\n"
            "Please check:\n"
            "• Camera is connected properly\n"
            "• Camera permissions are granted\n"
            "• No other app is using the camera\n"
            "• Try: sudo usermod -a -G video $USER"
        )
        return False

    def setup_application(self):
        """Initialize application state"""
        self.current_mode = "photo"
        self.recording_active = False
        self.mirror_enabled = True
        self.flip_enabled = False
        self.display_info = True
        self.recording_start_time = None
        self.video_recorder = None
        self.audio_recorder = None
        self.last_frame_time = time.time()
        self.frame_counter = 0
        self.current_frame_data = None

    def initialize_ui(self):
        """Set up the user interface"""
        self.setWindowTitle(f"SayCheese  v{self.version} - by {self.developer}")
        self.setFixedSize(1000, 700)
        self.apply_dark_theme()
        
        # Main camera display
        self.camera_display = QLabel("Say Cheese! ")
        self.camera_display.setAlignment(Qt.AlignCenter)
        self.camera_display.setStyleSheet("""
            QLabel {
                background-color: #000000;
                color: #ffffff;
                border: 3px solid #444444;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.camera_display.setMinimumSize(800, 500)
        
        # Mode buttons
        self.photo_btn = QPushButton(" Photo Mode")
        self.video_btn = QPushButton("🎥 Video Mode")
        
        # Capture button
        self.capture_btn = QPushButton(" Capture Photo")
        self.capture_btn.setStyleSheet(self.get_capture_button_style())
        
        # Settings buttons
        self.mirror_btn = QPushButton(" Mirror: ON")
        self.flip_btn = QPushButton(" Flip: OFF")
        self.gallery_btn = QPushButton(" Open Gallery")
        
        # Style all buttons
        for btn in [self.photo_btn, self.video_btn, self.mirror_btn, self.flip_btn, self.gallery_btn]:
            btn.setStyleSheet(self.get_button_style())
            btn.setFixedHeight(40)
            
        self.capture_btn.setFixedHeight(50)
        
        # Layout setup
        main_layout = QVBoxLayout()
        
        # Camera display
        main_layout.addWidget(self.camera_display)
        
        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self.photo_btn)
        mode_layout.addWidget(self.video_btn)
        mode_layout.addStretch()
        
        # Capture button
        capture_layout = QHBoxLayout()
        capture_layout.addStretch()
        capture_layout.addWidget(self.capture_btn)
        capture_layout.addStretch()
        
        # Settings
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(self.mirror_btn)
        settings_layout.addWidget(self.flip_btn)
        settings_layout.addWidget(self.gallery_btn)
        settings_layout.addStretch()
        
        main_layout.addLayout(mode_layout)
        main_layout.addLayout(capture_layout)
        main_layout.addLayout(settings_layout)
        
        self.setLayout(main_layout)
        
        # Connect signals
        self.photo_btn.clicked.connect(lambda: self.switch_mode("photo"))
        self.video_btn.clicked.connect(lambda: self.switch_mode("video"))
        self.capture_btn.clicked.connect(self.capture_action)
        self.mirror_btn.clicked.connect(self.toggle_mirror)
        self.flip_btn.clicked.connect(self.toggle_flip)
        self.gallery_btn.clicked.connect(self.open_gallery)
        
        # Update initial state
        self.update_ui()
        
    def apply_dark_theme(self):
        """Apply dark theme to the application"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(40, 40, 40))
        dark_palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.Text, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.Button, QColor(60, 60, 60))
        dark_palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Highlight, QColor(255, 165, 0))  # Orange highlight
        dark_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(dark_palette)
        
    def get_button_style(self):
        return """
            QPushButton {
                background-color: #555555;
                color: white;
                border: 2px solid #777777;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666666;
                border: 2px solid #888888;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
        """
        
    def get_capture_button_style(self):
        if self.recording_active:
            return """
                QPushButton {
                    background-color: #ff4444;
                    color: white;
                    border: 3px solid #ff7777;
                    border-radius: 25px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff6666;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #ffa500;
                    color: black;
                    border: 3px solid #ffb732;
                    border-radius: 25px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ffb732;
                }
            """
        
    def switch_mode(self, mode):
        """Switch between photo and video modes"""
        if self.recording_active:
            self.stop_recording()
            
        self.current_mode = mode
        self.update_ui()
        
        if mode == "photo":
            self.show_status(" Photo mode activated - Press Capture or Spacebar!")
        else:
            self.show_status(" Video mode activated - Press Record or Spacebar!")
            
    def update_ui(self):
        """Update UI based on current state"""
        # Update mode buttons
        photo_style = self.get_active_style() if self.current_mode == "photo" else self.get_button_style()
        video_style = self.get_active_style() if self.current_mode == "video" else self.get_button_style()
        
        self.photo_btn.setStyleSheet(photo_style)
        self.video_btn.setStyleSheet(video_style)
        
        # Update capture button
        self.capture_btn.setStyleSheet(self.get_capture_button_style())
        
        if self.current_mode == "photo":
            self.capture_btn.setText("📷 Capture Photo")
        else:
            if self.recording_active:
                self.capture_btn.setText(" Stop Recording")
            else:
                self.capture_btn.setText(" Start Recording")
                
        # Update mirror/flip buttons
        self.mirror_btn.setText(f" Mirror: {'ON' if self.mirror_enabled else 'OFF'}")
        self.flip_btn.setText(f" Flip: {'ON' if self.flip_enabled else 'OFF'}")
        
    def get_active_style(self):
        return """
            QPushButton {
                background-color: #ffa500;
                color: black;
                border: 2px solid #ffb732;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ffb732;
            }
        """
        
    def capture_action(self):
        """Handle capture/record actions"""
        if self.current_mode == "photo":
            self.capture_photo()
        else:
            if not self.recording_active:
                self.start_recording()
            else:
                self.stop_recording()
                
    def capture_photo(self):
        """Capture and save a photo"""
        if self.current_frame_data is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"saycheese_photo_{timestamp}.jpg"
            filepath = os.path.join(self.save_directory, filename)
            
            try:
                cv2.imwrite(filepath, self.current_frame_data, [cv2.IMWRITE_JPEG_QUALITY, 95])
                self.show_status(f" Photo saved: {filename}")
                print(f" Photo saved to: {filepath}")
            except Exception as e:
                self.show_error(f"Failed to save photo: {e}")
                
    def start_recording(self):
        """Start video recording"""
        if not self.check_ffmpeg():
            self.show_warning("FFmpeg not found. Video will be saved without audio.")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.final_video_path = os.path.join(self.save_directory, f"saycheese_video_{timestamp}.avi")
        
        try:
            # Get frame dimensions
            if self.current_frame_data is not None:
                height, width = self.current_frame_data.shape[:2]
            else:
                width, height = 640, 480
                
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.video_recorder = cv2.VideoWriter(
                self.final_video_path, fourcc, 20.0, (width, height)
            )
            
            self.recording_active = True
            self.recording_start_time = time.time()
            self.update_ui()
            self.show_status("🎥 Recording started... Press Stop or Spacebar to finish")
            
        except Exception as e:
            self.show_error(f"Failed to start recording: {e}")
            
    def stop_recording(self):
        """Stop video recording"""
        if self.video_recorder:
            self.video_recorder.release()
            self.video_recorder = None
            
        self.recording_active = False
        self.update_ui()
        
        recording_time = time.time() - self.recording_start_time
        self.show_status(f" Recording saved! Duration: {recording_time:.1f}s")
        print(f" Video saved to: {self.final_video_path}")
        
    def toggle_mirror(self):
        """Toggle mirror mode"""
        self.mirror_enabled = not self.mirror_enabled
        self.update_ui()
        self.show_status(f"Mirror {'enabled' if self.mirror_enabled else 'disabled'}")
        
    def toggle_flip(self):
        """Toggle flip mode"""
        self.flip_enabled = not self.flip_enabled
        self.update_ui()
        self.show_status(f"Flip {'enabled' if self.flip_enabled else 'disabled'}")
        
    def open_gallery(self):
        """Open the gallery directory"""
        try:
            subprocess.run(['xdg-open', self.save_directory])
            self.show_status(" Opening gallery...")
        except Exception as e:
            self.show_error(f"Failed to open gallery: {e}")
            
    def setup_timers(self):
        """Set up frame update timer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~33 FPS
        
    def update_frame(self):
        """Update camera frame display"""
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                # Apply transformations
                if self.mirror_enabled:
                    frame = cv2.flip(frame, 1)
                if self.flip_enabled:
                    frame = cv2.flip(frame, 0)
                    
                self.current_frame_data = frame
                
                # Convert to QImage and display
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                
                # Add overlays
                if self.recording_active:
                    painter = QPainter(pixmap)
                    elapsed = int(time.time() - self.recording_start_time)
                    timer_text = f"● REC {elapsed // 60:02d}:{elapsed % 60:02d}"
                    
                    painter.setPen(QColor(255, 0, 0))
                    painter.setFont(QFont("Arial", 24, QFont.Bold))
                    painter.drawText(20, 40, timer_text)
                    painter.end()
                
                self.camera_display.setPixmap(
                    pixmap.scaled(self.camera_display.width(), 
                                self.camera_display.height(),
                                Qt.KeepAspectRatio))
                                
    def show_status(self, message):
        """Show status message"""
        print(f" {message}")
        
    def show_warning(self, message):
        """Show warning message"""
        QMessageBox.warning(self, "Warning", message)
        
    def show_error(self, message):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        key = event.key()
        
        if key == Qt.Key_Space:
            self.capture_action()
        elif key == Qt.Key_P:
            self.switch_mode("photo")
        elif key == Qt.Key_V:
            self.switch_mode("video")
        elif key == Qt.Key_M:
            self.toggle_mirror()
        elif key == Qt.Key_F:
            self.toggle_flip()
        elif key == Qt.Key_G:
            self.open_gallery()
        elif key == Qt.Key_Escape:
            self.close()
        elif key == Qt.Key_H:
            self.show_help()
        else:
            super().keyPressEvent(event)
            
    def show_help(self):
        """Show keyboard shortcuts help"""
        help_text = """
        🎮 Keyboard Shortcuts:
        
        Spacebar  - Capture photo / Start-stop recording
        P         - Switch to Photo mode
        V         - Switch to Video mode  
        M         - Toggle mirror mode
        F         - Toggle flip mode
        G         - Open gallery
        H         - Show this help
        Esc       - Exit application
        
         Photos/Videos are saved to:
        ~/Pictures/SayCheese/
        """
        QMessageBox.information(self, "SayCheese Help", help_text)
        
    def closeEvent(self, event):
        """Handle application closure"""
        if self.recording_active:
            self.stop_recording()
        if self.camera and self.camera.isOpened():
            self.camera.release()
            
        print(" SayCheese application closed")
        event.accept()

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("SayCheese")
    app.setApplicationVersion("1.0.0")
    
    # Check if running on Linux
    if not sys.platform.startswith('linux'):
        QMessageBox.warning(None, "Platform Warning", 
                          "SayCheese is optimized for Linux. .")
    
    print(" Starting SayCheese Camera Application...")
    print(" Developed by Jahanzaib Ashraf Mir")
    print(" Say Cheese! ")
    
    window = SayCheeseApp()
    window.show()
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())
