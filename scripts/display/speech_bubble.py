from PyQt5.QtWidgets import QLabel, QVBoxLayout, QFrame, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFontDatabase, QFont
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SpeechBubble(QWidget):
    """A floating speech bubble that appears near the Ova pet"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Load Roboto font if available, otherwise fallback to system sans-serif
        font_id = QFontDatabase.addApplicationFont("assets/fonts/Roboto-Regular.ttf")
        if font_id != -1:
            self.font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        else:
            self.font_family = "Segoe UI"  # Modern Windows default
            
        self.setup_ui()
        self.hide_timer = None
        
    def setup_ui(self):
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create main content widget
        self.content = QWidget(self)
        self.content.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
            }
        """)
        layout.addWidget(self.content)
        
        # Create content layout
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(8)
        
        # Create labels for user text and response
        self.user_label = QLabel()
        self.user_label.setStyleSheet(f"""
            QLabel {{
                color: #666;
                font-family: "{self.font_family}";
                font-size: 11px;
                font-style: italic;
                background: transparent;
                padding: -14px 0;
                border: none;
            }}
        """)
        self.user_label.setWordWrap(True)
        self.user_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content_layout.addWidget(self.user_label)
        
        # Create divider
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setStyleSheet("background-color: #ccc;")
        content_layout.addWidget(self.divider)
        
        # Create response label
        self.response_label = QLabel()
        self.response_label.setStyleSheet(f"""
            QLabel {{
                color: #333;
                font-family: "{self.font_family}";
                font-size: 14px;
                line-height: 1.4;
                background: transparent;
                padding: 0;
                border: none;
            }}
        """)
        self.response_label.setWordWrap(True)
        self.response_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content_layout.addWidget(self.response_label)
        
        # Set size constraints
        self.setMinimumWidth(250)
        self.setMaximumWidth(450)
        
    def setText(self, text, last_text=""):
        """Set the text of the speech bubble"""
        # Update user text if provided
        if last_text:
            self.user_label.setText(f"You: {last_text}")
            self.user_label.show()
            self.divider.show()
        else:
            self.user_label.hide()
            self.divider.hide()
        
        # Update response text
        self.response_label.setText(text)
        
        # Adjust size
        self.adjustSize()
        
    def showMessage(self, text, duration=5000):
        """Show the speech bubble with text for a duration"""
        self.setText(text)
        self.show()
        
        # Reset timer if exists
        if self.hide_timer:
            self.hide_timer.stop()
            
        # Start new timer
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.hideAndReset)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.start(duration)
        
    def hideAndReset(self):
        """Hide the bubble and notify parent to reset sleep timer"""
        self.hide()
        if self.parent():
            self.parent().reset_idle_timer()
            
    def showAtPosition(self, x, y):
        """Show the speech bubble at the specified position"""
        self.move(x, y)
        self.show()
