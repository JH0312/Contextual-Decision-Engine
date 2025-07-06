"""
Classifier Agent - Detects format and business intent using OpenAI
Uses few-shot examples and schema matching for accurate classification
"""

import json
from typing import Dict, Any, Optional
from ContextualDecisionEngine.utils.openai_client import OpenAIClient
from ContextualDecisionEngine.memory.store import MemoryStore

class ClassifierAgent:
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        self.openai_client = OpenAIClient()
        
        # Few-shot examples for classification
        self.few_shot_examples = {
            "format_examples": [
                {
                    "input": "From: john@company.com\nSubject: Urgent Issue\nDear Support Team...",
                    "format": "Email"
                },
                {
                    "input": '{"customer_id": 123, "amount": 1500.00, "type": "invoice"}',
                    "format": "JSON"
                },
                {
                    "input": "INVOICE\nCompany: ABC Corp\nTotal: $5,000.00\nLine items...",
                    "format": "PDF"
                }
            ],
            "intent_examples": [
                {
                    "input": "We need a quote for 100 units of product X by Friday",
                    "intent": "RFQ"
                },
                {
                    "input": "I am extremely disappointed with the service quality",
                    "intent": "Complaint"
                },
                {
                    "input": "Invoice #12345 for $2,500 due on 2024-01-15",
                    "intent": "Invoice"
                },
                {
                    "input": "New GDPR compliance requirements effective immediately",
                    "intent": "Regulation"
                },
                {
                    "input": "Suspicious transaction pattern detected in account",
                    "intent": "Fraud Risk"
                }
            ]
        }

    async def classify(self, content: str, detected_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify input format and business intent
        
        Args:
            content: Input content to classify
            detected_format: Pre-detected format (optional)
            
        Returns:
            Dictionary with classification results
        """
        try:
            # If format is already detected (e.g., from file extension), use it
            format_result = detected_format
            
            # If format not detected, classify it
            if not format_result:
                format_result = await self._classify_format(content)
            
            # Classify business intent
            intent_result = await self._classify_intent(content)
            
            # Store classification in memory
            classification_data = {
                "format": format_result,
                "intent": intent_result,
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "confidence_score": 0.85  # Placeholder - in real implementation, extract from OpenAI response
            }
            
            self.memory_store.store_classification(classification_data)
            
            return classification_data
            
        except Exception as e:
            raise Exception(f"Classification failed: {str(e)}")

    async def _classify_format(self, content: str) -> str:
        """Classify the format of the input content"""
        
        # Prepare few-shot examples for format classification
        examples_text = "\n\n".join([
            f"Input: {ex['input'][:100]}...\nFormat: {ex['format']}"
            for ex in self.few_shot_examples["format_examples"]
        ])
        
        prompt = f"""
        You are a format classification expert. Based on the following examples, classify the format of the given input.
        
        Examples:
        {examples_text}
        
        Available formats: Email, JSON, PDF
        
        Input to classify:
        {content[:500]}
        
        Analyze the structure, patterns, and content to determine the format.
        Respond with JSON in this exact format: {{"format": "Email|JSON|PDF", "reasoning": "explanation"}}
        """
        
        try:
            response = await self.openai_client.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"},
                max_tokens=200
            )
            
            result = json.loads(response)
            return result.get("format", "Unknown")
            
        except Exception as e:
            # Fallback logic for format detection
            content_lower = content.lower()
            if any(keyword in content_lower for keyword in ["from:", "to:", "subject:", "@"]):
                return "Email"
            elif content.strip().startswith(("{", "[")):
                return "JSON"
            else:
                return "PDF"

    async def _classify_intent(self, content: str) -> str:
        """Classify the business intent of the input content"""
        
        # Prepare few-shot examples for intent classification
        examples_text = "\n\n".join([
            f"Input: {ex['input']}\nIntent: {ex['intent']}"
            for ex in self.few_shot_examples["intent_examples"]
        ])
        
        prompt = f"""
        You are a business intent classification expert. Based on the following examples, classify the business intent of the given input.
        
        Examples:
        {examples_text}
        
        Available intents: Policy Review, Invoice Processing, Contract Review, Customer Service, Risk Assessment, Documentation, General Document
        
        Input to classify:
        {content[:1000]}
        
        Analyze the content, keywords, and context to determine the business intent.
        Respond with JSON in this exact format: {{"intent": "RFQ|Complaint|Invoice|Regulation|Fraud Risk", "reasoning": "explanation", "confidence": 0.0-1.0}}
        """
        
        try:
            response = await self.openai_client.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            return result.get("intent", "Unknown")
            
        except Exception as e:
            # Enhanced fallback logic for intent detection
            content_lower = content.lower()
            
            # Policy and regulatory documents
            if any(keyword in content_lower for keyword in [
                "policy", "gdpr", "regulation", "compliance", "privacy", "data protection",
                "hipaa", "sox", "pci", "iso", "audit", "governance", "security policy",
                "acceptable use", "code of conduct", "regulatory", "legal", "terms"
            ]):
                return "Policy Review"
            
            # Invoice and financial documents
            elif any(keyword in content_lower for keyword in [
                "invoice", "bill", "payment", "amount", "total", "subtotal", "tax",
                "purchase order", "receipt", "financial", "accounting", "cost"
            ]):
                return "Invoice Processing"
            
            # Contract and agreement documents
            elif any(keyword in content_lower for keyword in [
                "contract", "agreement", "terms and conditions", "sla", "statement of work",
                "proposal", "quote", "rfq", "quotation", "pricing", "vendor"
            ]):
                return "Contract Review"
            
            # Complaint and issue documents
            elif any(keyword in content_lower for keyword in [
                "complaint", "issue", "problem", "disappointed", "dissatisfied",
                "escalation", "urgent", "critical", "failure", "error"
            ]):
                return "Customer Service"
            
            # Risk and fraud documents
            elif any(keyword in content_lower for keyword in [
                "fraud", "suspicious", "risk", "alert", "anomaly", "unusual",
                "investigation", "security incident", "breach"
            ]):
                return "Risk Assessment"
            
            # Technical documentation
            elif any(keyword in content_lower for keyword in [
                "manual", "documentation", "specification", "technical", "procedure",
                "installation", "configuration", "setup", "guide"
            ]):
                return "Documentation"
            
            # Default for unclassified content
            else:
                return "General Document"
