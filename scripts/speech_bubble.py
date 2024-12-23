from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QMetaObject, Q_ARG
from PyQt5.QtWidgets import QApplication

class SpeechBubbleWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Create main layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Create main content widget
        self.content = QWidget(self)
        self.content.setStyleSheet("""
            QWidget {
                background-color: #fff;
                border: 3px solid #888;
                border-radius: 10px;
            }
        """)
        self.layout.addWidget(self.content)
        
        # Create content layout
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(0)
        
        # Create label for the question
        self.question_label = QLabel()
        self.question_label.setStyleSheet("""
            QLabel {
                border: none;
                background-color: transparent;
                font-family: 'Comic Sans MS', cursive;
                font-size: 11px;
                color: #666666;
                font-style: italic;
            }
        """)
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.content_layout.addWidget(self.question_label)
        
        # Create divider line
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setStyleSheet("""
            QFrame {
                border: none;
                background-color: #CCCCCC;
                max-height: 1px;
                margin-top: 4px;
                margin-bottom: 4px;
            }
        """)
        self.content_layout.addWidget(self.divider)
        
        # Create the label for response text
        self.response_label = QLabel()
        self.response_label.setStyleSheet("""
            QLabel {
                border: none;
                background-color: transparent;
                font-family: 'Comic Sans MS', cursive;
                font-size: 14px;
                color: #333333;
                min-width: 200px;
                max-width: 400px;
            }
        """)
        self.response_label.setWordWrap(True)
        self.response_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.content_layout.addWidget(self.response_label)
    
    def setText(self, text, question=""):
        # Ensure this runs in the GUI thread
        if not self.thread() == QApplication.instance().thread():
            QMetaObject.invokeMethod(self, 'setText',
                                   Qt.QueuedConnection,
                                   Q_ARG(str, text),
                                   Q_ARG(str, question))
            return
            
        # Set maximum width for text wrapping
        screen = QApplication.primaryScreen().geometry()
        max_width = min(screen.width() - 100, 400)
        
        # Set and adjust question text if provided
        if question:
            self.question_label.setText(question)
            self.question_label.setMaximumWidth(max_width)
            self.question_label.show()
            self.divider.show()
        else:
            self.question_label.hide()
            self.divider.hide()
        
        # Set and adjust response text
        self.response_label.setText(text)
        self.response_label.setMaximumWidth(max_width)
        
        # Force layout update
        self.content_layout.activate()
        self.layout.activate()
        
        # Update sizes
        self.content.adjustSize()
        self.adjustSize()
    
    def showAtPosition(self, x, y):
        """Show the speech bubble at the specified position"""
        # Ensure this runs in the GUI thread
        if not self.thread() == QApplication.instance().thread():
            QMetaObject.invokeMethod(self, 'showAtPosition',
                                   Qt.QueuedConnection,
                                   Q_ARG(int, x),
                                   Q_ARG(int, y))
            return
            
        self.move(x, y)
        self.show()
    
    def hide(self):
        """Hide the speech bubble"""
        # Ensure this runs in the GUI thread
        if not self.thread() == QApplication.instance().thread():
            QMetaObject.invokeMethod(self, 'hide',
                                   Qt.QueuedConnection)
            return
            
        super().hide()
