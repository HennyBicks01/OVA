import os
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)

class GoogleProvider:
    def __init__(self, api_key=None, model_name="gemini-1.5-flash-8b"):
        self.api_key = api_key
        self.model_name = model_name
        self.conversation_history = []
        self.chat_session = None
        
        # Configure generation settings
        self.generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        
        # Initialize the model if API key is provided
        if api_key:
            logger.info("Initializing Google Gemini model..." + api_key)

            self.initialize_model(api_key)

    def initialize_model(self, api_key):
        """Initialize the Gemini model with the provided API key"""
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=self.generation_config
            )
            self.chat_session = self.model.start_chat(history=[])
            logger.info("Google Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Google Gemini model: {e}")
            raise

    def get_response(self, prompt, system_prompt="", conversation_history=None):
        """Get response from the model"""
        if not self.chat_session:
            if not self.api_key:
                raise ValueError("API key not provided. Please set up the API key in settings.")
            self.initialize_model(self.api_key)
        
        try:
            logger.info(f"Getting response from Google using model: {self.model_name}")
            # If there's a new conversation history, restart the chat with the entire history
            if conversation_history is not None and conversation_history != self.conversation_history:
                self.conversation_history = conversation_history
                
                # Convert history to Gemini format
                history = []
                if system_prompt:
                    history.append({"role": "user", "parts": [system_prompt]})
                    history.append({"role": "model", "parts": ["Understood."]})
                
                # Add conversation history
                for msg in conversation_history:
                    role = "user" if msg['role'] == 'user' else "model"
                    history.append({"role": role, "parts": [msg['content']]})
                
                # Start new chat with full history
                self.chat_session = self.model.start_chat(history=history)
            
            # Send the user's prompt and get response
            response = self.chat_session.send_message(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error getting response from Google Gemini: {e}")
            raise

    def get_conversation_history(self):
        """Return the current conversation history"""
        return self.conversation_history

    def set_conversation_history(self, history):
        """Set the conversation history"""
        self.conversation_history = history
        if self.chat_session:
            self.chat_session = self.model.start_chat(history=[])
