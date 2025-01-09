import os
import logging
from .ollama import OllamaProvider
from .google import GoogleProvider
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIManager:
    def __init__(self, provider_name="ollama", google_api_key=None, model=None):
        """Initialize AI manager with specified provider"""
        load_dotenv()  # Keep this for any other env vars that might be needed
        
        # Get default Ollama model if none specified
        if not model and provider_name == "ollama":
            try:
                import subprocess
                result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
                if result.returncode == 0:
                    models = [line.split()[0] for line in result.stdout.strip().split('\n')[1:]]
                    if models:
                        model = models[0]  # Use first available model
                    else:
                        logger.warning("No Ollama models found, attempting to pull llama3.2:1b")
                        subprocess.run(['ollama', 'pull', 'llama3.2:1b'], capture_output=True)
                        model = "llama3.2:1b"
                else:
                    model = "llama3.2:1b"  # Default if ollama list fails
            except Exception as e:
                logger.error(f"Error getting Ollama models: {e}")
                model = "llama3.2:1b"  # Default if exception occurs
        
        # Initialize providers
        self.providers = {
            "ollama": OllamaProvider(model=model if model else "llama3.2:1b"),
        }
        
        # Add Google provider if API key is provided
        if google_api_key:
            self.providers["google"] = GoogleProvider(api_key=google_api_key, model_name=model if model else "gemini-1.5-flash-8b")
        elif provider_name == "google":
            # Create a placeholder for Google provider
            self.providers["google"] = None
        
        # Set current provider
        self.provider_name = provider_name
        self.current_provider = self.providers.get(provider_name)
        
        self.conversation_history = []
    
    def set_provider(self, provider_name):
        """Change the AI provider"""
        if provider_name == "google" and "google" not in self.providers:
            raise ValueError("Google Gemini API key not found. Please set GEMINI_API_KEY in your environment.")
        if provider_name in self.providers:
            self.current_provider = self.providers[provider_name]
            return True
        return False
    
    def get_response(self, text, system_prompt="", conversation_history=None):
        """Get response from current AI provider"""
        # Check if trying to use Google without API key
        if self.provider_name == "google" and not self.current_provider:
            return "I'm sorry, but you need to add a Google API key in settings or switch to Ollama in order to generate a response."
            
        try:
            if conversation_history is not None:
                self.conversation_history = conversation_history
            
            response = self.current_provider.get_response(
                text, 
                system_prompt, 
                self.conversation_history
            )
            
            # Update conversation history
            self.conversation_history.append({
                'role': 'user',
                'content': text
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting response from {self.current_provider.__class__.__name__}: {e}")
            if isinstance(self.current_provider, GoogleProvider):
                return "API key not valid. Please check your Google API key in settings."
            return "I'm having trouble thinking right now. Could you please try again?"
    
    def get_conversation_history(self):
        """Get the current conversation history"""
        return self.conversation_history
    
    def set_conversation_history(self, history):
        """Set the conversation history"""
        self.conversation_history = history
