import sys
import os
import random
import glob
import math
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QSystemTrayIcon, QMenu
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QImage, QIcon, QTransform

class OwlPet(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.loadAnimations()
        self.current_state = "idle"
        self.frame_index = 0
        self.dragging = False
        self.offset = QPoint()
        self.facing_right = True
        self.last_pos = None
        
        # Flying movement variables
        self.flying_start = None
        self.flying_end = None
        self.flying_progress = 0
        self.flying_control_points = []
        
        # Set initial size
        self.setMinimumSize(100, 100)
        
        # Animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.updateAnimation)
        self.animation_timer.start(50)  # Update every 50ms for smoother animation
        
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

    def initUI(self):
        # Create a window without frame that stays on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Create label for the sprite
        self.sprite_label = QLabel(self)
        self.sprite_label.setMinimumSize(64, 64)  # Set minimum size
        self.setCentralWidget(self.sprite_label)
        
        # Set initial position
        self.desktop = QApplication.desktop().screenGeometry()
        initial_pos = QPoint(self.desktop.width() - 200, self.desktop.height() - 200)
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
                    self.animations[anim_dir] = [QPixmap(frame).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation) for frame in frames]

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
        if self.current_state in self.animations:
            frames = self.animations[self.current_state]
            if frames:
                self.frame_index = (self.frame_index + 1) % len(frames)
                
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
                
                # Update sprite with current frame (and flip if needed)
                current_frame = self.get_current_frame()
                if current_frame:
                    self.sprite_label.setPixmap(current_frame)
                
                # Handle transition states
                if self.frame_index == len(frames) - 1:  # At the last frame
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
        self.current_state = new_state
        self.frame_index = 0
        self.in_transition = new_state in ["take_flight", "landing", "pruning"]

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
            if not self.in_transition:
                self.changeState("idle")

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = self.mapToGlobal(event.pos() - self.offset)
            self.update_facing_direction(new_pos)
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when window is closed
    pet = OwlPet()
    sys.exit(app.exec_())
