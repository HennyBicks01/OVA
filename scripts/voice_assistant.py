import speech_recognition as sr
import threading
import queue
import time
from ollama import Client

class VoiceAssistant:
    def __init__(self, wake_word="hey echo", callback=None):
        self.wake_word = wake_word.lower()
        self.callback = callback
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self.client = Client(host='http://localhost:11434')
        
        # Test if Ollama is running and check for llama3.2
        try:
            models = self.client.list()
            print("Successfully connected to Ollama!")
            
            # Check if llama3.2 is available
            model_names = [model['name'] for model in models['models']]
            if 'llama3.2' not in model_names:
                print("llama3.2 model not found. Please run 'ollama pull llama3.2' first.")
        except Exception as e:
            print("Error connecting to Ollama. Make sure it's running:", e)
    
    def start_listening(self):
        """Start listening in background"""
        self.is_listening = True
        threading.Thread(target=self._listen_loop, daemon=True).start()
    
    def stop_listening(self):
        """Stop listening"""
        self.is_listening = False
    
    def _listen_loop(self):
        """Continuous listening loop"""
        with sr.Microphone() as source:
            print("Adjusting for ambient noise...")
            # Adjust for ambient noise
            self.recognizer.adjust_for_ambient_noise(source)
            print("Ready! Listening for wake word:", self.wake_word)
            
            while self.is_listening:
                try:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    try:
                        text = self.recognizer.recognize_google(audio).lower()
                        print("Heard:", text)
                        
                        if self.wake_word in text:
                            print("Wake word detected! Processing command...")
                            # Extract the question (everything after the wake word)
                            question = text.split(self.wake_word)[-1].strip()
                            if question:
                                self._generate_response(question)
                    except sr.UnknownValueError:
                        pass  # Speech was unintelligible
                    except sr.RequestError as e:
                        print(f"Could not request results; {e}")
                except sr.WaitTimeoutError:
                    pass  # No speech detected within timeout
                except Exception as e:
                    print(f"Error in listen loop: {e}")
                    time.sleep(1)
    
    def _generate_response(self, text):
        """Generate a response using Ollama with llama3.2"""
        try:
            print("Generating response for:", text)
            
            # Generate response using llama3.2
            response = self.client.chat(model='llama3.2', messages=[{
                'role': 'system',
                'content': 'You are a helpful and friendly child assistant. Always address the user as "Miss Kathy". Keep your responses cheerful and simple, like a young helper eager to assist. Use casual, child-like language but be polite and respectful.'
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
                self.callback("I'm sorry Miss Kathy, I'm having a little trouble thinking right now. Could you please make sure my friend Ollama is running?")
