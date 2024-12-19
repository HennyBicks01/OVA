import sys
import os
import random
import glob
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QSystemTrayIcon, QMenu
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QImage, QIcon

class OwlPet(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.loadAnimations()
        self.current_state = "idle"
        self.frame_index = 0
        self.dragging = False
        self.offset = QPoint()
        
        # Set initial size
        self.setMinimumSize(100, 100)
        
        # Animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.updateAnimation)
        self.animation_timer.start(100)  # Update every 100ms
        
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
        desktop = QApplication.desktop().screenGeometry()
        self.move(desktop.width() - 200, desktop.height() - 200)
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

    def updateAnimation(self):
        if self.current_state in self.animations:
            frames = self.animations[self.current_state]
            if frames:
                self.frame_index = (self.frame_index + 1) % len(frames)
                self.sprite_label.setPixmap(frames[self.frame_index])
                
                # Handle transition states
                if self.frame_index == len(frames) - 1:  # At the last frame
                    if self.current_state in ["take_flight", "landing", "pruning"]:
                        next_state = self.state_transitions[self.current_state][0]
                        self.changeState(next_state)
                
                self.adjustSize()

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
            self.move(self.mapToGlobal(event.pos() - self.offset))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def contextMenuEvent(self, event):
        # Right-click to dance only if not in transition
        if not self.in_transition:
            self.changeState("dance")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when window is closed
    pet = OwlPet()
    sys.exit(app.exec_())
