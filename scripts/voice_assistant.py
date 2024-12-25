import speech_recognition as sr
import threading
import time
from ollama import Client
import os
import json
import logging
import pygame

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
        self.mic = None  # Microphone instance
        self.listen_thread = None
        self.direct_listen_mode = False
        self.direct_listen_timer = None
        self.no_response_timer = None
        self.conversation_history = []  # Store conversation history
        
        # Load config and history
        self.config = self.load_config()
        self.load_conversation_history()
        
        # Sound file paths and initialization
        self.activation_sound = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'sounds', 'HeyOva.mp3')
        self.no_answer_sound = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'sounds', 'NoAnswer.mp3')
        
        # Load sounds
        pygame.mixer.init()
        try:
            self.activation_sound_obj = pygame.mixer.Sound(self.activation_sound)
            self.no_answer_sound_obj = pygame.mixer.Sound(self.no_answer_sound)
        except Exception as e:
            print(f"Error loading sounds: {e}")
            self.activation_sound_obj = None
            self.no_answer_sound_obj = None
        
        logger.info(f"Voice assistant initialized with config: {self.config}")
        
        # Optimize recognition settings for better wake word detection
        self.recognizer.dynamic_energy_threshold = False
        self.recognizer.energy_threshold = 800  # More sensitive for wake word
        self.recognizer.pause_threshold = 1.5  # Balanced pause threshold
        self.recognizer.phrase_threshold = 0.05  # More sensitive phrase detection
        self.recognizer.non_speaking_duration = 0.5  # Shorter non-speaking duration
        self.recognizer.operation_timeout = None  # No timeout

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
    
    def load_conversation_history(self):
        """Load conversation history from file"""
        history_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conversation_history.json')
        try:
            if os.path.exists(history_path) and self.config.get('save_conversation_history', True):
                with open(history_path, 'r') as f:
                    self.conversation_history = json.load(f)
                    # Trim to max length from config
                    max_pairs = self.config.get('max_conversation_pairs', 10)
                    if len(self.conversation_history) > max_pairs * 2:
                        self.conversation_history = self.conversation_history[-(max_pairs * 2):]
                    logger.info(f"Loaded {len(self.conversation_history)} messages from history")
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
            self.conversation_history = []

    def save_conversation_history(self):
        """Save conversation history to file"""
        if not self.config.get('save_conversation_history', True):
            return
            
        history_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conversation_history.json')
        try:
            # Ensure we don't exceed max pairs
            max_pairs = self.config.get('max_conversation_pairs', 10)
            if len(self.conversation_history) > max_pairs * 2:
                self.conversation_history = self.conversation_history[-(max_pairs * 2):]
                
            with open(history_path, 'w') as f:
                json.dump(self.conversation_history, f)
            logger.info(f"Saved {len(self.conversation_history)} messages to history")
        except Exception as e:
            logger.error(f"Error saving conversation history: {e}")

    def reload_config(self):
        """Reload configuration"""
        self.config = self.load_config()
        logger.info(f"Reloaded voice assistant config: {self.config}")
        # Reload conversation history with new settings
        self.load_conversation_history()

    def start_listening(self):
        """Start continuous listening in a separate thread"""
        if not self.is_listening:
            self.is_listening = True
            
            # Initialize microphone if not already done
            if self.mic is None:
                try:
                    self.mic = sr.Microphone()
                    with self.mic as source:
                        print("Adjusting for ambient noise...")
                        self.recognizer.adjust_for_ambient_noise(source, duration=1)
                except Exception as e:
                    print(f"Error initializing microphone: {e}")
                    return
            
            # Start listening thread
            self.listen_thread = threading.Thread(target=self._continuous_listen, daemon=True)
            self.listen_thread.start()

    def _continuous_listen(self):
        """Continuous listening function running in separate thread"""
        print("Starting continuous listening...")
        
        # List of wake word variations
        wake_words = [
            "hey ova", "hey nova", "hey bova", "hey over", 
            "jehovah", "hanover", "hangover", "hey eva",
            "hey oppa", "hey google", "hey opa"
        ]
        
        with self.mic as source:
            while self.is_listening:
                try:
                    # Use shorter phrase time limit for wake word detection
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=2)
                    try:
                        text = self.recognizer.recognize_google(audio).lower()
                        print("Heard:", text)
                        
                        # Check for wake word or direct listen mode
                        detected_wake_word = None
                        if not self.direct_listen_mode:  # Only check wake word if not in direct listen
                            for wake_word in wake_words:
                                if wake_word in text:
                                    detected_wake_word = wake_word
                                    break
                        
                        if detected_wake_word or self.direct_listen_mode:
                            # Play activation sound for wake word only
                            if detected_wake_word and self.activation_sound_obj:
                                self.activation_sound_obj.play()
                            
                            # Start listening animation if not already listening
                            if not self.direct_listen_mode and self.callback:
                                self.callback("START_LISTENING")
                            
                            # Flag to track if we got a response
                            got_response = False
                            
                            # Process text based on mode
                            if self.direct_listen_mode:
                                # In direct listen mode, process the text directly
                                got_response = True
                                if self.callback:
                                    self.callback("START_THINKING")
                                self._generate_response(text)
                                # Exit direct listen mode
                                self.stop_direct_listening()
                            else:
                                # Check for command after wake word
                                command_after_wake = text.replace(detected_wake_word, "").strip()
                                if command_after_wake:
                                    got_response = True
                                    if self.callback:
                                        self.callback("START_THINKING")
                                    self._generate_response(command_after_wake)
                                else:
                                    # Start no-response timer
                                    if self.no_response_timer:
                                        self.no_response_timer.cancel()
                                    
                                    def handle_no_response():
                                        nonlocal got_response
                                        if not got_response:
                                            if self.no_answer_sound_obj:
                                                self.no_answer_sound_obj.play()
                                            if self.callback:
                                                self.callback("STOP_LISTENING")
                                            got_response = True
                                    
                                    self.no_response_timer = threading.Timer(10.0, handle_no_response)
                                    self.no_response_timer.start()
                                    
                                    # Listen for command
                                    try:
                                        time.sleep(0.1)
                                        start_time = time.time()
                                        while not got_response and time.time() - start_time < 5:
                                            try:
                                                command_audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=10)
                                                command_text = self.recognizer.recognize_google(command_audio).lower()
                                                print("Command:", command_text)
                                                
                                                if self.no_response_timer:
                                                    self.no_response_timer.cancel()
                                                
                                                got_response = True
                                                
                                                if command_text:
                                                    if self.callback:
                                                        self.callback("START_THINKING")
                                                    self._generate_response(command_text)
                                                break
                                                
                                            except sr.WaitTimeoutError:
                                                continue
                                            except sr.UnknownValueError:
                                                continue
                                        
                                    except sr.RequestError as e:
                                        print(f"Could not request results for command: {e}")
                                    finally:
                                        if self.no_response_timer:
                                            self.no_response_timer.cancel()
                    
                    except sr.UnknownValueError:
                        pass  # Silent failure for unrecognized speech
                    except sr.RequestError as e:
                        print(f"Could not request results: {e}")
                        time.sleep(1)
                        
                except Exception as e:
                    if self.is_listening:
                        print(f"Error in continuous listening: {e}")
                        time.sleep(0.5)

    def stop_listening(self):
        """Stop the listening thread"""
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=1)
            self.listen_thread = None

    def start_direct_listening(self, timeout=5):
        """Start listening directly without wake word for a specified duration"""
        self.direct_listen_mode = True
        self.callback("START_LISTENING")  # Trigger listening animation
        
        # Start no-response timer
        if self.no_response_timer:
            self.no_response_timer.cancel()
        
        def handle_no_response():
            self.direct_listen_mode = False
            self.direct_listen_timer = None
            if self.no_answer_sound_obj:
                self.no_answer_sound_obj.play()
            if self.callback:
                self.callback("STOP_LISTENING")
        
        self.no_response_timer = threading.Timer(timeout, handle_no_response)
        self.no_response_timer.start()

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

    def handle_no_response(self):
        """Handle when no response is received after wake word"""
        try:
            if self.no_answer_sound_obj:
                self.no_answer_sound_obj.play()
        except Exception as e:
            print(f"Error playing no-answer sound: {e}")
        finally:
            # Reset direct listen mode if active
            if self.direct_listen_mode:
                self.stop_direct_listening()

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
            
            # Build messages array with history
            messages = [{
                'role': 'system',
                'content': system_prompt
            }]
            
            # Add conversation history
            for msg in self.conversation_history:
                messages.append(msg)
            
            # Add current user message
            messages.append({
                'role': 'user',
                'content': text
            })
            
            # Generate response using llama3.2 with selected preset and history
            response = self.client.chat(model='llama3.2:latest', messages=messages)
            
            response_text = response['message']['content']
            print("Generated response:", response_text)
            
            # Add the exchange to conversation history
            self.conversation_history.append({
                'role': 'user',
                'content': text
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': response_text
            })
            
            # Trim history if needed
            max_pairs = self.config.get('max_conversation_pairs', 10)
            if len(self.conversation_history) > max_pairs * 2:
                self.conversation_history = self.conversation_history[-(max_pairs * 2):]
            
            # Save updated history
            self.save_conversation_history()
            
            if self.callback:
                self.callback((response_text, text))  # Pass tuple of (response, last_text)
        except Exception as e:
            print(f"Error generating response: {e}")
            if self.callback:
                self.callback(("I'm sorry Miss Kathy, my little owl brain is having trouble thinking right now. Could you please make sure my friend Ollama is running?", text))

    def test_ollama(self):
        """Test if Ollama is running and check for llama3.2"""
        try:
            models = self.client.list()
            if not any(model['name'] == 'llama3.2:latest' for model in models['models']):
                print("Warning: llama3.2 model not found. Please run: ollama pull llama3.2")
        except Exception as e:
            print("Error connecting to Ollama. Make sure it's running:", e)
