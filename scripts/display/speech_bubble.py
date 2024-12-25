from PyQt5.QtWidgets import QLabel, QVBoxLayout, QFrame, QWidget, QSizePolicy, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer, QSize
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
        # Set size policy
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
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
        self.content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout.addWidget(self.content)
        
        # Create content layout
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(15, 10, 15, 10)
        content_layout.setSpacing(4)
        
        # Create top row with user text and close button
        top_row = QHBoxLayout()
        
        # Create labels for user text and response
        self.user_label = QLabel()
        self.user_label.setStyleSheet(f"""
            QLabel {{
                color: #666;
                font-family: "{self.font_family}";
                font-size: 11px;
                font-style: italic;
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
                max-height: 25px;
            }}
        """)
        self.user_label.setWordWrap(True)
        self.user_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.user_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        top_row.addWidget(self.user_label)
        
        # Add close button
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(16, 16)
        self.close_button.setStyleSheet("""
            QPushButton {
                color: #ff4444;
                background: transparent;
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 0;
                margin: 0;
            }
            QPushButton:hover {
                color: #ff0000;
            }
        """)
        self.close_button.clicked.connect(self.hide)
        top_row.addWidget(self.close_button)
        
        content_layout.addLayout(top_row)
        
        # Create divider
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setStyleSheet("""
            background-color: #ccc;
            margin: 5px 0 1px 0;
        """)
        self.divider.setFixedHeight(1)
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
                border: none;
                padding: 0;
                margin: 0;
            }}
        """)
        self.response_label.setWordWrap(True)
        self.response_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.response_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        content_layout.addWidget(self.response_label)
        
        # Set size constraints
        self.setMinimumSize(QSize(250, 100))
        self.setMaximumSize(QSize(1200, 1200))
        
    def sizeHint(self):
        """Return the recommended size for the widget"""
        width = max(250, min(self.content.sizeHint().width() + 30, 1200))
        height = max(100, min(self.content.sizeHint().height() + 30, 1200))
        return QSize(width, height)
        
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
        
        # Update size
        hint = self.sizeHint()
        self.resize(hint)
        
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
