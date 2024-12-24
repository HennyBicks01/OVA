from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QLabel, QPushButton, QGroupBox, QTabWidget, QWidget, QSpinBox)
from PyQt5.QtCore import Qt
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setModal(True)
        self.config = self.load_config()
        self.initUI()
        
    def load_config(self):
        """Load configuration from config.json"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        default_config = {
            'voice_type': 'Azure Voice',
            'voice_name': 'en-US-AnaNeural',
            'sleep_timer': 30,
            'personality_preset': 'ova',
            'display_mode': 'bubble'
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    logger.info(f"Loaded config: {loaded_config}")
                    return loaded_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        
        logger.info("Using default config")
        return default_config.copy()
    
    def save_config(self):
        """Save configuration to config.json"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        try:
            logger.info(f"Saving config: {self.config}")
            with open(config_path, 'w') as f:
                json.dump(self.config, f)
            logger.info("Config saved successfully")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get_available_presets(self):
        """Get list of available preset files"""
        presets_dir = os.path.join(os.path.dirname(__file__), 'presets')
        presets = []
        if os.path.exists(presets_dir):
            for file in os.listdir(presets_dir):
                if file.endswith('.txt'):
                    presets.append(os.path.splitext(file)[0])
        logger.info(f"Available presets: {presets}")
        return sorted(presets)

    def initUI(self):
        layout = QVBoxLayout()
        
        # Create tab widget
        tabs = QTabWidget()
        
        # General Settings Tab
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        
        # Preset Selection Group
        preset_group = QGroupBox("System Preset")
        preset_group_layout = QHBoxLayout()
        
        # Preset Selection
        self.preset_selection = QComboBox()
        self.preset_selection.addItems(self.get_available_presets())
        preset_group_layout.addWidget(QLabel("Preset:"))
        preset_group_layout.addWidget(self.preset_selection)
        
        preset_group.setLayout(preset_group_layout)
        general_layout.addWidget(preset_group)
        
        # Display Mode Group
        display_group = QGroupBox("Display Settings")
        display_group_layout = QHBoxLayout()
        
        # Display Mode Selection
        self.display_mode = QComboBox()
        self.display_mode.addItems(["Speech Bubble", "Chat Window", "No Display"])
        display_group_layout.addWidget(QLabel("Display Mode:"))
        display_group_layout.addWidget(self.display_mode)
        
        display_group.setLayout(display_group_layout)
        general_layout.addWidget(display_group)
        
        general_tab.setLayout(general_layout)

        # Voice Settings Tab
        voice_tab = QWidget()
        voice_layout = QVBoxLayout()
        
        # Voice Selection Group
        voice_group = QGroupBox("Voice Selection")
        voice_group_layout = QVBoxLayout()
        
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
        
        voice_group_layout.addLayout(type_layout)
        voice_group_layout.addLayout(voice_selection_layout)
        voice_group.setLayout(voice_group_layout)
        voice_layout.addWidget(voice_group)
        voice_tab.setLayout(voice_layout)
        
        # Behavior Settings Tab
        behavior_tab = QWidget()
        behavior_layout = QVBoxLayout()
        
        # Sleep Timer Group
        sleep_group = QGroupBox("Sleep Timer")
        sleep_group_layout = QHBoxLayout()
        
        # Sleep Timer Input
        self.sleep_timer = QSpinBox()
        self.sleep_timer.setMinimum(5)  # Minimum 5 seconds
        self.sleep_timer.setMaximum(3600)  # Maximum 1 hour
        self.sleep_timer.setValue(self.config.get('sleep_timer', 30))  # Default 30 seconds
        self.sleep_timer.setSuffix(" seconds")
        
        sleep_group_layout.addWidget(QLabel("Time before sleep:"))
        sleep_group_layout.addWidget(self.sleep_timer)
        sleep_group.setLayout(sleep_group_layout)
        behavior_layout.addWidget(sleep_group)
        behavior_tab.setLayout(behavior_layout)
        
        # Add tabs
        tabs.addTab(general_tab, "General")
        tabs.addTab(voice_tab, "Voice")
        tabs.addTab(behavior_tab, "Behavior")
        layout.addWidget(tabs)
        
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
        preset = self.config.get('personality_preset', 'ova')
        display_mode = self.config.get('display_mode', 'bubble')
        
        # Set preset
        index = self.preset_selection.findText(preset)
        if index >= 0:
            self.preset_selection.setCurrentIndex(index)
        
        # Set display mode
        mode_map = {'bubble': 'Speech Bubble', 'chat': 'Chat Window', 'none': 'No Display'}
        mode_text = mode_map.get(display_mode, 'Speech Bubble')
        index = self.display_mode.findText(mode_text)
        if index >= 0:
            self.display_mode.setCurrentIndex(index)
        
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
            
    def accept(self):
        """Called when Save button is clicked"""
        logger.info("Save button clicked")
        
        # Update config with current values
        self.config['voice_type'] = self.voice_type.currentText()
        self.config['voice_name'] = self.voice_selection.currentText()
        self.config['sleep_timer'] = self.sleep_timer.value()
        self.config['personality_preset'] = self.preset_selection.currentText()
        
        # Map display mode text to config value
        mode_map = {'Speech Bubble': 'bubble', 'Chat Window': 'chat', 'No Display': 'none'}
        self.config['display_mode'] = mode_map.get(self.display_mode.currentText(), 'bubble')
        
        # Save config
        self.save_config()
        
        # Call parent accept to close dialog
        super().accept()
    
    def getSelectedVoice(self):
        """Get the selected voice"""
        voice_type = self.voice_type.currentText()
        voice = self.voice_selection.currentText()
        
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
