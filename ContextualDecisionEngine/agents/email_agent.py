"""
Email Agent - Processes email content and extracts structured fields
Identifies tone and triggers actions based on urgency and sentiment
"""

import json
import re
from typing import Dict, Any
from ContextualDecisionEngine.utils.openai_client import OpenAIClient
from ContextualDecisionEngine.memory.store import MemoryStore

class EmailAgent:
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        self.openai_client = OpenAIClient()

    async def process(self, content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process email content and extract structured fields
        
        Args:
            content: Email content to process
            classification: Classification result from classifier agent
            
        Returns:
            Dictionary with extracted fields and processing results
        """
        try:
            # Extract structured fields from email
            extracted_fields = await self._extract_email_fields(content)
            
            # Analyze tone and sentiment
            tone_analysis = await self._analyze_tone(content)
            
            # Determine urgency level
            urgency_level = await self._determine_urgency(content, tone_analysis)
            
            # Determine action based on tone and urgency
            recommended_action = self._determine_action(tone_analysis, urgency_level)
            
            # Prepare result
            result = {
                "agent_type": "Email",
                "extracted_fields": extracted_fields,
                "tone_analysis": tone_analysis,
                "urgency_level": urgency_level,
                "recommended_action": recommended_action,
                "processing_timestamp": self.memory_store.get_current_timestamp()
            }
            
            # Store in memory
            self.memory_store.store_agent_result("email", result)
            
            return result
            
        except Exception as e:
            raise Exception(f"Email processing failed: {str(e)}")

    async def _extract_email_fields(self, content: str) -> Dict[str, Any]:
        """Extract structured fields from email content"""
        
        prompt = f"""
        Extract structured information from the following email content.
        
        Email content:
        {content}
        
        Extract the following fields and respond with JSON:
        - sender: email address or name of sender
        - recipient: email address or name of recipient  
        - subject: email subject line
        - issue_type: main issue or request type
        - key_points: list of main points or requests
        - contact_info: any contact information mentioned
        - deadline_mentioned: any deadlines or time-sensitive information
        
        Respond with JSON in this format:
        {{
            "sender": "string",
            "recipient": "string", 
            "subject": "string",
            "issue_type": "string",
            "key_points": ["string"],
            "contact_info": "string",
            "deadline_mentioned": "string"
        }}
        """
        
        try:
            response = await self.openai_client.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response)
            
        except Exception as e:
            # Fallback extraction using regex
            return self._fallback_extract_fields(content)

    def _fallback_extract_fields(self, content: str) -> Dict[str, Any]:
        """Fallback extraction using regex patterns"""
        
        # Extract sender
        sender_match = re.search(r'From:\s*([^\n\r]+)', content, re.IGNORECASE)
        sender = sender_match.group(1).strip() if sender_match else "Unknown"
        
        # Extract subject
        subject_match = re.search(r'Subject:\s*([^\n\r]+)', content, re.IGNORECASE)
        subject = subject_match.group(1).strip() if subject_match else "No Subject"
        
        # Extract recipient
        recipient_match = re.search(r'To:\s*([^\n\r]+)', content, re.IGNORECASE)
        recipient = recipient_match.group(1).strip() if recipient_match else "Unknown"
        
        return {
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "issue_type": "General Inquiry",
            "key_points": [content[:100] + "..."],
            "contact_info": sender,
            "deadline_mentioned": "None specified"
        }

    async def _analyze_tone(self, content: str) -> Dict[str, Any]:
        """Analyze tone and sentiment of email content"""
        
        prompt = f"""
        Analyze the tone and sentiment of the following email content.
        
        Email content:
        {content}
        
        Classify the tone into one of these categories:
        - polite: Professional, courteous, respectful
        - escalation: Frustrated but controlled, seeking resolution
        - threatening: Aggressive, demanding, mentions consequences
        - neutral: Factual, no strong emotional indicators
        - urgent: Time-sensitive, requires immediate attention
        
        Respond with JSON in this format:
        {{
            "tone": "polite|escalation|threatening|neutral|urgent",
            "sentiment_score": 0.0-1.0,
            "emotional_indicators": ["string"],
            "politeness_level": "high|medium|low",
            "reasoning": "explanation"
        }}
        """
        
        try:
            response = await self.openai_client.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response)
            
        except Exception as e:
            # Fallback tone analysis
            content_lower = content.lower()
            
            if any(word in content_lower for word in ["urgent", "asap", "immediately", "emergency"]):
                tone = "urgent"
                sentiment_score = 0.8
            elif any(word in content_lower for word in ["disappointed", "frustrated", "unacceptable", "demand"]):
                tone = "escalation"
                sentiment_score = 0.3
            elif any(word in content_lower for word in ["threat", "legal", "lawsuit", "report"]):
                tone = "threatening"
                sentiment_score = 0.1
            elif any(word in content_lower for word in ["please", "thank", "appreciate", "kindly"]):
                tone = "polite"
                sentiment_score = 0.9
            else:
                tone = "neutral"
                sentiment_score = 0.5
            
            return {
                "tone": tone,
                "sentiment_score": sentiment_score,
                "emotional_indicators": [],
                "politeness_level": "medium",
                "reasoning": "Fallback analysis based on keyword detection"
            }

    async def _determine_urgency(self, content: str, tone_analysis: Dict[str, Any]) -> str:
        """Determine urgency level based on content and tone"""
        
        content_lower = content.lower()
        urgency_keywords = {
            "high": ["urgent", "asap", "immediately", "emergency", "critical", "deadline"],
            "medium": ["soon", "priority", "important", "escalate"],
            "low": ["when possible", "convenient", "no rush", "whenever"]
        }
        
        # Check for urgency keywords
        high_count = sum(1 for keyword in urgency_keywords["high"] if keyword in content_lower)
        medium_count = sum(1 for keyword in urgency_keywords["medium"] if keyword in content_lower)
        low_count = sum(1 for keyword in urgency_keywords["low"] if keyword in content_lower)
        
        # Factor in tone analysis
        tone = tone_analysis.get("tone", "neutral")
        if tone in ["threatening", "urgent"]:
            return "high"
        elif tone == "escalation":
            return "medium" if medium_count > 0 or high_count > 0 else "medium"
        
        # Determine based on keyword counts
        if high_count > 0:
            return "high"
        elif medium_count > 0:
            return "medium"
        elif low_count > 0:
            return "low"
        else:
            return "medium"  # Default

    def _determine_action(self, tone_analysis: Dict[str, Any], urgency_level: str) -> str:
        """Determine recommended action based on tone and urgency"""
        
        tone = tone_analysis.get("tone", "neutral")
        
        # Action mapping based on tone and urgency
        if tone == "threatening" or (tone == "escalation" and urgency_level == "high"):
            return "escalate_immediate"
        elif tone == "escalation" or urgency_level == "high":
            return "escalate_standard" 
        elif tone == "urgent":
            return "prioritize"
        elif tone == "polite" and urgency_level == "low":
            return "log_and_acknowledge"
        else:
            return "standard_response"
