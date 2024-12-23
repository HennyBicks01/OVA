import sys
import os
import random
import glob
import math
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QSystemTrayIcon, QMenu, QPushButton
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject, QSize
from PyQt5.QtGui import QPixmap, QImage, QIcon, QTransform
import threading
from voice_assistant import VoiceAssistant
from speech_bubble import SpeechBubbleWindow
from text_to_speech import TTSEngine
import pyttsx3

class ChatBubble(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #ccc;
                border-radius: 10px;
                padding: 10px;
                font-size: 12px;
            }
        """)
        self.hide()
        
    def showMessage(self, text, duration=5000):
        self.setText(text)
        self.adjustSize()
        self.show()
        QTimer.singleShot(duration, self.hide)

class ResponseHandler(QObject):
    response_ready = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()

class OwlPet(QWidget):
    handle_response_signal = pyqtSignal(str)
    start_dance_signal = pyqtSignal()
    stop_dance_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.loadAnimations()
        self.current_state = "idle"
        self.previous_state = None
        self.frame_index = 0
        self.frame_delay = 50  # 50ms = 20fps
        self.dance_frame_delay = 50  # 30ms ≈ 33fps for dancing
        self.blink_interval = (2000, 4000)  # Random blink every 2-4 seconds
        self.dance_duration = 3000  # Dance for 3 seconds
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.updateAnimation)
        self.animation_timer.start(self.frame_delay)
        
        # Initialize speech bubble window
        self.speech_bubble = SpeechBubbleWindow()
        
        # Initialize response handler
        self.response_handler = ResponseHandler()
        self.response_handler.response_ready.connect(self.handle_response_gui)
        
        # Initialize voice assistant
        try:
            self.voice_assistant = VoiceAssistant(callback=self.handle_response_thread)
            self.voice_assistant.start_listening()
        except ImportError as e:
            print(f"Voice assistant not available: {e}")
            self.voice_assistant = None
        
        # Initialize TTS engine
        self.tts_engine = TTSEngine()
        self.tts_engine.speak_started.connect(self.start_dance)
        self.tts_engine.speak_finished.connect(self.on_speak_done)
        self.tts_engine.speak_error.connect(lambda e: print(f"TTS Error: {e}"))
        
        self.dragging = False
        self.offset = QPoint()
        self.facing_right = True
        self.last_pos = None
        
        # Create chat bubble
        self.chat_bubble = ChatBubble(self)
        
        # Flying movement variables
        self.flying_start = None
        self.flying_end = None
        self.flying_progress = 0
        self.flying_control_points = []
        
        # Set initial size
        self.setMinimumSize(100, 100)
        
        # State change timer
        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self.randomStateChange)
        self.state_timer.start(5000)  # Check for state change every 5 seconds
        
        # Create system tray icon
        self.createSystemTray()
        
        # State transitions
        self.state_transitions = {
            "idle": ["take_flight", "pruning", "dance"],
            "take_flight": ["flying"],  # Only transitions to flying
            "flying": ["landing"],      # Only transitions to landing
            "landing": ["idle"],        # Only transitions to idle
            "pruning": ["idle"],        # Returns to idle after pruning
            "dance": ["idle"]           # Returns to idle after dance
        }
        
        # Track if we're in a transition animation
        self.in_transition = False
        
        # Connect all signals
        self.handle_response_signal.connect(self.handle_response_gui)
        self.start_dance_signal.connect(self.start_dance)
        self.stop_dance_signal.connect(self.stop_dance)

    def initUI(self):
        # Create a window without frame that stays on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Create sprite label with fixed size
        self.sprite_label = QLabel(self)
        self.sprite_label.setFixedSize(64, 64)
        self.sprite_label.move(0, 0)  # Position at top-left corner
        
        # Set window to same fixed size as sprite
        self.setFixedSize(48, 48)
        
        # Initialize speech bubble window
        self.speech_bubble = SpeechBubbleWindow()
        
        # Set initial position
        self.desktop = QApplication.desktop().screenGeometry()
        initial_pos = QPoint(self.desktop.width() - 500, self.desktop.height() - 500)
        self.move(initial_pos)
        self.last_pos = initial_pos
        self.show()

    def createSystemTray(self):
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'idle', '1.png')))
        
        # Create tray menu
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show/Hide")
        show_action.triggered.connect(self.toggleVisibility)
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def toggleVisibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def loadAnimations(self):
        self.animations = {}
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
        
        # Load all animations
        for anim_dir in ['idle', 'dance', 'flying', 'landing', 'pruning', 'take_flight']:
            anim_path = os.path.join(assets_dir, anim_dir)
            if os.path.exists(anim_path):
                frames = sorted(glob.glob(os.path.join(anim_path, '*.png')))
                if frames:  # Only add if there are frames
                    self.animations[anim_dir] = [QPixmap(frame).scaled(64, 64, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) for frame in frames]

    def generate_bezier_points(self):
        # Generate a new random flight path using bezier curves
        start = self.pos()
        
        # Generate random end point on screen
        end_x = random.randint(0, self.desktop.width() - self.width())
        end_y = random.randint(0, self.desktop.height() - self.height())
        end = QPoint(end_x, end_y)
        
        # Generate two control points for curved path
        ctrl1_x = random.randint(min(start.x(), end.x()), max(start.x(), end.x()))
        ctrl1_y = random.randint(0, self.desktop.height())
        ctrl2_x = random.randint(min(start.x(), end.x()), max(start.x(), end.x()))
        ctrl2_y = random.randint(0, self.desktop.height())
        
        # Set initial facing direction based on flight path
        self.facing_right = end_x > start.x()
        
        return start, QPoint(ctrl1_x, ctrl1_y), QPoint(ctrl2_x, ctrl2_y), end

    def bezier_curve(self, t, p0, p1, p2, p3):
        # Calculate point on bezier curve at time t
        x = (1-t)**3 * p0.x() + 3*(1-t)**2*t * p1.x() + 3*(1-t)*t**2 * p2.x() + t**3 * p3.x()
        y = (1-t)**3 * p0.y() + 3*(1-t)**2*t * p1.y() + 3*(1-t)*t**2 * p2.y() + t**3 * p3.y()
        return QPoint(int(x), int(y))

    def update_facing_direction(self, new_pos):
        if self.last_pos is not None:
            # Determine direction based on x movement
            moving_right = new_pos.x() > self.last_pos.x()
            
            # Only update direction if there's significant horizontal movement
            if abs(new_pos.x() - self.last_pos.x()) > 5:
                if moving_right and not self.facing_right:
                    self.facing_right = True
                elif not moving_right and self.facing_right:
                    self.facing_right = False
        
        self.last_pos = new_pos

    def get_current_frame(self):
        if self.current_state in self.animations and self.animations[self.current_state]:
            pixmap = self.animations[self.current_state][self.frame_index]
            
            # Flip the sprite if facing left for flight-related animations and regular movement
            if not self.facing_right and (self.current_state in ["flying", "take_flight", "landing"] or self.dragging):
                transform = QTransform()
                transform.scale(-1, 1)  # Flip horizontally
                pixmap = pixmap.transformed(transform)
            
            return pixmap
        return None

    def updateAnimation(self):
        """Update the current animation frame"""
        if not self.animations or not self.animations.get(self.current_state):
            return

        # Get current frame list
        current_frames = self.animations[self.current_state]
        if not current_frames:
            return

        # Update frame index
        self.frame_index = (self.frame_index + 1) % len(current_frames)
        
        # Update image
        self.sprite_label.setPixmap(current_frames[self.frame_index])
        
        # Handle flying movement
        if self.current_state == "flying":
            if self.flying_start is None:
                # Initialize new flight path
                self.flying_start, *self.flying_control_points, self.flying_end = self.generate_bezier_points()
                self.flying_progress = 0
            
            # Update position along flight path
            self.flying_progress += 0.02  # Adjust speed here
            
            # Calculate new position
            new_pos = self.bezier_curve(
                self.flying_progress,
                self.flying_start,
                self.flying_control_points[0],
                self.flying_control_points[1],
                self.flying_end
            )
            
            # Update facing direction before moving
            self.update_facing_direction(new_pos)
            self.move(new_pos)
            
            # If we've reached the destination, transition to landing
            if self.flying_progress >= 1:
                self.changeState("landing")
        
        # Handle transition states
        if self.frame_index == len(current_frames) - 1:  # At the last frame
            if self.current_state in ["take_flight", "landing", "pruning"]:
                next_state = self.state_transitions[self.current_state][0]
                self.changeState(next_state)
        
        self.adjustSize()
        
        # Reset flying variables when not flying
        if self.current_state != "flying":
            self.flying_start = None
            self.flying_progress = 0
            self.flying_control_points = []

    def changeState(self, new_state):
        if new_state == "dance" and not self.in_transition:
            self.in_transition = True
            self.current_state = new_state
            self.frame_index = 0
            self.animation_timer.setInterval(self.dance_frame_delay)
            QTimer.singleShot(self.dance_duration, self.stop_dance)
        else:
            self.current_state = new_state
            self.frame_index = 0
            self.animation_timer.setInterval(self.frame_delay)

    def randomStateChange(self):
        # Don't change state if we're in a transition animation
        if self.in_transition:
            return
            
        if random.random() < 0.3:  # 30% chance to change state
            if self.current_state in self.state_transitions:
                available_states = self.state_transitions[self.current_state]
                if available_states:
                    new_state = random.choice(available_states)
                    self.changeState(new_state)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = self.mapToParent(event.pos() - self.offset)
            self.move(new_pos)
            # Update speech bubble position if it's visible
            if hasattr(self, 'speech_bubble') and self.speech_bubble.isVisible():
                self.update_speech_bubble_position()

    def update_speech_bubble_position(self):
        """Update the speech bubble position based on current owl position"""
        # Get screen geometry and bubble size
        screen = QApplication.primaryScreen().geometry()
        bubble_size = self.speech_bubble.size()
        owl_pos = self.pos()
        owl_size = self.size()
        
        # Default position: top-right of owl
        positions = [
            # Position 1: Top-right of owl (default)
            (owl_pos.x() + owl_size.width(), owl_pos.y() - bubble_size.height()),
            # Position 2: Top-left of owl
            (owl_pos.x() - bubble_size.width(), owl_pos.y() - bubble_size.height()),
            # Position 3: Bottom-right of owl
            (owl_pos.x() + owl_size.width(), owl_pos.y() + owl_size.height()),
            # Position 4: Bottom-left of owl
            (owl_pos.x() - bubble_size.width(), owl_pos.y() + owl_size.height())
        ]
        
        # Find the best position that keeps the bubble on screen
        for bubble_x, bubble_y in positions:
            # Check if bubble fits at this position
            if (bubble_x >= 0 and 
                bubble_y >= 0 and 
                bubble_x + bubble_size.width() <= screen.width() and 
                bubble_y + bubble_size.height() <= screen.height()):
                # Found a good position
                self.speech_bubble.showAtPosition(bubble_x, bubble_y)
                return
        
        # If no perfect position found, use centered position above owl
        fallback_x = owl_pos.x() + (owl_size.width() - bubble_size.width()) // 2
        fallback_y = owl_pos.y() - bubble_size.height()
        
        # Ensure bubble stays within screen bounds
        fallback_x = max(0, min(fallback_x, screen.width() - bubble_size.width()))
        fallback_y = max(0, min(fallback_y, screen.height() - bubble_size.height()))
        
        self.speech_bubble.showAtPosition(fallback_x, fallback_y)

    def show_speech_bubble(self, text):
        """Show a speech bubble with the response"""
        # Get the last recognized text from the voice assistant
        last_text = ""
        if hasattr(self, 'voice_assistant') and self.voice_assistant:
            last_text = self.voice_assistant.last_text
        
        # Update speech bubble text
        self.speech_bubble.setText(text, last_text)
        
        # Update position
        self.update_speech_bubble_position()
    
    def handle_response_thread(self, response):
        """Handle the response from a background thread"""
        # Emit signal to handle response in GUI thread
        self.handle_response_signal.emit(response)
    
    def handle_response_gui(self, response):
        """Handle the response in the GUI thread"""
        try:
            # Show the speech bubble with both question and response
            self.show_speech_bubble(response)
            # Speak the response
            self.speak_response(response)
        except Exception as e:
            print(f"Error handling response: {e}")
    
    def speak_response(self, response):
        """Speak the response using TTS"""
        self.tts_engine.speak(response)
    
    def on_speak_done(self):
        """Handle completion of speaking in GUI thread"""
        self.stop_dance()
        self.speech_bubble.hide()
    
    def start_dance(self):
        """Start dance animation in GUI thread"""
        if not self.in_transition:
            self.changeState("dance")
    
    def stop_dance(self):
        """Stop dance animation in GUI thread"""
        self.in_transition = False
        self.changeState("idle")
    
    def contextMenuEvent(self, event):
        # Only show menu if not in transition
        if not self.in_transition:
            # Create action menu
            action_menu = QMenu(self)
            
            # Add actions
            dance_action = action_menu.addAction("Dance")
            dance_action.triggered.connect(lambda: self.changeState("dance"))
            
            fly_action = action_menu.addAction("Take Flight")
            fly_action.triggered.connect(lambda: self.initiate_flight())
            
            preen_action = action_menu.addAction("Preen")
            preen_action.triggered.connect(lambda: self.changeState("pruning"))
            
            # Add separator before quit
            action_menu.addSeparator()
            
            quit_action = action_menu.addAction("Quit")
            quit_action.triggered.connect(QApplication.quit)
            
            # Show the menu at cursor position
            action_menu.exec_(event.globalPos())

    def initiate_flight(self):
        # Generate flight path before starting take-off animation
        self.flying_start, *self.flying_control_points, self.flying_end = self.generate_bezier_points()
        self.flying_progress = 0
        self.changeState("take_flight")

    def closeEvent(self, event):
        """Clean up resources when closing"""
        if hasattr(self, 'voice_assistant'):
            self.voice_assistant.stop_listening()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when window is closed
    pet = OwlPet()
    sys.exit(app.exec_())
