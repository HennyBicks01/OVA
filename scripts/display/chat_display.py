from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame
from PyQt5.QtCore import Qt, QTimer
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatDisplay(QWidget):
    """A scrollable chat window that shows the conversation history"""
    
    def __init__(self, parent=None):
        super().__init__(None)  # Set parent to None to make it a separate window
        self.owner = parent  # Keep reference to owner for positioning
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setup_ui()
        
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
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)  # Add spacing between messages
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.1);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 0.2);
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        content_layout.addWidget(scroll)
        
        # Create message container
        self.message_container = QWidget()
        self.message_container.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        self.messages_layout = QVBoxLayout(self.message_container)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.setSpacing(15)  # Add spacing between messages
        self.messages_layout.addStretch()
        scroll.setWidget(self.message_container)
        
    def create_message_label(self, text, is_user=False):
        """Create a styled message label"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add sender label
        sender = QLabel("You:" if is_user else "Ova:")
        sender.setStyleSheet("""
            QLabel {
                color: #666666;
                font-family: Segoe UI;
                font-size: 11px;
                font-weight: bold;
                padding: 0px 10px;
            }
        """)
        sender.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(sender)
        
        # Add message label
        message = QLabel(text)
        message.setWordWrap(True)
        message.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message.setStyleSheet(f"""
            QLabel {{
                background-color: {'rgba(240, 240, 240, 0.95)' if is_user else 'rgba(220, 240, 255, 0.95)'};
                border-radius: 10px;
                padding: 10px;
                font-family: Segoe UI;
                font-size: {'12px' if is_user else '13px'};
                color: #333333;
                margin-{'right' if is_user else 'left'}: 50px;
            }}
        """)
        layout.addWidget(message)
        
        return container
        
    def add_message(self, text, is_user=False):
        """Add a message to the chat window"""
        # Create message widget
        message = self.create_message_label(text, is_user)
        
        # Insert message before the stretch
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, message)
        
        # Scroll to bottom
        QTimer.singleShot(100, self.scroll_to_bottom)
        
    def scroll_to_bottom(self):
        """Scroll to the bottom of the chat"""
        scroll = self.findChild(QScrollArea)
        if scroll:
            vsb = scroll.verticalScrollBar()
            vsb.setValue(vsb.maximum())
                
    def clear_history(self):
        """Clear all messages from the chat"""
        while self.messages_layout.count() > 1:  # Keep the stretch
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()