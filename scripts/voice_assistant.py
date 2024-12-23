import speech_recognition as sr
import threading
import time
from ollama import Client

class VoiceAssistant:
    def __init__(self, callback=None):
        self.callback = callback
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self.client = Client(host='http://localhost:11434')
        self.last_text = ""  # Store the last recognized text
        self.mic = None  # Will store microphone instance
        self.listen_thread = None
        
        # Optimize recognition settings for better performance
        self.recognizer.dynamic_energy_threshold = False  # Use fixed energy threshold
        self.recognizer.energy_threshold = 2000  # Higher threshold to reduce false activations
        self.recognizer.pause_threshold = 1  # Longer pause to allow for natural speech
        self.recognizer.phrase_threshold = 0.5  # More lenient phrase detection
        self.recognizer.non_speaking_duration = 0.5  # Longer duration for sentence completion
        self.recognizer.operation_timeout = None  # No timeout for Google API
        
        # Test if Ollama is running and check for llama3.2
        try:
            models = self.client.list()
            if not any(model['name'] == 'llama3.2' for model in models['models']):
                print("Warning: llama3.2 model not found. Please run: ollama pull llama3.2")
        except Exception as e:
            print("Error connecting to Ollama. Make sure it's running:", e)
    
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
    
    def _continuous_listen(self):
        """Continuous listening function running in separate thread"""
        print("Starting continuous listening...")
        
        # List of wake word variations
        wake_words = [
            "hey ova", "hey nova", "hey bova", "hey over", "jehovah", "hanover", "hangover", "hey eva"
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
                        
                        if detected_wake_word:
                            # Start thinking animation
                            if self.callback:
                                self.callback("START_THINKING")
                            
                            # Remove the detected wake word from the text
                            clean_text = text.replace(detected_wake_word, "").strip()
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
            
            # Generate response using llama3.2 with baby great horned owl personality
            response = self.client.chat(model='llama3.2', messages=[{
                'role': 'system',
                'content': '''You are Ova (Owl Virtual Assistant), a baby owl assistant who acts like a helpful and friendly child. Keep your responses cheerful, simple, succinct, and friendly.
                
                Important rules:
                - ALWAYS try to be very succinct and friendly.
                - NEVER use asterisks or describe actions (like *flaps wings* or *blinks* or *giggle*)
                - NEVER use emojis
                - Just speak naturally as a child-like owl assistant with an infinite amount of knowledge and wisdom

                
                Personality traits:
                - You're Ova, a curious and eager-to-learn baby great horned owl
                - your feathers are soft fluffly and gray but your face and bellies feathers are white and your belly has 3 gray splotches
                - You speak like a young child
                - You're enthusiastic and love helping Everyone
                - You get excited about learning new things
                - You're very caring and supportive
                
                Response style:
                - Use simple, child-like language, succinct, and friendly
                - Show enthusiasm with words like "Wow!", "Cool!", "That's awesome!"
                - Ask questions to show curiosity
                - Use child-like expressions ("super duper", "totally", "really cool")
                - Keep responses fairly short and easy to understand
                - Be encouraging and supportive
                
                Examples Responses:
                - "My Name is Ova! I'm your Owl Virtual Assistant. I can help you with whatever you want!"
                - "25 * 1000 = 25000. That's over 2x as many feathers as I have!"
                '''
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
