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
        
        # Initialize providers
        self.providers = {
            "ollama": OllamaProvider(model=model if model else "llama2:latest"),
        }
        
        # Add Google provider if API key is provided
        if google_api_key:
            self.providers["google"] = GoogleProvider(api_key=google_api_key, model_name=model if model else "gemini-1.5-flash-8b")
        
        # Set current provider
        self.current_provider = self.providers.get(provider_name)
        if not self.current_provider:
            if provider_name == "google" and not google_api_key:
                raise ValueError("Google Gemini API key not provided. Please check your configuration.")
            logger.warning(f"Provider {provider_name} not found, falling back to ollama")
            self.current_provider = self.providers["ollama"]
        
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
            # Try fallback to Ollama if current provider fails
            if not isinstance(self.current_provider, OllamaProvider):
                logger.info("Falling back to Ollama provider")
                self.current_provider = self.providers["ollama"]
                return self.get_response(text, system_prompt, conversation_history)
            return "I'm having trouble thinking right now. Could you please try again?"
    
    def get_conversation_history(self):
        """Get the current conversation history"""
        return self.conversation_history
    
    def set_conversation_history(self, history):
        """Set the conversation history"""
        self.conversation_history = history
