from ollama import Client
import logging

logger = logging.getLogger(__name__)

class OllamaProvider:
    def __init__(self, host='http://localhost:11434', model='llama3.2:latest'):
        """Initialize Ollama provider"""
        self.client = Client(host=host)
        self.model = model
        
    def get_response(self, text, system_prompt="", conversation_history=None):
        """Get response from Ollama"""
        try:
            logger.info(f"Getting response from Ollama using model: {self.model}")
            # Build messages array
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current message
            messages.append({
                'role': 'user',
                'content': text
            })
            
            # Get response from Ollama
            response = self.client.chat(model=self.model, messages=messages)
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise
    
    def test_connection(self):
        """Test if Ollama is running and model is available"""
        try:
            models = self.client.list()
            if not any(model['name'] == self.model for model in models['models']):
                logger.warning(f"Model {self.model} not found. Please run: ollama pull {self.model}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {e}")
            return False
