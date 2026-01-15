"""
Simple LLM provider wrapper for keyword extractor.
Supports OpenAI-compatible APIs (Qwen/DashScope, OpenAI).
"""
import os
from typing import Optional

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


class SimpleLLMProvider:
    """Simple LLM provider using OpenAI-compatible API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize LLM provider (OpenAI).
        
        Args:
            api_key: API key (defaults to OPENAI_API_KEY, with fallback to QWEN_API_KEY or DASHSCOPE_API_KEY)
            base_url: API base URL (defaults to OpenAI endpoint, Qwen/DashScope commented out)
            model: Model name (defaults to gpt-4o-mini)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package is required. Install with: pip install openai")
        
        # Get API key from env or parameter - prioritize OpenAI
        # COMMENTED OUT: Qwen usage - using OpenAI instead
        # self.api_key = api_key or os.getenv('QWEN_API_KEY') or os.getenv('DASHSCOPE_API_KEY') or os.getenv('OPENAI_API_KEY')
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('QWEN_API_KEY') or os.getenv('DASHSCOPE_API_KEY')
        if not self.api_key:
            raise ValueError(
                "API key required. Set OPENAI_API_KEY environment variable"
            )
        
        # Determine base URL - explicitly use OpenAI endpoint
        # IMPORTANT: OpenAI client automatically reads OPENAI_BASE_URL from env,
        # so we must explicitly override it to ensure we use OpenAI, not DashScope
        if base_url:
            self.base_url = base_url
        else:
            # Check if OPENAI_BASE_URL is set in environment
            env_base_url = os.getenv('OPENAI_BASE_URL')
            
            # If OPENAI_BASE_URL points to DashScope/Qwen, explicitly use OpenAI endpoint
            if env_base_url and 'dashscope' in env_base_url.lower():
                # Force OpenAI endpoint - override DashScope setting
                self.base_url = "https://api.openai.com/v1"
            # If OPENAI_BASE_URL is set to OpenAI endpoint, use it
            elif env_base_url and 'openai' in env_base_url.lower():
                self.base_url = env_base_url
            else:
                # No OPENAI_BASE_URL or it's not set - use OpenAI default
                self.base_url = "https://api.openai.com/v1"  # Explicitly set OpenAI endpoint
        
        # Model selection - use OpenAI model
        # COMMENTED OUT: Qwen model default
        # self.model = model or os.getenv('LLM_MODEL', 'qwen-plus')
        self.model = model or os.getenv('LLM_MODEL', 'gpt-4o-mini')
        
        # Log configuration for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[LLM Provider] Initializing with:")
        logger.info(f"  - API Key starts with: {self.api_key[:10]}..." if self.api_key else "  - API Key: None")
        logger.info(f"  - Base URL: {self.base_url or 'None (using OpenAI default)'}")
        logger.info(f"  - Model: {self.model}")
        logger.info(f"  - OPENAI_BASE_URL env: {os.getenv('OPENAI_BASE_URL', 'Not set')}")
        
        # Initialize client
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
    
    def llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (default: 0.3)
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text response
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"LLM API error: {str(e)}") from e





