"""
OpenAI Client - Wrapper for OpenAI API interactions
Handles chat completions with proper error handling and response formatting
"""

import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI

class OpenAIClient:
    def __init__(self):
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.api_key = os.getenv("OPENAI_API_KEY", "default_key")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"

    async def chat_completion(
        self, 
        prompt: str, 
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: int = 500,
        temperature: float = 0.3
    ) -> str:
        """
        Generate chat completion using OpenAI API
        
        Args:
            prompt: The prompt to send to the model
            response_format: Optional response format specification
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Response content as string
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant specialized in document processing and analysis. Always provide accurate, structured responses."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Add response format if specified
            if response_format:
                api_params["response_format"] = response_format
            
            # Make API call
            response = self.client.chat.completions.create(**api_params)
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {str(e)}")

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text using OpenAI
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment analysis results
        """
        try:
            prompt = f"""
            Analyze the sentiment of the following text and provide a rating from 1 to 5 stars 
            and a confidence score between 0 and 1.
            
            Text: {text}
            
            Respond with JSON in this format:
            {{"rating": number, "confidence": number, "sentiment": "positive|negative|neutral"}}
            """
            
            response = await self.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            return {
                "rating": max(1, min(5, round(result.get("rating", 3)))),
                "confidence": max(0, min(1, result.get("confidence", 0.5))),
                "sentiment": result.get("sentiment", "neutral")
            }
            
        except Exception as e:
            raise Exception(f"Failed to analyze sentiment: {e}")

    async def extract_structured_data(self, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from text according to provided schema
        
        Args:
            text: Text to extract data from
            schema: JSON schema describing expected structure
            
        Returns:
            Extracted structured data
        """
        try:
            schema_str = json.dumps(schema, indent=2)
            
            prompt = f"""
            Extract structured data from the following text according to the provided schema.
            
            Schema:
            {schema_str}
            
            Text:
            {text}
            
            Extract the data and respond with JSON that matches the schema structure.
            If a field cannot be found, use null or appropriate default value.
            """
            
            response = await self.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response)
            
        except Exception as e:
            raise Exception(f"Failed to extract structured data: {e}")

    async def classify_text(self, text: str, categories: list, examples: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Classify text into one of the provided categories
        
        Args:
            text: Text to classify
            categories: List of possible categories
            examples: Optional examples for few-shot learning
            
        Returns:
            Classification result with category and confidence
        """
        try:
            categories_str = ", ".join(categories)
            
            examples_text = ""
            if examples:
                examples_text = "Examples:\n" + "\n".join([
                    f"Text: {text}\nCategory: {category}"
                    for text, category in examples.items()
                ]) + "\n\n"
            
            prompt = f"""
            Classify the following text into one of these categories: {categories_str}
            
            {examples_text}Text to classify:
            {text}
            
            Respond with JSON in this format:
            {{"category": "category_name", "confidence": 0.0-1.0, "reasoning": "explanation"}}
            """
            
            response = await self.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            
            # Validate category is in allowed list
            predicted_category = result.get("category", "unknown")
            if predicted_category not in categories:
                predicted_category = categories[0]  # Default to first category
            
            return {
                "category": predicted_category,
                "confidence": max(0, min(1, result.get("confidence", 0.5))),
                "reasoning": result.get("reasoning", "")
            }
            
        except Exception as e:
            raise Exception(f"Failed to classify text: {e}")
