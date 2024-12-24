import os
import pyttsx3
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import threading
import json
import logging
import asyncio
import edge_tts
import tempfile
import pygame
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize pygame mixer
pygame.mixer.init()

class TTSWorker(QThread):
    """Worker thread for TTS playback"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, temp_file, voice):
        super().__init__()
        self.temp_file = temp_file
        self.voice = voice
        self.text = None
        
    def set_text(self, text):
        self.text = text
        
    def run(self):
        try:
            # Create communicate instance and save audio
            communicate = edge_tts.Communicate(self.text, self.voice)
            
            # Create event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Generate audio file
                loop.run_until_complete(communicate.save(self.temp_file))
                
                # Play audio
                pygame.mixer.music.load(self.temp_file)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                    
            finally:
                loop.close()
                
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
        finally:
            # Cleanup
            try:
                pygame.mixer.music.unload()
                os.remove(self.temp_file)
            except:
                pass

class TTSEngine(QObject):
    speak_started = pyqtSignal()
    speak_finished = pyqtSignal()
    speak_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.windows_engine = None
        self.use_fallback = False
        self.config = self.load_config()
        self.is_speaking = False
        self.temp_dir = tempfile.mkdtemp()
        self.tts_worker = None
        self.setup_engine()
        
        # Log initial state
        logger.info(f"TTS Engine initialized with config: {self.config}")
        logger.info(f"Using fallback: {self.use_fallback}")
    
    def load_config(self):
        """Load configuration from config.json"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        default_config = {
            'voice_type': 'Edge Voice',
            'voice_name': 'en-US-AnaNeural',
            'sleep_timer': 30,
            'personality_preset': 'ova'
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    logger.info(f"TTS loaded config: {loaded_config}")
                    return loaded_config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        
        return default_config.copy()

    async def _list_voices(self):
        """List available Edge TTS voices"""
        try:
            voices = await edge_tts.list_voices()
            logger.info("Available Edge TTS voices:")
            for voice in voices:
                logger.info(f"- {voice['ShortName']}")
            return voices
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            return []

    def setup_engine(self):
        """Setup Edge TTS engine with fallback to Windows voices"""
        try:
            # First set up Windows engine as fallback
            self.windows_engine = pyttsx3.init()
            voices = self.windows_engine.getProperty('voices')
            
            # Get saved voice settings
            voice_type = self.config.get('voice_type', 'Edge Voice')
            voice_name = self.config.get('voice_name', 'en-US-AnaNeural')
            
            logger.info(f"Setting up TTS with voice type: {voice_type}, voice name: {voice_name}")
            
            # Configure Windows voice as fallback
            if len(voices) > 0:
                if voice_type == 'Windows Voice':
                    self.windows_engine.setProperty('voice', voice_name)
                    logger.info(f"Set Windows voice to: {voice_name}")
                else:
                    # Use first available voice as fallback
                    self.windows_engine.setProperty('voice', voices[0].id)
                    logger.info(f"Set fallback Windows voice to: {voices[0].id}")
            
            self.windows_engine.setProperty('rate', 150)
            self.windows_engine.setProperty('volume', 0.9)
            
            # If Windows voice is selected, use fallback
            if voice_type == 'Windows Voice':
                self.use_fallback = True
                logger.info("Using Windows voice as primary")
                return
            
            # Test Edge TTS by listing voices
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            voices = loop.run_until_complete(self._list_voices())
            loop.close()
            
            if not voices:
                raise Exception("No Edge TTS voices available")
            
            # Verify the selected voice exists
            voice_exists = any(v['ShortName'] == voice_name for v in voices)
            if not voice_exists:
                logger.warning(f"Selected voice {voice_name} not found in Edge TTS voices")
                # Try to find a similar voice
                for v in voices:
                    if 'en-US' in v['ShortName']:
                        voice_name = v['ShortName']
                        logger.info(f"Using alternative voice: {voice_name}")
                        break
            
            self.use_fallback = False
            logger.info("Edge TTS setup successful")
            
        except Exception as e:
            self.use_fallback = True
            error_msg = f"Failed to set up Edge TTS, falling back to Windows: {str(e)}"
            logger.error(error_msg)
            self.speak_error.emit(error_msg)

    def change_voice(self, voice_name):
        """Change the voice being used"""
        try:
            if "Neural" in voice_name:  # Edge voice
                logger.info(f"Changing to Edge voice: {voice_name}")
                # Just update the config, voice will be used in next speak call
                self.use_fallback = False
                
                # Update local config only
                self.config['voice_type'] = 'Edge Voice'
                self.config['voice_name'] = voice_name
                logger.info(f"Changed to Edge voice: {voice_name}")
                
            else:  # Windows voice
                logger.info(f"Changing to Windows voice: {voice_name}")
                if not self.windows_engine:
                    self.windows_engine = pyttsx3.init()
                self.windows_engine.setProperty('voice', voice_name)
                self.use_fallback = True
                
                # Update local config only
                self.config['voice_type'] = 'Windows Voice'
                self.config['voice_name'] = voice_name
                logger.info(f"Changed to Windows voice: {voice_name}")
            
        except Exception as e:
            self.use_fallback = True
            error_msg = f"Failed to set voice, falling back to Windows: {str(e)}"
            logger.error(error_msg)
            self.speak_error.emit(error_msg)
            
            # Try to set up Windows fallback if not already done
            if not self.windows_engine:
                try:
                    self.windows_engine = pyttsx3.init()
                    voices = self.windows_engine.getProperty('voices')
                    if voices:
                        self.windows_engine.setProperty('voice', voices[0].id)
                except Exception as we:
                    error_msg = f"Failed to set up Windows fallback: {str(we)}"
                    logger.error(error_msg)
                    self.speak_error.emit(error_msg)

    def speak(self, text):
        """Speak text using Edge TTS with fallback to Windows voices"""
        if self.use_fallback:
            logger.info("Using Windows fallback for speech")
            self._speak_windows(text)
        else:
            logger.info("Using Edge TTS for speech")
            
            # Clean up previous worker if it exists
            if self.tts_worker and self.tts_worker.isRunning():
                self.tts_worker.terminate()
                self.tts_worker.wait()
            
            # Generate temp file path
            temp_file = os.path.join(self.temp_dir, 'temp_speech.mp3')
            
            # Create and setup worker
            self.tts_worker = TTSWorker(temp_file, self.config.get('voice_name', 'en-US-AnaNeural'))
            self.tts_worker.set_text(text)
            self.tts_worker.finished.connect(self._on_tts_finished)
            self.tts_worker.error.connect(self._on_tts_error)
            
            # Start speaking
            self.is_speaking = True
            self.speak_started.emit()
            self.tts_worker.start()
    
    def _on_tts_finished(self):
        """Handle TTS completion"""
        self.is_speaking = False
        self.speak_finished.emit()
        
    def _on_tts_error(self, error):
        """Handle TTS error"""
        self.is_speaking = False
        error_msg = f"Edge TTS error: {error}"
        logger.error(error_msg)
        self.speak_error.emit(error_msg)
        # Fall back to Windows voice
        self._speak_windows(self.tts_worker.text)
        
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
                error_msg = f"Windows TTS error: {str(e)}"
                logger.error(error_msg)
                self.speak_error.emit(error_msg)
        
        threading.Thread(target=speak_thread, daemon=True).start()
