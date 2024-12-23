import pyttsx3
from PyQt5.QtCore import QObject, pyqtSignal
import threading

class TTSEngine(QObject):
    speak_started = pyqtSignal()
    speak_finished = pyqtSignal()
    speak_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.engine = None
        self.setup_engine()
    
    def setup_engine(self):
        """Setup text-to-speech engine with child voice"""
        try:
            self.engine = pyttsx3.init()
            
            # Configure for child-like voice
            voices = self.engine.getProperty('voices')
            # Try to find a child-like or female voice
            child_voice = None
            for voice in voices:
                if 'child' in voice.name.lower() or 'female' in voice.name.lower():
                    child_voice = voice
                    break
            
            # Set voice if found, otherwise use default
            if child_voice:
                self.engine.setProperty('voice', child_voice.id)
            
            # Adjust properties for child-like speech
            self.engine.setProperty('rate', 150)  # Slightly faster than default
            self.engine.setProperty('pitch', 150)  # Higher pitch
            self.engine.setProperty('volume', 0.9)  # Slightly quieter
            
        except Exception as e:
            print(f"Error setting up TTS engine: {e}")
            self.speak_error.emit(str(e))
    
    def speak(self, text):
        """Speak text using TTS in a separate thread"""
        def speak_thread():
            try:
                if not self.engine:
                    self.setup_engine()
                
                self.speak_started.emit()
                self.engine.say(text)
                self.engine.runAndWait()
                self.speak_finished.emit()
                
            except Exception as e:
                print(f"Error in TTS: {e}")
                self.speak_error.emit(str(e))
        
        # Run in a separate thread to avoid blocking
        threading.Thread(target=speak_thread, daemon=True).start()
