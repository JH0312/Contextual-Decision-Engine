"""
PDF Agent - Extracts fields from PDF documents using PDF parsers
Processes invoices and policy documents with specific flagging rules
"""

import os
import re
import json
from typing import Dict, Any, List
import PyPDF2
from ContextualDecisionEngine.utils.openai_client import OpenAIClient
from ContextualDecisionEngine.memory.store import MemoryStore

class PDFAgent:
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        self.openai_client = OpenAIClient()
        
        # Compliance keywords to flag
        self.compliance_keywords = {
            "GDPR": ["gdpr", "general data protection regulation", "data protection"],
            "FDA": ["fda", "food and drug administration", "medical device"],
            "HIPAA": ["hipaa", "health insurance portability"],
            "SOX": ["sarbanes-oxley", "sox", "financial reporting"],
            "PCI": ["pci", "payment card industry", "credit card"]
        }

    async def process(self, content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process PDF content and extract structured fields
        
        Args:
            content: PDF file path (for file uploads) or text content
            classification: Classification result from classifier agent
            
        Returns:
            Dictionary with extracted fields and processing results
        """
        try:
            # Extract text from PDF
            if content.startswith('/tmp') and content.endswith('.pdf'):
                # It's a file path
                pdf_text = self._extract_text_from_pdf(content)
            else:
                # It's already text content
                pdf_text = content
            
            # Determine document type
            doc_type = await self._determine_document_type(pdf_text)
            
            # Extract fields based on document type
            if doc_type == "invoice":
                extracted_data = await self._process_invoice(pdf_text)
            elif doc_type == "policy":
                extracted_data = await self._process_policy_document(pdf_text)
            else:
                extracted_data = await self._process_general_document(pdf_text)
            
            # Check for flagging conditions
            flags = self._check_flagging_conditions(extracted_data, pdf_text)
            
            # Assess compliance requirements
            compliance_flags = self._check_compliance_flags(pdf_text)
            
            # Prepare result
            result = {
                "agent_type": "PDF",
                "document_type": doc_type,
                "extracted_data": extracted_data,
                "flags": flags,
                "compliance_flags": compliance_flags,
                "text_length": len(pdf_text),
                "processing_timestamp": self.memory_store.get_current_timestamp()
            }
            
            # Store in memory
            self.memory_store.store_agent_result("pdf", result)
            
            return result
            
        except Exception as e:
            raise Exception(f"PDF processing failed: {str(e)}")

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF file"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    async def _determine_document_type(self, text: str) -> str:
        """Determine the type of PDF document"""
        
        text_lower = text.lower()
        
        # Check for invoice indicators
        invoice_keywords = ["invoice", "bill", "amount due", "total", "line item", "payment terms"]
        invoice_score = sum(1 for keyword in invoice_keywords if keyword in text_lower)
        
        # Check for policy indicators
        policy_keywords = ["policy", "procedure", "regulation", "compliance", "guidelines", "terms"]
        policy_score = sum(1 for keyword in policy_keywords if keyword in text_lower)
        
        if invoice_score > policy_score and invoice_score >= 2:
            return "invoice"
        elif policy_score >= 2:
            return "policy"
        
        # Use AI for more complex determination
        try:
            prompt = f"""
            Analyze the following document text and determine its type.
            
            Document text (first 1000 characters):
            {text[:1000]}
            
            Possible types: invoice, policy, contract, report, general
            
            Respond with JSON in this format:
            {{"document_type": "invoice|policy|contract|report|general", "confidence": 0.0-1.0, "reasoning": "explanation"}}
            """
            
            response = await self.openai_client.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            return result.get("document_type", "general")
            
        except Exception:
            return "general"

    async def _process_invoice(self, text: str) -> Dict[str, Any]:
        """Process invoice document and extract line items and totals"""
        
        prompt = f"""
        Extract structured invoice information from the following text.
        
        Invoice text:
        {text}
        
        Extract the following information and respond with JSON:
        - invoice_number: invoice ID or number
        - total_amount: total amount due (number only)
        - currency: currency code if mentioned
        - invoice_date: date of invoice
        - due_date: payment due date
        - vendor_name: name of vendor/company
        - customer_name: name of customer/buyer
        - line_items: array of line items with description and amount
        - tax_amount: tax amount if specified
        - subtotal: subtotal before tax
        
        Respond with JSON in this format:
        {{
            "invoice_number": "string",
            "total_amount": number,
            "currency": "string",
            "invoice_date": "string",
            "due_date": "string", 
            "vendor_name": "string",
            "customer_name": "string",
            "line_items": [
                {{"description": "string", "amount": number, "quantity": number}}
            ],
            "tax_amount": number,
            "subtotal": number
        }}
        """
        
        try:
            response = await self.openai_client.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response)
            
        except Exception:
            # Fallback extraction using regex
            return self._fallback_extract_invoice(text)

    def _fallback_extract_invoice(self, text: str) -> Dict[str, Any]:
        """Fallback invoice extraction using regex patterns"""
        
        # Extract total amount
        amount_patterns = [
            r'total[:\s]+\$?(\d+[\d,]*\.?\d*)',
            r'amount due[:\s]+\$?(\d+[\d,]*\.?\d*)',
            r'\$(\d+[\d,]*\.?\d*)\s*total'
        ]
        
        total_amount = 0
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    total_amount = float(amount_str)
                    break
                except ValueError:
                    continue
        
        # Extract invoice number
        invoice_patterns = [
            r'invoice\s*#?\s*(\w+)',
            r'inv\s*#?\s*(\w+)',
            r'#(\d+)'
        ]
        
        invoice_number = "Unknown"
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_number = match.group(1)
                break
        
        return {
            "invoice_number": invoice_number,
            "total_amount": total_amount,
            "currency": "USD",
            "invoice_date": "Not found",
            "due_date": "Not found",
            "vendor_name": "Not found",
            "customer_name": "Not found",
            "line_items": [],
            "tax_amount": 0,
            "subtotal": total_amount
        }

    async def _process_policy_document(self, text: str) -> Dict[str, Any]:
        """Process policy document and extract key information"""
        
        prompt = f"""
        Extract structured information from the following policy document.
        
        Policy text:
        {text[:2000]}
        
        Extract the following information and respond with JSON:
        - policy_title: title of the policy
        - effective_date: when the policy becomes effective
        - policy_type: type of policy (privacy, security, compliance, etc.)
        - key_requirements: list of main requirements or rules
        - compliance_standards: any compliance standards mentioned
        - penalties_mentioned: any penalties or consequences mentioned
        - review_date: next review date if mentioned
        
        Respond with JSON in this format:
        {{
            "policy_title": "string",
            "effective_date": "string",
            "policy_type": "string",
            "key_requirements": ["string"],
            "compliance_standards": ["string"],
            "penalties_mentioned": ["string"],
            "review_date": "string"
        }}
        """
        
        try:
            response = await self.openai_client.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response)
            
        except Exception:
            # Fallback extraction
            return {
                "policy_title": "Policy Document",
                "effective_date": "Not specified",
                "policy_type": "General",
                "key_requirements": [],
                "compliance_standards": [],
                "penalties_mentioned": [],
                "review_date": "Not specified"
            }

    async def _process_general_document(self, text: str) -> Dict[str, Any]:
        """Process general document type"""
        
        return {
            "document_summary": text[:200] + "..." if len(text) > 200 else text,
            "word_count": len(text.split()),
            "key_topics": [],
            "document_structure": "General document"
        }

    def _check_flagging_conditions(self, extracted_data: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """Check for conditions that require flagging"""
        
        flags = []
        
        # Flag high-value invoices (>$10,000)
        if "total_amount" in extracted_data:
            total_amount = extracted_data.get("total_amount", 0)
            if isinstance(total_amount, (int, float)) and total_amount > 10000:
                flags.append({
                    "type": "high_value_invoice",
                    "severity": "medium",
                    "description": f"Invoice amount ${total_amount:,.2f} exceeds $10,000 threshold",
                    "amount": total_amount,
                    "requires_approval": True
                })
        
        # Flag missing critical invoice information
        if extracted_data.get("invoice_number") == "Unknown":
            flags.append({
                "type": "missing_invoice_number",
                "severity": "high",
                "description": "Invoice number could not be extracted",
                "requires_review": True
            })
        
        # Flag policy documents with specific mentions
        text_lower = text.lower()
        policy_flags = ["audit", "violation", "penalty", "non-compliance"]
        for flag_term in policy_flags:
            if flag_term in text_lower:
                flags.append({
                    "type": f"policy_{flag_term}",
                    "severity": "medium",
                    "description": f"Policy document mentions '{flag_term}'",
                    "keyword": flag_term
                })
        
        return flags

    def _check_compliance_flags(self, text: str) -> List[Dict[str, Any]]:
        """Check for compliance-related keywords and regulations"""
        
        compliance_flags = []
        text_lower = text.lower()
        
        for regulation, keywords in self.compliance_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Count occurrences
                    count = text_lower.count(keyword)
                    compliance_flags.append({
                        "regulation": regulation,
                        "keyword": keyword,
                        "occurrences": count,
                        "severity": "high" if regulation in ["GDPR", "FDA"] else "medium",
                        "description": f"Document mentions {regulation} compliance requirement",
                        "requires_legal_review": True
                    })
                    break  # Only flag once per regulation type
        
        return compliance_flags
