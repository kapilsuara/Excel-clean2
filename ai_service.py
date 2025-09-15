"""
Unified AI Service with automatic fallback between Anthropic and OpenAI
"""

import os
import json
import logging
import streamlit as st
from typing import Optional, Tuple, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Try to import AI libraries
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available")

class AIService:
    """Unified AI service with automatic fallback"""
    
    def __init__(self):
        self.anthropic_client = None
        self.openai_client = None
        self.current_provider = None
        self._initialize_clients()
    
    def _get_api_keys(self) -> Tuple[Optional[str], Optional[str]]:
        """Get API keys from Streamlit secrets or environment variables"""
        anthropic_key = None
        openai_key = None
        
        # Try Streamlit secrets first
        try:
            if hasattr(st, 'secrets'):
                if 'ANTHROPIC_API_KEY' in st.secrets:
                    anthropic_key = st.secrets['ANTHROPIC_API_KEY']
                if 'OPENAI_API_KEY' in st.secrets:
                    openai_key = st.secrets['OPENAI_API_KEY']
        except:
            pass
        
        # Fall back to environment variables
        if not anthropic_key:
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if not openai_key:
            openai_key = os.getenv('OPENAI_API_KEY')
        
        return anthropic_key, openai_key
    
    def _initialize_clients(self):
        """Initialize AI clients"""
        anthropic_key, openai_key = self._get_api_keys()
        
        # Initialize Anthropic
        if ANTHROPIC_AVAILABLE and anthropic_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                logger.info("Anthropic client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic: {e}")
        
        # Initialize OpenAI
        if OPENAI_AVAILABLE and openai_key:
            try:
                # Check OpenAI version and initialize accordingly
                import openai
                if hasattr(openai, '__version__'):
                    # OpenAI v1.x
                    self.openai_client = openai.OpenAI(api_key=openai_key)
                else:
                    # OpenAI v0.x
                    openai.api_key = openai_key
                    self.openai_client = openai
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
    
    def _call_anthropic(self, prompt: str, max_tokens: int = 400, system_prompt: Optional[str] = None) -> Optional[str]:
        """Call Anthropic API"""
        if not self.anthropic_client:
            return None
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            if system_prompt:
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=messages
                )
            else:
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=max_tokens,
                    messages=messages
                )
            
            return response.content[0].text.strip()
        
        except Exception as e:
            error_msg = str(e).lower()
            if 'credit' in error_msg or 'balance' in error_msg or 'insufficient' in error_msg or 'billing' in error_msg:
                logger.warning(f"Anthropic API insufficient credits: {e}")
                st.warning("⚠️ Anthropic API has insufficient credits, switching to OpenAI...")
            else:
                logger.error(f"Anthropic API error: {e}")
            return None
    
    def _call_openai(self, prompt: str, max_tokens: int = 400, system_prompt: Optional[str] = None) -> Optional[str]:
        """Call OpenAI API"""
        if not self.openai_client:
            return None
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Check if it's the new client (v1.x) or old (v0.x)
            if hasattr(self.openai_client, 'chat'):
                # OpenAI v1.x
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
            else:
                # OpenAI v0.x or direct API
                import openai
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
        
        except Exception as e:
            error_msg = str(e).lower()
            if 'credit' in error_msg or 'balance' in error_msg or 'insufficient' in error_msg or 'quota' in error_msg:
                logger.warning(f"OpenAI API insufficient credits: {e}")
                st.error("❌ OpenAI API also has insufficient credits")
            else:
                logger.error(f"OpenAI API error: {e}")
            return None
    
    def call(self, prompt: str, max_tokens: int = 400, system_prompt: Optional[str] = None) -> Optional[str]:
        """
        Make an AI call with automatic fallback
        
        Args:
            prompt: The user prompt
            max_tokens: Maximum tokens for response
            system_prompt: Optional system prompt
        
        Returns:
            Response text or None if both services fail
        """
        # Try Anthropic first
        if self.anthropic_client:
            response = self._call_anthropic(prompt, max_tokens, system_prompt)
            if response:
                self.current_provider = 'anthropic'
                return response
        
        # Fall back to OpenAI
        if self.openai_client:
            st.info("Using OpenAI as fallback...")
            response = self._call_openai(prompt, max_tokens, system_prompt)
            if response:
                self.current_provider = 'openai'
                return response
        
        # Both failed
        st.error("❌ Both AI services failed. Please check your API keys and credits.")
        return None
    
    def get_status(self) -> str:
        """Get current AI service status"""
        if self.current_provider == 'anthropic':
            return "✅ Using Claude AI"
        elif self.current_provider == 'openai':
            return "✅ Using OpenAI GPT"
        elif self.anthropic_client:
            return "🟡 Claude AI Ready"
        elif self.openai_client:
            return "🟡 OpenAI Ready"
        else:
            return "❌ No AI Service Available"
    
    def is_available(self) -> bool:
        """Check if any AI service is available"""
        return self.anthropic_client is not None or self.openai_client is not None

# Global AI service instance
_ai_service = None

def get_ai_service() -> AIService:
    """Get or create the global AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service

def make_ai_call(prompt: str, max_tokens: int = 400, system_prompt: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to make AI calls
    
    This function automatically handles:
    - Fallback from Anthropic to OpenAI
    - Error handling and user notifications
    - Credit/billing issues
    """
    service = get_ai_service()
    
    if not service.is_available():
        st.error("❌ No AI service available. Please configure API keys.")
        st.info("Add ANTHROPIC_API_KEY or OPENAI_API_KEY to .streamlit/secrets.toml")
        return None
    
    return service.call(prompt, max_tokens, system_prompt)