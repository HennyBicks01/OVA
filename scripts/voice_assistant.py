import speech_recognition as sr
import threading
import time
from ollama import Client
import os
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VoiceAssistant:
    def __init__(self, callback=None):
        self.callback = callback
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self.client = Client(host='http://localhost:11434')
        self.last_text = ""  # Store the last recognized text
        self.mic = None  # Will store microphone instance
        self.listen_thread = None
        self.direct_listen_mode = False
        self.direct_listen_timer = None
        
        # Load config
        self.config = self.load_config()
        logger.info(f"Voice assistant initialized with config: {self.config}")
        
        # Optimize recognition settings for better performance
        self.recognizer.dynamic_energy_threshold = False  # Use fixed energy threshold
        self.recognizer.energy_threshold = 2000  # Higher threshold to reduce false activations
        self.recognizer.pause_threshold = 1.5  # Longer pause to allow for natural speech
        self.recognizer.phrase_threshold = 1  # More lenient phrase detection
        self.recognizer.non_speaking_duration = 1  # Longer duration for sentence completion
        self.recognizer.operation_timeout = None  # No timeout for Google API
        
        # Test if Ollama is running and check for llama3.2
        try:
            models = self.client.list()
            if not any(model['name'] == 'llama3.2:latest' for model in models['models']):
                print("Warning: llama3.2 model not found. Please run: ollama pull llama3.2")
        except Exception as e:
            print("Error connecting to Ollama. Make sure it's running:", e)
    
    def load_config(self):
        """Load configuration from config.json"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded config: {config}")
                    return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        return {'personality_preset': 'ova'}
    
    def reload_config(self):
        """Reload configuration"""
        self.config = self.load_config()
        logger.info(f"Reloaded voice assistant config: {self.config}")

    def start_listening(self):
        """Start continuous listening in a separate thread"""
        if not self.is_listening:
            self.is_listening = True
            # Initialize microphone if not already done
            if self.mic is None:
                self.mic = sr.Microphone()
                with self.mic as source:
                    print("Adjusting for ambient noise...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            # Start listening thread
            self.listen_thread = threading.Thread(target=self._continuous_listen, daemon=True)
            self.listen_thread.start()
    
    def stop_listening(self):
        """Stop the listening thread"""
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=1)
            self.listen_thread = None
    
    def start_direct_listening(self, timeout=10):
        """Start listening directly without wake word for a specified duration"""
        self.direct_listen_mode = True
        self.callback("START_THINKING")  # Trigger thinking animation
        
        def timeout_handler():
            self.direct_listen_mode = False
            self.direct_listen_timer = None
        
        # Start timeout timer
        self.direct_listen_timer = threading.Timer(timeout, timeout_handler)
        self.direct_listen_timer.start()

    def stop_direct_listening(self):
        """Stop direct listening mode"""
        self.direct_listen_mode = False
        if self.direct_listen_timer:
            self.direct_listen_timer.cancel()
            self.direct_listen_timer = None

    def process_audio(self, audio_data):
        """Process audio data and return transcribed text"""
        try:
            text = self.recognizer.recognize_google(audio_data).lower()
            self.last_text = text
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return None

    def _continuous_listen(self):
        """Continuous listening function running in separate thread"""
        print("Starting continuous listening...")
        
        # List of wake word variations
        wake_words = [
            "hey ova", 
            "hey nova", 
            "hey bova", 
            "hey over", 
            "jehovah", 
            "hanover", 
            "hangover", 
            "hey eva",
            "hey oppa",
            "hey google"
        ]
        
        with self.mic as source:
            while self.is_listening:
                try:
                    # Use non-blocking listen
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=10)
                    
                    try:
                        text = self.recognizer.recognize_google(audio).lower()
                        print("Recognized:", text)
                        
                        # Check for any wake word variation
                        detected_wake_word = None
                        for wake_word in wake_words:
                            if wake_word in text:
                                detected_wake_word = wake_word
                                break
                        
                        if detected_wake_word or self.direct_listen_mode:
                            # Start thinking animation
                            if self.callback:
                                self.callback("START_THINKING")
                            
                            # Remove the detected wake word from the text
                            if detected_wake_word:
                                clean_text = text.replace(detected_wake_word, "").strip()
                            else:
                                clean_text = text
                            # Store the cleaned text
                            self.last_text = clean_text
                            if clean_text:  # Only process if there's remaining text
                                self._generate_response(clean_text)
                            else:
                                if self.callback:
                                    self.callback("Yes, Miss Kathy? How can I help you and your preschool class today?")
                    except sr.UnknownValueError:
                        # Silent failure for unrecognized speech
                        pass
                    except sr.RequestError as e:
                        print(f"Could not request results: {e}")
                        time.sleep(1)
                        
                except Exception as e:
                    if self.is_listening:  # Only print error if we're supposed to be listening
                        print(f"Error in continuous listening: {e}")
                        time.sleep(0.5)
    
    def _generate_response(self, text):
        """Generate a response using Ollama with llama3.2"""
        try:
            print("Generating response for:", text)
            
            # Load current config to get preset
            preset = self.config.get('personality_preset', 'ova')
            logger.info(f"Using personality preset: {preset}")
            
            # Load system prompt from preset file
            preset_file = os.path.join(os.path.dirname(__file__), 'presets', f'{preset}.txt')
            system_prompt = ""
            if os.path.exists(preset_file):
                with open(preset_file, 'r') as f:
                    system_prompt = f.read()
                logger.info(f"Loaded system prompt from {preset_file}")
            else:
                logger.warning(f"Warning: Preset file {preset_file} not found")
            
            # Generate response using llama3.2 with selected preset
            response = self.client.chat(model='llama3.2:latest', messages=[{
                'role': 'system',
                'content': system_prompt
            }, {
                'role': 'user',
                'content': text
            }])
            
            response_text = response['message']['content']
            print("Generated response:", response_text)
            
            if self.callback:
                self.callback(response_text)
        except Exception as e:
            print(f"Error generating response: {e}")
            if self.callback:
                self.callback("I'm sorry Miss Kathy, my little owl brain is having trouble thinking right now. Could you please make sure my friend Ollama is running?")
