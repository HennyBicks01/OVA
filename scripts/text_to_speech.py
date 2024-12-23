import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
import pyttsx3
from PyQt5.QtCore import QObject, pyqtSignal
import threading
from config import load_config, save_config

# Load environment variables
load_dotenv()

class TTSEngine(QObject):
    speak_started = pyqtSignal()
    speak_finished = pyqtSignal()
    speak_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.speech_config = None
        self.speech_synthesizer = None
        self.windows_engine = None
        self.use_fallback = False
        self.config = load_config()
        self.is_speaking = False
        self.setup_engine()
    
    def setup_engine(self):
        """Setup Azure text-to-speech engine with fallback to Windows voices"""
        try:
            # First set up Windows engine as fallback
            self.windows_engine = pyttsx3.init()
            voices = self.windows_engine.getProperty('voices')
            
            # Get saved voice settings
            voice_type = self.config.get('voice_type', 'Azure Voice')
            voice_name = self.config.get('voice_name', 'en-US-AnaNeural')
            
            # Configure Windows voice
            if len(voices) > 0:
                if voice_type == 'Windows Voice':
                    self.windows_engine.setProperty('voice', voice_name)
                else:
                    # Use first available voice as fallback
                    self.windows_engine.setProperty('voice', voices[0].id)
            
            self.windows_engine.setProperty('rate', 150)
            self.windows_engine.setProperty('pitch', 270)
            self.windows_engine.setProperty('volume', 0.9)
            
            # If Windows voice is selected, don't try Azure
            if voice_type == 'Windows Voice':
                self.use_fallback = True
                return
            
            # Now try to set up Azure
            speech_key = os.getenv('AZURE_SPEECH_KEY')
            speech_region = os.getenv('AZURE_SPEECH_REGION')
            
            if not speech_key or not speech_region:
                self.use_fallback = True
                return
            
            # Initialize Azure Speech config
            self.speech_config = speechsdk.SpeechConfig(
                subscription=speech_key, 
                region=speech_region
            )
            
            # Set to use saved Azure voice
            self.speech_config.speech_synthesis_voice_name = voice_name
            
            # Create speech synthesizer
            self.speech_synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config
            )
            
        except Exception as e:
            self.use_fallback = True
            self.speak_error.emit(f"Falling back to Windows voices: {str(e)}")

    def change_voice(self, voice_name):
        """Change the voice being used
        
        Args:
            voice_name (str): For Azure, the full voice name (e.g., 'en-US-AnaNeural')
                            For Windows, the voice ID from Windows SAPI5
        """
        try:
            if "Neural" in voice_name:  # Azure voice
                # Get Azure credentials
                speech_key = os.getenv('AZURE_SPEECH_KEY')
                speech_region = os.getenv('AZURE_SPEECH_REGION')
                
                if not speech_key or not speech_region:
                    raise ValueError("Azure credentials not found")
                
                # Initialize Azure Speech config if needed
                if not self.speech_config:
                    self.speech_config = speechsdk.SpeechConfig(
                        subscription=speech_key,
                        region=speech_region
                    )
                
                # Update voice
                self.speech_config.speech_synthesis_voice_name = voice_name
                self.speech_synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=self.speech_config
                )
                self.use_fallback = False
                
                # Update config
                self.config['voice_type'] = 'Azure Voice'
                self.config['voice_name'] = voice_name
                
            else:  # Windows voice
                if not self.windows_engine:
                    self.windows_engine = pyttsx3.init()
                self.windows_engine.setProperty('voice', voice_name)
                self.use_fallback = True
                
                # Update config
                self.config['voice_type'] = 'Windows Voice'
                self.config['voice_name'] = voice_name
            
            # Save the updated config
            save_config(self.config)
            
        except Exception as e:
            self.use_fallback = True
            self.speak_error.emit(f"Failed to set voice, falling back to Windows: {str(e)}")
            
            # Try to set up Windows fallback if not already done
            if not self.windows_engine:
                try:
                    self.windows_engine = pyttsx3.init()
                    voices = self.windows_engine.getProperty('voices')
                    if voices:
                        self.windows_engine.setProperty('voice', voices[0].id)
                except Exception as we:
                    self.speak_error.emit(f"Failed to set up Windows fallback: {str(we)}")
    
    def speak(self, text):
        """Speak text using Azure TTS with fallback to Windows voices"""
        if self.use_fallback:
            self._speak_windows(text)
        else:
            self._speak_azure(text)
    
    def _speak_windows(self, text):
        """Fallback method using Windows voices"""
        def speak_thread():
            try:
                self.is_speaking = True
                self.speak_started.emit()
                self.windows_engine.say(text)
                self.windows_engine.runAndWait()
                self.is_speaking = False
                self.speak_finished.emit()
            except Exception as e:
                self.is_speaking = False
                self.speak_error.emit(str(e))
        
        threading.Thread(target=speak_thread, daemon=True).start()
    
    def _speak_azure(self, text):
        """Primary method using Azure TTS"""
        def speak_thread():
            try:
                self.is_speaking = True
                self.speak_started.emit()
                result = self.speech_synthesizer.speak_text_async(text).get()
                
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    self.is_speaking = False
                    self.speak_finished.emit()
                else:
                    # If Azure fails, switch to fallback and retry
                    self.use_fallback = True
                    self.speak_error.emit("Azure synthesis failed, switching to Windows voices")
                    self._speak_windows(text)
                    
            except Exception as e:
                # If Azure fails, switch to fallback and retry
                self.use_fallback = True
                self.speak_error.emit(f"Azure error, switching to Windows voices: {str(e)}")
                self._speak_windows(text)
        
        threading.Thread(target=speak_thread).start()
