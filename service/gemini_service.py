"""
Google Gemini API service wrapper for Python backend
Provides a unified interface for Gemini AI model interactions
"""

import google.generativeai as genai
import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class GeminiService:
    """Wrapper for Google Gemini API"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        self._configure()

    def _configure(self):
        """Configure the Gemini API client"""
        if not self.api_key or self.api_key == "your-gemini-api-key-here":
            logger.warning("Gemini API key not configured. Using fallback mode.")
            return

        try:
            genai.configure(api_key=self.api_key)
            # Using gemini-1.5-flash for fast responses, can switch to gemini-1.5-pro for complex tasks
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini service: {e}")
            self.model = None

    def is_configured(self) -> bool:
        """Check if Gemini is properly configured"""
        return self.model is not None

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate text using Gemini API

        Args:
            prompt: The user prompt
            system_instruction: System instruction for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Dict with 'text' and 'usage' fields
        """
        if not self.is_configured():
            raise Exception("Gemini API not configured. Please set GEMINI_API_KEY environment variable.")

        try:
            # Prepare the full prompt with system instruction
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"

            logger.info(f"Making Gemini request with {len(full_prompt)} characters")

            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Generate content
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )

            text = response.text

            logger.info(f"Gemini response received: {len(text)} characters")

            return {
                "text": text,
                "usage": {
                    "prompt_tokens": 0,  # Gemini doesn't provide detailed token counts
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            # Handle common errors
            if "API_KEY_INVALID" in str(e):
                raise Exception("Invalid Gemini API key. Please check your GEMINI_API_KEY.")
            elif "QUOTA_EXCEEDED" in str(e):
                raise Exception("Gemini API quota exceeded. Please check your usage limits.")
            elif "RATE_LIMIT_EXCEEDED" in str(e):
                raise Exception("Gemini API rate limit exceeded. Please wait and try again.")
            else:
                raise Exception(f"Gemini API error: {str(e)}")

    async def generate_json_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Generate a JSON response using Gemini

        Args:
            prompt: The user prompt
            system_instruction: System instruction for context
            temperature: Lower temperature for more structured output

        Returns:
            Parsed JSON response
        """
        # Add JSON formatting instruction to the prompt
        json_prompt = f"""{prompt}

Please respond with valid JSON only. Do not include any text before or after the JSON object."""

        if system_instruction:
            json_system = f"{system_instruction}\n\nIMPORTANT: Always respond with valid JSON format."
        else:
            json_system = "You are an AI assistant that responds with valid JSON format."

        response = await self.generate_text(
            json_prompt,
            system_instruction=json_system,
            temperature=temperature
        )

        try:
            # Extract JSON from response
            text = response["text"].strip()

            # Find JSON object boundaries
            start = text.find('{')
            end = text.rfind('}') + 1

            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
            else:
                # If no JSON found, try parsing the entire text
                return json.loads(text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            logger.error(f"Response text: {response['text'][:500]}...")
            raise Exception(f"Failed to parse JSON response: {str(e)}")

# Global instance
gemini_service = GeminiService()