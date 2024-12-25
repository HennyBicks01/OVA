from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt
from .chat_display import ChatDisplay
from .speech_bubble import SpeechBubble
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DisplayManager:
    """Manages different display modes for Ova's responses"""
    
    DISPLAY_MODES = {
        "none": "No Display",
        "bubble": "Speech Bubble",
        "chat": "Chat Window"
    }
    
    def __init__(self, parent=None):
        self.parent = parent
        self.current_mode = "bubble"  # Default mode
        self.chat_display = None
        self.speech_bubble = None
        
    def initialize(self, mode="bubble"):
        """Initialize display with specified mode"""
        self.current_mode = mode
        logger.info(f"Initializing display manager with mode: {mode}")
        
        if mode == "chat":
            if not self.chat_display:
                self.chat_display = ChatDisplay(self.parent)
                # Position on left side of screen
                screen = QApplication.primaryScreen().geometry()
                # Set size to 1/3 of screen width and full height
                width = screen.width() // 3
                height = screen.height() - 100  # Leave some margin
                self.chat_display.resize(width, height)
                # Position at left edge with some margin
                self.chat_display.move(20, 50)
            self.chat_display.show()
            if self.speech_bubble:
                self.speech_bubble.hide()
                
        elif mode == "bubble":
            if not self.speech_bubble:
                self.speech_bubble = SpeechBubble(self.parent)
            if self.chat_display:
                self.chat_display.hide()
                
        else:  # mode == "none"
            if self.speech_bubble:
                self.speech_bubble.hide()
            if self.chat_display:
                self.chat_display.hide()
    
    def show_message(self, message_data, user_text=""):
        """Display a message in the current mode"""
        logger.info(f"Showing message in mode {self.current_mode}")
        
        # Handle tuple of (response, last_text) or just text
        text = message_data[0] if isinstance(message_data, tuple) else message_data
        user_text = message_data[1] if isinstance(message_data, tuple) else user_text
        
        if self.current_mode == "chat":
            if not self.chat_display:
                self.initialize("chat")
            if user_text:
                self.chat_display.add_message(user_text, is_user=True)
            if text:  # Only add non-empty messages
                self.chat_display.add_message(text, is_user=False)
            
        elif self.current_mode == "bubble":
            if not self.speech_bubble:
                self.initialize("bubble")
            if text or user_text:  # Only update if there's text
                self.speech_bubble.setText(text, user_text)
                # Let parent handle positioning
                if hasattr(self.parent, 'update_speech_bubble_position'):
                    self.parent.update_speech_bubble_position()
                self.speech_bubble.show()
    
    def hide_all(self):
        """Hide all displays"""
        if self.speech_bubble:
            self.speech_bubble.hide()
        if self.chat_display:
            self.chat_display.hide()
    
    def get_speech_bubble(self):
        """Get speech bubble widget"""
        if not self.speech_bubble and self.current_mode == "bubble":
            self.initialize("bubble")
        return self.speech_bubble
    
    def get_chat_display(self):
        """Get chat display widget"""
        if not self.chat_display and self.current_mode == "chat":
            self.initialize("chat")
        return self.chat_display
    
    def clear_history(self):
        """Clear chat history"""
        if self.chat_display:
            self.chat_display.clear_history()
            
    def change_mode(self, mode):
        """Change display mode"""
        if mode in self.DISPLAY_MODES:
            logger.info(f"Changing display mode to: {mode}")
            self.initialize(mode)
        else:
            logger.error(f"Invalid display mode: {mode}")