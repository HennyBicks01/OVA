import sys
import os
import random
import glob
from PyQt5.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu, QDialog
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject, QSize, QThread
from PyQt5.QtGui import QPixmap, QIcon, QTransform, QPainter
from voice_assistant import VoiceAssistant
from display.display_manager import DisplayManager
from text_to_speech import TTSEngine
from settings_dialog import SettingsDialog
import json
import time
import logging
import pygame

# Add scripts directory to Python path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_resource_path(relative_path):
    """Get the correct resource path whether running as script or frozen exe"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        # For config and history, use the executable directory
        if relative_path in ['config.json', 'history']:
            return os.path.join(os.path.dirname(sys.executable), relative_path)
        # For other resources, use the bundled resources directory
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # Running as script
        base_path = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(base_path, relative_path)

class ChatBubble:
    def __init__(self, parent=None):
        self.parent = parent
        self.text = ""
        self.duration = 5000
        self.hide_timer = None
        
    def showMessage(self, text, duration=5000):
        self.text = text
        self.duration = duration
        
        # Clear any existing timer
        if self.hide_timer is not None:
            self.hide_timer.stop()
            
        # Create new timer for hiding
        self.hide_timer = QTimer(self.parent)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hideAndReset)
        self.hide_timer.start(duration)
    
    def hideAndReset(self):
        """Hide the bubble and notify parent to reset sleep timer"""
        # Get the OwlPet parent and reset its sleep timer
        parent = self.parent
        if parent and hasattr(parent, 'reset_idle_timer'):
            parent.reset_idle_timer()
        
class ResponseHandler(QObject):
    response_ready = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()

class OwlPet(QWidget):
    handle_response_signal = pyqtSignal(object)  # Changed from str to object to handle tuples
    start_thinking_signal = pyqtSignal()
    start_speaking_signal = pyqtSignal()
    stop_speaking_signal = pyqtSignal()
    start_listening_signal = pyqtSignal()
    stop_listening_signal = pyqtSignal()
    state_change_signal = pyqtSignal(str)  # New signal for state changes
    
    def __init__(self):
        super().__init__()
        # Initialize pygame mixer for sound effects
        pygame.mixer.init()
        
        # Initialize variables
        self.current_state = "idle"
        self.previous_state = None
        self.frame_index = 0
        self.frame_delay = 50  # 50ms = 20fps for normal animations
        self.in_transition = False
        self.scale_factor = 2  # Reduced scale factor
        
        # Load config
        self.config = self.load_config()
        
        # Random action timer
        self.random_action_timer = QTimer(self)
        self.random_action_timer.timeout.connect(self.perform_random_action)
        self.schedule_next_random_action()
        
        # Initialize variables
        self.current_state = "idle"
        self.previous_state = None
        self.frame_index = 0
        self.frame_delay = 50  # 50ms = 20fps for normal animations
        self.in_transition = False
        self.scale_factor = 2  # Reduced scale factor
        
        # Load config
        self.config = self.load_config()
        
        # Flag for direct listening mode
        self.waiting_for_response = False
        
        # Movement and position variables
        self.dragging = False
        self.offset = QPoint()
        self.facing_right = True
        self.last_pos = None
        self.flying_start = None
        self.flying_control_points = []
        self.flying_progress = 0
        
        # Animation loop counters
        self.dance_loops = 0
        self.dance_loops_target = 0
        
        # Pickup animation state
        self.reverse_animation = False
        self.held_state = None  # Store state before pickup
        
        # Sleep timer
        self.last_activity_time = QTimer()
        self.last_activity_time.timeout.connect(self.check_idle)
        self.last_activity_time.start(1000)  # Check every second
        self.idle_timeout = self.config.get('sleep_timer', 30)  # Get sleep timer from config, default to 30 seconds
        self.last_active = time.time()
        
        # Animation states and transitions
        self.state_transitions = {
            "take_flight": ["flying"],  # Take flight transitions to flying
            "flying": ["landing"],      # Flying loops until landing triggered
            "landing": ["idle"],        # Landing transitions to idle
            "look_around": ["idle"],    # Look around transitions to idle
            "listening": ["thinking", "idle"],  # Listening transitions to thinking on command or idle on timeout
            "thinking": ["speaking"],   # Thinking transitions to speaking when response ready
            "speaking": ["idle"],       # Speaking transitions to idle when done
            "dance": ["idle"],          # Dance transitions to idle after loops complete
            "pickup": ["held"],         # Pickup transitions to held state
            "held": ["putdown"],        # Held transitions to putdown when released
            "putdown": ["idle"],        # Putdown transitions back to previous state
            "falling_asleep": ["asleep"],  # Falling asleep transitions to asleep
            "waking_up": ["idle"],      # Waking up transitions to idle
        }
        
        # States that should loop
        self.looping_states = {"flying", "listening", "thinking", "speaking", "dance", "held", "asleep"}
        
        # Initialize UI and animations
        self.initUI()
        self.loadAnimations()
        self.setupTimers()
        
        # Initialize components
        self.setupComponents()
        
        # Connect state change signal
        self.state_change_signal.connect(self.setState)

    def setupTimers(self):
        """Setup animation and state timers"""
        # Animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.updateAnimation)
        self.animation_timer.start(self.frame_delay)
        
        # Random state change timer - disabled for now
        # self.state_timer = QTimer(self)
        # self.state_timer.timeout.connect(self.randomStateChange)
        # self.state_timer.start(random.randint(5000, 10000))  # Random interval between 5-10 seconds

    def setupComponents(self):
        """Setup additional components like TTS and voice assistant"""
        # Initialize display manager
        self.display_manager = DisplayManager(self)
        display_mode = self.config.get('display_mode', 'bubble')
        self.display_manager.initialize(display_mode)
        
        # Initialize TTS Engine
        self.tts_engine = TTSEngine()
        self.tts_engine.speak_started.connect(self.start_speaking)
        self.tts_engine.speak_finished.connect(self.on_speak_done)
        self.tts_engine.speak_error.connect(lambda e: print(f"TTS Error: {e}"))
        
        # Initialize Voice Assistant
        try:
            self.voice_assistant = VoiceAssistant(callback=self.handle_response_thread)
            print("Voice assistant initialized. Continuously listening...")
            self.voice_assistant.start_listening()
        except Exception as e:
            print(f"Voice assistant not available: {e}")
            self.voice_assistant = None
        
        # Connect all signals
        self.handle_response_signal.connect(self.handle_response_gui)
        self.start_thinking_signal.connect(self.start_thinking)
        self.start_speaking_signal.connect(self.start_speaking)
        self.stop_speaking_signal.connect(self.on_speak_done)
        self.start_listening_signal.connect(self.start_listening)
        self.stop_listening_signal.connect(self.stop_listening)
        
        # Initialize response handler
        self.response_handler = ResponseHandler()
        self.response_handler.response_ready.connect(self.handle_response_gui)
        
        # Set initial size
        self.setMinimumSize(100, 100)
        
        # Create context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        
        # Set initial position
        self.desktop = QApplication.desktop().screenGeometry()
        initial_pos = QPoint(self.desktop.width() - 500, self.desktop.height() - 500)
        self.move(initial_pos)
        self.show()
        
        # Create system tray
        self.createSystemTray()
    
    def initUI(self):
        # Create a window without frame that stays on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        
    def createSystemTray(self):
        """Create system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(get_resource_path(os.path.join("assets", "tray_icon.png"))))
        
        # Create the menu
        menu = QMenu()
        
        # Add actions
        look_around_action = menu.addAction("Look Around")
        look_around_action.triggered.connect(lambda: self.state_change_signal.emit("look_around"))
        
        take_flight_action = menu.addAction("Take Flight")
        take_flight_action.triggered.connect(lambda: self.state_change_signal.emit("take_flight"))
        
        menu.addSeparator()
        
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.showSettings)
        
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def toggleVisibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def loadAnimations(self):
        """Load all animation frames from assets directory"""
        # Get path to assets directory using resource path
        assets_dir = get_resource_path('assets')
        
        # Load all animations
        self.animations = {}
        for anim_dir in ['idle', 'flying', 'landing', 'take_flight', 'look_around', 'thinking', 
                        'speaking', 'dance', 'pickup', 'falling_asleep', 'asleep', 'waking_up', 'listening']:
            anim_path = os.path.join(assets_dir, anim_dir)
            if os.path.exists(anim_path):
                frames = sorted(glob.glob(os.path.join(anim_path, '*.png')))
                if frames:
                    # Load first frame to get dimensions
                    first_frame = QPixmap(frames[0])
                    base_size = first_frame.size()
                    
                    # Calculate scaled size maintaining aspect ratio
                    scaled_width = base_size.width() * self.scale_factor
                    scaled_height = base_size.height() * self.scale_factor
                    scaled_size = QSize(scaled_width, scaled_height)
                    
                    # Set window to scaled size
                    self.setFixedSize(scaled_size)
                    
                    # Scale all frames maintaining square pixels
                    self.animations[anim_dir] = [
                        QPixmap(frame).scaled(
                            scaled_width,
                            scaled_height,
                            Qt.IgnoreAspectRatio,  # Force exact dimensions
                            Qt.FastTransformation  # Use nearest-neighbor scaling
                        )
                        for frame in frames
                    ]
                    
                    # Create putdown animation by reversing pickup frames
                    if anim_dir == 'pickup':
                        self.animations['putdown'] = list(reversed(self.animations['pickup']))
                        # Create held state using last frame of pickup
                        self.animations['held'] = [self.animations['pickup'][-1]]
            else:
                print(f"Warning: Animation directory not found: {anim_path}")

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
        
        # Get the current frame
        current_frame = current_frames[self.frame_index]
        
        # Flip the sprite if facing left for flight-related animations
        if not self.facing_right and (self.current_state in ["flying", "take_flight", "landing"]):
            transform = QTransform()
            transform.scale(-1, 1)  # Flip horizontally
            current_frame = current_frame.transformed(transform)
        
        # Update image
        self.update()  # Request a repaint
        
        # Handle state transitions at the end of non-looping animations
        if self.frame_index == len(current_frames) - 1:  # At last frame
            if self.current_state == "dance":
                self.dance_loops += 1
                if self.dance_loops >= self.dance_loops_target:
                    self.state_change_signal.emit("idle")
            elif self.current_state == "pickup":
                self.state_change_signal.emit("held")
            elif self.current_state == "putdown":
                # Return to previous state or idle
                next_state = "idle"
                if self.held_state in ["thinking", "speaking"]:
                    next_state = self.held_state
                self.state_change_signal.emit(next_state)
            elif self.current_state == "falling_asleep":
                self.state_change_signal.emit("asleep")
            elif self.current_state == "waking_up":
                self.state_change_signal.emit("idle")
            elif self.current_state not in self.looping_states:
                # Non-looping states transition to their next state
                if self.current_state in self.state_transitions:
                    next_state = self.state_transitions[self.current_state][0]
                    self.state_change_signal.emit(next_state)
        
        # Handle flying movement
        if self.current_state == "flying":
            self.handle_flying_movement()

    def handle_flying_movement(self):
        """Handle movement during flying animation"""
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
        
        # Move to new position
        self.move(new_pos)
        
        # If we've reached the destination, transition to landing
        if self.flying_progress >= 1:
            self.state_change_signal.emit("landing")
            
        # Reset flying variables when not flying
        if self.current_state != "flying":
            self.flying_start = None
            self.flying_control_points = []
            
    def initiate_flight(self):
        """Start the flight sequence"""
        self.state_change_signal.emit("take_flight")

    def setState(self, new_state):
        """Change the current state and reset animation"""
        # Ensure this runs in the GUI thread
        if QThread.currentThread() != QApplication.instance().thread():
            self.state_change_signal.emit(new_state)
            return
            
        print(f"Changing state from {self.current_state} to {new_state}")
        
        # Store previous state
        self.previous_state = self.current_state
        
        # Update to new state
        self.current_state = new_state
        self.frame_index = 0
        
        # Stop current animation timer if running
        if hasattr(self, 'animation_timer') and self.animation_timer.isActive():
            self.animation_timer.stop()
        
        # Reset and start animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.updateAnimation)
        self.animation_timer.start(self.frame_delay)
        
        # If transitioning to idle after landing, keep the last facing direction
        if new_state == "idle" and self.previous_state == "landing":
            return
            
        # If starting a new flight sequence, update facing direction
        if new_state == "take_flight":
            # Generate flight path and set direction
            self.flying_start, *self.flying_control_points, self.flying_end = self.generate_bezier_points()
            self.flying_progress = 0
            self.facing_right = self.flying_end.x() > self.flying_start.x()
            
        # Schedule next random action only when entering idle state
        if new_state == "idle" and self.previous_state != "idle":
            self.schedule_next_random_action()

    def randomStateChange(self):
        """Disabled random state changes"""
        pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.current_state in ['asleep', 'falling_asleep']:
                self.wake_up()
                return
                
            self.dragging = True
            self.offset = event.pos()
            # Store current state before pickup
            if self.current_state not in ["pickup", "held", "putdown"]:
                self.held_state = self.current_state
            self.state_change_signal.emit("pickup")
        self.reset_idle_timer()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            if self.current_state in ["pickup", "held"]:
                self.state_change_signal.emit("putdown")

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = self.mapToParent(event.pos() - self.offset)
            self.move(new_pos)
            # Update display position if in bubble mode
            if self.display_manager and self.display_manager.current_mode == "bubble":
                self.update_speech_bubble_position()
        self.reset_idle_timer()

    def update_speech_bubble_position(self):
        """Update the speech bubble position based on current owl position"""
        if not self.display_manager or not self.display_manager.get_speech_bubble():
            return
            
        # Get screen geometry and bubble size
        screen = QApplication.primaryScreen().geometry()
        bubble = self.display_manager.get_speech_bubble()
        bubble_size = bubble.size()
        owl_pos = self.pos()
        owl_size = self.size()
        
        # Calculate center points
        owl_center_x = owl_pos.x() + owl_size.width() // 2
        owl_center_y = owl_pos.y() + owl_size.height() // 2
        
        # Define all possible positions (8 positions around Ova)
        positions = [
            # North (top center)
            (owl_center_x - bubble_size.width() // 2, 
             owl_pos.y() - bubble_size.height()),
            
            # Northeast (top right)
            (owl_pos.x() + owl_size.width(), 
             owl_pos.y() - bubble_size.height()),
            
            # East (right center)
            (owl_pos.x() + owl_size.width(),
             owl_center_y - bubble_size.height() // 2),
            
            # Southeast (bottom right)
            (owl_pos.x() + owl_size.width(),
             owl_pos.y() + owl_size.height()),
            
            # South (bottom center)
            (owl_center_x - bubble_size.width() // 2,
             owl_pos.y() + owl_size.height()),
            
            # Southwest (bottom left)
            (owl_pos.x() - bubble_size.width(),
             owl_pos.y() + owl_size.height()),
            
            # West (left center)
            (owl_pos.x() - bubble_size.width(),
             owl_center_y - bubble_size.height() // 2),
            
            # Northwest (top left)
            (owl_pos.x() - bubble_size.width(),
             owl_pos.y() - bubble_size.height())
        ]
        
        # Find best position that keeps bubble on screen
        best_pos = None
        min_overflow = float('inf')
        
        for x, y in positions:
            # Calculate how much the bubble would overflow screen bounds
            overflow = max(0, -x) + max(0, -y) + \
                      max(0, x + bubble_size.width() - screen.width()) + \
                      max(0, y + bubble_size.height() - screen.height())
            
            # If position is completely on screen, use it immediately
            if overflow == 0:
                best_pos = (x, y)
                break
            
            # Otherwise, keep track of position with minimum overflow
            if overflow < min_overflow:
                min_overflow = overflow
                best_pos = (x, y)
        
        # If no perfect position found, adjust the best position to fit on screen
        if best_pos:
            x, y = best_pos
            # Constrain to screen bounds
            x = max(0, min(x, screen.width() - bubble_size.width()))
            y = max(0, min(y, screen.height() - bubble_size.height()))
            bubble.move(int(x), int(y))
    
    def show_speech_bubble(self, text):
        """Show a message in the current display mode"""
        # Get the last recognized text from the voice assistant
        last_text = ""
        if hasattr(self, 'voice_assistant') and self.voice_assistant:
            last_text = self.voice_assistant.last_text
        
        # Show message using display manager
        if self.display_manager:
            self.display_manager.show_message(text, last_text)
    
    def handle_response_thread(self, response):
        """Handle the response from a background thread"""
        try:
            # Wake up if asleep
            if self.current_state in ['asleep', 'falling_asleep']:
                self.wake_up()
            
            # Handle different response types
            if response == "START_LISTENING":
                self.start_listening_signal.emit()
            elif response == "STOP_LISTENING":
                self.stop_listening_signal.emit()
            elif response == "START_THINKING":
                self.start_thinking_signal.emit()
            else:
                # Emit signal to handle response in GUI thread
                self.handle_response_signal.emit(response)
        except Exception as e:
            print(f"Error handling response: {e}")
    
    def handle_response_gui(self, response):
        """Handle the response in the GUI thread"""
        try:
            # Extract response text and user text from tuple if present
            response_text = response[0] if isinstance(response, tuple) else response
            
            # Show the message in the current display mode
            self.show_speech_bubble(response)
            # Change from thinking to speaking
            self.state_change_signal.emit("speaking")
            # Speak the response
            self.speak_response(response_text)
            
            # Check if response ends with a question mark
            if response_text.strip().endswith('?') and not self.waiting_for_response:
                self.waiting_for_response = True
                # Connect to speak finished to start listening
                self.tts_engine.speak_finished.connect(self.handle_question_response)
                
        except Exception as e:
            print(f"Error handling response: {e}")
    
    def handle_question_response(self):
        """Handle when Ova asks a question"""
        try:
            # Disconnect the signal to prevent multiple connections
            self.tts_engine.speak_finished.disconnect(self.handle_question_response)
            
            if hasattr(self, 'voice_assistant') and self.voice_assistant:
                # Play activation sound before starting to listen
                if self.voice_assistant.activation_sound_obj:
                    self.voice_assistant.activation_sound_obj.play()
                    time.sleep(0.1)  # Small delay to let sound start playing
                
                # Start listening animation through signal
                self.state_change_signal.emit("listening")
                
                # Start direct listening mode
                self.voice_assistant.start_direct_listening(timeout=10)  # Increased timeout for questions
            
            self.waiting_for_response = False
            
        except Exception as e:
            print(f"Error in handle_question_response: {e}")
            self.waiting_for_response = False

    def start_thinking(self):
        """Start thinking animation when wake word detected"""
        self.state_change_signal.emit("thinking")
    
    def speak_response(self, response):
        """Speak the response using TTS"""
        # Extract response text if it's a tuple
        response_text = response[0] if isinstance(response, tuple) else response
        self.tts_engine.speak(response_text)
    
    def on_speak_done(self):
        """Handle completion of speaking in GUI thread"""
        if self.current_state == "speaking":
            self.state_change_signal.emit("idle")
            self.reset_idle_timer()  # Reset sleep timer when done speaking

    def start_speaking(self):
        """Start speaking animation in GUI thread"""
        self.state_change_signal.emit("speaking")
        self.reset_idle_timer()  # Reset sleep timer when starting to speak

    def stop_speaking(self):
        """Stop speaking animation in GUI thread"""
        self.state_change_signal.emit("idle")
        self.reset_idle_timer()  # Reset sleep timer when stopping speech
    
    def contextMenuEvent(self, event):
        # Only show menu if not in transition
        if not self.in_transition:
            # Create action menu
            action_menu = QMenu(self)
            
            # Add actions
            fly_action = action_menu.addAction("Take Flight")
            fly_action.triggered.connect(lambda: self.state_change_signal.emit("take_flight"))
            
            look_action = action_menu.addAction("Look Around")
            look_action.triggered.connect(lambda: self.state_change_signal.emit("look_around"))
            
            # Add separator before quit
            action_menu.addSeparator()
            
            quit_action = action_menu.addAction("Quit")
            quit_action.triggered.connect(QApplication.quit)
            
            # Show the menu at cursor position
            action_menu.exec_(event.globalPos())

    def generate_bezier_points(self):
        """Generate a new random flight path using bezier curves"""
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
        """Get the current frame, flipping it if necessary"""
        if self.current_state in self.animations and self.animations[self.current_state]:
            current_frame = self.animations[self.current_state][self.frame_index]
            
            # Flip the sprite if facing left for flight-related animations and regular movement
            if not self.facing_right and (self.current_state in ["flying", "take_flight", "landing"] or self.dragging):
                transform = QTransform()
                transform.scale(-1, 1)  # Flip horizontally
                current_frame = current_frame.transformed(transform)
            
            return current_frame
        return None

    def showContextMenu(self, position):
        """Show context menu with settings"""
        menu = QMenu(self)
        
        # Add actions
        look_around_action = menu.addAction("Look Around")
        look_around_action.triggered.connect(lambda: self.state_change_signal.emit("look_around"))
        
        take_flight_action = menu.addAction("Take Flight")
        take_flight_action.triggered.connect(lambda: self.state_change_signal.emit("take_flight"))
        
        dance_action = menu.addAction("Dance")
        dance_action.triggered.connect(self.start_dance)
        
        screech_action = menu.addAction("Screech")
        screech_action.triggered.connect(self.screech)
        
        menu.addSeparator()
        
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.showSettings)
        
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        
        menu.exec_(self.mapToGlobal(position))
            
    def start_dance(self):
        """Start the dance animation with random number of loops"""
        self.dance_loops = 0
        self.dance_loops_target = random.randint(4, 20)  # Random number of loops between 4 and 20
        self.state_change_signal.emit("dance")

    def showSettings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            logger.info("Settings dialog accepted, reloading config")
            # Reload config
            self.config = self.load_config()
            logger.info(f"Reloaded config: {self.config}")
            
            # Update voice if changed
            selected_voice = dialog.getSelectedVoice()
            if selected_voice:
                self.tts_engine.change_voice(selected_voice)
                
            # Update sleep timer
            self.idle_timeout = self.config.get('sleep_timer', 30)
            logger.info(f"Updated sleep timer to {self.idle_timeout}")
            
            # Update display mode
            if self.display_manager:
                display_mode = self.config.get('display_mode', 'bubble')
                self.display_manager.initialize(display_mode)
            
            # Update voice assistant with new config
            if hasattr(self, 'voice_assistant') and self.voice_assistant:
                self.voice_assistant.reload_config()
                logger.info("Voice assistant config reloaded")
            
            # Reschedule random actions with new settings
            self.schedule_next_random_action()
            logger.info("Settings update complete")

    def load_config(self):
        """Load configuration from config.json"""
        config_path = get_resource_path('config.json')
        default_config = {
            'voice_type': 'Azure Voice',
            'voice_name': 'en-US-AnaNeural',
            'sleep_timer': 30,
            'personality_preset': 'ova',
            'display_mode': 'bubble',
            'ai_provider': 'ollama',
            'ai_settings': {
                'model': 'ova',
                'google_api_key': ''
            },
            'save_conversation_history': True
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    logger.info(f"Loaded config from {config_path}")
                    return {**default_config, **loaded_config}  # Merge with defaults
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        
        logger.info("Using default config")
        return default_config.copy()

    def check_idle(self):
        """Check if Ova has been idle for too long"""
        # Don't start sleeping if already asleep or in certain states
        if self.current_state in ['asleep', 'falling_asleep', 'waking_up', 'pickup', 'held', 'putdown', 
                                'take_flight', 'flying', 'landing', 'dance']:
            return
            
        # Don't sleep if currently speaking
        if hasattr(self, 'tts_engine') and self.tts_engine.is_speaking:
            return
            
        # Get sleep timer from config, default to 30 seconds
        sleep_timer = self.config.get('sleep_timer', 30)
            
        if time.time() - self.last_active > sleep_timer:
            self.state_change_signal.emit("falling_asleep")

    def fall_asleep(self):
        """Start the falling asleep animation"""
        self.state_change_signal.emit("falling_asleep")

    def wake_up(self):
        """Wake up from sleep"""
        if self.current_state in ['asleep', 'falling_asleep']:
            self.state_change_signal.emit("waking_up")
            self.reset_idle_timer()

    def reset_idle_timer(self):
        """Reset the idle timer"""
        self.last_active = time.time()

    def paintEvent(self, event):
        """Custom paint event to ensure pixel-perfect rendering"""
        if not self.animations:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)  # Disable antialiasing
        painter.setRenderHint(QPainter.Antialiasing, False)
        
        current_frame = self.get_current_frame()
        if current_frame:
            painter.drawPixmap(self.rect(), current_frame)

    def start_listening(self):
        """Start listening animation in GUI thread"""
        print("Starting listening animation")
        self.state_change_signal.emit("listening")
        self.reset_idle_timer()

    def stop_listening(self):
        """Stop listening animation in GUI thread"""
        print("Stopping listening animation")
        if self.current_state == "listening":
            self.state_change_signal.emit("idle")
            self.reset_idle_timer()

    def screech(self):
        """Play a random screech sound and animate"""
        try:
            # Get list of screech sound files
            screech_dir = get_resource_path(os.path.join('assets', 'sounds', 'screeches'))
            screech_files = glob.glob(os.path.join(screech_dir, '*.mp3'))
            
            if screech_files:
                # Choose random screech
                screech_file = random.choice(screech_files)
                
                # Load and play the sound
                sound = pygame.mixer.Sound(screech_file)
                
                # Start speaking animation
                self.state_change_signal.emit("speaking")
                
                # Play the sound
                channel = sound.play()
                
                # Create a timer to check when sound is done
                check_timer = QTimer(self)
                check_timer.timeout.connect(lambda: self.check_screech_done(channel))
                check_timer.start(100)  # Check every 100ms
                
        except Exception as e:
            print(f"Error playing screech: {e}")
            self.state_change_signal.emit("idle")
    
    def check_screech_done(self, channel):
        """Check if screech sound is finished playing"""
        if not channel.get_busy():
            # Sound is done, stop the timer
            self.sender().stop()
            # Return to idle
            self.state_change_signal.emit("idle")

    def schedule_next_random_action(self):
        """Schedule the next random action based on config settings"""
        if not self.config.get('enable_random_actions', True):
            return
            
        min_interval = self.config.get('min_action_interval', 5)
        max_interval = self.config.get('max_action_interval', 10)
        
        # Convert to milliseconds
        interval = random.randint(min_interval * 1000, max_interval * 1000)
        
        # Reset and start timer
        if hasattr(self, 'random_action_timer'):
            self.random_action_timer.stop()
        self.random_action_timer = QTimer(self)
        self.random_action_timer.timeout.connect(self.perform_random_action)
        self.random_action_timer.setSingleShot(True)  # Only trigger once
        self.random_action_timer.start(interval)
    
    def perform_random_action(self):
        """Perform a random action from the enabled actions list"""
        # Only perform actions if we're in idle state
        if self.current_state != "idle":
            return
            
        # Get enabled actions
        enabled_actions = self.config.get('enabled_actions', {})
        available_actions = [
            action for action, enabled in enabled_actions.items()
            if enabled
        ]
        
        if available_actions:
            # Choose random action
            action = random.choice(available_actions)
            
            # Perform the chosen action
            if action == 'take_flight':
                self.state_change_signal.emit("take_flight")
            elif action == 'look_around':
                self.state_change_signal.emit("look_around")
            elif action == 'dance':
                self.start_dance()
            elif action == 'screech':
                self.screech()
        
        # Schedule next action
        self.schedule_next_random_action()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when window is closed
    pet = OwlPet()
    sys.exit(app.exec_())
