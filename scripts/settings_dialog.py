from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QLabel, QPushButton, QGroupBox)
from PyQt5.QtCore import Qt
from config import load_config, save_config

class VoiceSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Voice Settings")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setModal(True)
        self.config = load_config()
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Voice Selection Group
        voice_group = QGroupBox("Voice Selection")
        voice_layout = QVBoxLayout()
        
        # Voice Type Selection
        type_layout = QHBoxLayout()
        self.voice_type = QComboBox()
        self.voice_type.addItems(["Azure Voice", "Windows Voice"])
        self.voice_type.currentTextChanged.connect(self.onVoiceTypeChanged)
        type_layout.addWidget(QLabel("Voice Type:"))
        type_layout.addWidget(self.voice_type)
        
        # Voice Selection
        voice_selection_layout = QHBoxLayout()
        self.voice_selection = QComboBox()
        voice_selection_layout.addWidget(QLabel("Voice:"))
        voice_selection_layout.addWidget(self.voice_selection)
        
        voice_layout.addLayout(type_layout)
        voice_layout.addLayout(voice_selection_layout)
        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Load saved settings
        self.loadSavedSettings()
        
    def loadSavedSettings(self):
        """Load and apply saved settings"""
        voice_type = self.config.get('voice_type', 'Azure Voice')
        voice_name = self.config.get('voice_name', 'en-US-AnaNeural')
        
        # Set voice type
        index = self.voice_type.findText(voice_type)
        if index >= 0:
            self.voice_type.setCurrentIndex(index)
        
        # Populate voice selection
        self.onVoiceTypeChanged(voice_type)
        
        # Set voice name
        index = self.voice_selection.findText(voice_name)
        if index >= 0:
            self.voice_selection.setCurrentIndex(index)
        
    def onVoiceTypeChanged(self, voice_type):
        self.voice_selection.clear()
        if voice_type == "Azure Voice":
            self.voice_selection.addItems([
                "en-US-AnaNeural",
                "en-US-JennyNeural",
                "en-US-SaraNeural",
                "en-US-AmyNeural"
            ])
        else:  # Windows Voice
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            self.voice_selection.addItems([voice.name for voice in voices])
            engine.stop()
            
    def getSelectedVoice(self):
        """Get the selected voice and save settings"""
        voice_type = self.voice_type.currentText()
        voice = self.voice_selection.currentText()
        
        # Save settings
        self.config['voice_type'] = voice_type
        self.config['voice_name'] = voice
        save_config(self.config)
        
        if voice_type == "Azure Voice":
            return voice
        else:
            # For Windows voices, we need to find the matching voice ID
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            for v in voices:
                if v.name == voice:
                    engine.stop()
                    return v.id
            engine.stop()
            return None
