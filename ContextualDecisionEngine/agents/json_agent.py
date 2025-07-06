"""
JSON Agent - Parses webhook data and validates schema fields
Flags anomalies and validates data integrity
"""

import json
import jsonschema
from typing import Dict, Any, List
from ContextualDecisionEngine.utils.openai_client import OpenAIClient
from ContextualDecisionEngine.memory.store import MemoryStore

class JSONAgent:
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        self.openai_client = OpenAIClient()
        
        # Expected schemas for different types of JSON data
        self.expected_schemas = {
            "webhook": {
                "type": "object",
                "required": ["timestamp", "event_type", "data"],
                "properties": {
                    "timestamp": {"type": "string"},
                    "event_type": {"type": "string"},
                    "data": {"type": "object"}
                }
            },
            "invoice": {
                "type": "object", 
                "required": ["invoice_id", "amount", "customer_id"],
                "properties": {
                    "invoice_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "customer_id": {"type": ["string", "number"]},
                    "line_items": {"type": "array"}
                }
            },
            "transaction": {
                "type": "object",
                "required": ["transaction_id", "amount", "account_id"],
                "properties": {
                    "transaction_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "account_id": {"type": "string"},
                    "timestamp": {"type": "string"}
                }
            }
        }

    async def process(self, content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process JSON content and validate schema
        
        Args:
            content: JSON content to process
            classification: Classification result from classifier agent
            
        Returns:
            Dictionary with validation results and extracted data
        """
        try:
            # Parse JSON content
            json_data = json.loads(content)
            
            # Determine JSON type and validate schema
            json_type = await self._determine_json_type(json_data)
            schema_validation = self._validate_schema(json_data, json_type)
            
            # Detect anomalies
            anomalies = await self._detect_anomalies(json_data, json_type)
            
            # Extract key business data
            extracted_data = await self._extract_business_data(json_data, json_type)
            
            # Determine risk level
            risk_level = self._assess_risk_level(anomalies, json_data)
            
            # Prepare result
            result = {
                "agent_type": "JSON",
                "json_type": json_type,
                "schema_validation": schema_validation,
                "anomalies": anomalies,
                "extracted_data": extracted_data,
                "risk_level": risk_level,
                "raw_data_size": len(content),
                "processing_timestamp": self.memory_store.get_current_timestamp()
            }
            
            # Store in memory
            self.memory_store.store_agent_result("json", result)
            
            return result
            
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise Exception(f"JSON processing failed: {str(e)}")

    async def _determine_json_type(self, json_data: Dict[str, Any]) -> str:
        """Determine the type of JSON data based on structure and content"""
        
        # Check for webhook characteristics
        if "event_type" in json_data and "timestamp" in json_data:
            return "webhook"
        
        # Check for invoice characteristics
        elif "invoice_id" in json_data or "amount" in json_data:
            return "invoice"
        
        # Check for transaction characteristics
        elif "transaction_id" in json_data or ("amount" in json_data and "account_id" in json_data):
            return "transaction"
        
        # Use OpenAI for complex determination
        try:
            prompt = f"""
            Analyze the following JSON data structure and determine its type.
            
            JSON data:
            {json.dumps(json_data, indent=2)[:1000]}
            
            Possible types: webhook, invoice, transaction, general
            
            Respond with JSON in this format:
            {{"type": "webhook|invoice|transaction|general", "reasoning": "explanation"}}
            """
            
            response = await self.openai_client.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            return result.get("type", "general")
            
        except Exception:
            return "general"

    def _validate_schema(self, json_data: Dict[str, Any], json_type: str) -> Dict[str, Any]:
        """Validate JSON data against expected schema"""
        
        validation_result = {
            "is_valid": True,
            "missing_fields": [],
            "type_errors": [],
            "extra_fields": [],
            "schema_used": json_type
        }
        
        if json_type not in self.expected_schemas:
            validation_result["is_valid"] = False
            validation_result["type_errors"].append(f"Unknown JSON type: {json_type}")
            return validation_result
        
        schema = self.expected_schemas[json_type]
        
        try:
            # Validate using jsonschema
            jsonschema.validate(json_data, schema)
            
        except jsonschema.ValidationError as e:
            validation_result["is_valid"] = False
            
            # Parse validation errors
            if "required" in str(e):
                missing_field = str(e).split("'")[1] if "'" in str(e) else "unknown"
                validation_result["missing_fields"].append(missing_field)
            else:
                validation_result["type_errors"].append(str(e))
        
        except Exception as e:
            validation_result["is_valid"] = False
            validation_result["type_errors"].append(f"Schema validation error: {str(e)}")
        
        return validation_result

    async def _detect_anomalies(self, json_data: Dict[str, Any], json_type: str) -> List[Dict[str, Any]]:
        """Detect anomalies in JSON data"""
        
        anomalies = []
        
        # Check for common anomalies based on type
        if json_type == "invoice":
            anomalies.extend(self._check_invoice_anomalies(json_data))
        elif json_type == "transaction":
            anomalies.extend(self._check_transaction_anomalies(json_data))
        elif json_type == "webhook":
            anomalies.extend(self._check_webhook_anomalies(json_data))
        
        # Use OpenAI for advanced anomaly detection
        try:
            advanced_anomalies = await self._ai_anomaly_detection(json_data, json_type)
            anomalies.extend(advanced_anomalies)
        except Exception:
            pass  # Continue with basic anomaly detection
        
        return anomalies

    def _check_invoice_anomalies(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for invoice-specific anomalies"""
        anomalies = []
        
        # Check for negative amounts
        amount = json_data.get("amount", 0)
        if isinstance(amount, (int, float)) and amount < 0:
            anomalies.append({
                "type": "negative_amount",
                "field": "amount",
                "value": amount,
                "severity": "high",
                "description": "Invoice amount is negative"
            })
        
        # Check for extremely high amounts
        if isinstance(amount, (int, float)) and amount > 100000:
            anomalies.append({
                "type": "high_amount",
                "field": "amount", 
                "value": amount,
                "severity": "medium",
                "description": "Invoice amount is unusually high"
            })
        
        # Check for missing line items on high-value invoices
        if isinstance(amount, (int, float)) and amount > 10000 and "line_items" not in json_data:
            anomalies.append({
                "type": "missing_line_items",
                "field": "line_items",
                "value": None,
                "severity": "medium",
                "description": "High-value invoice missing line item details"
            })
        
        return anomalies

    def _check_transaction_anomalies(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for transaction-specific anomalies"""
        anomalies = []
        
        # Check for duplicate transaction IDs (would need historical data in real implementation)
        transaction_id = json_data.get("transaction_id")
        if not transaction_id:
            anomalies.append({
                "type": "missing_transaction_id",
                "field": "transaction_id",
                "value": None,
                "severity": "high",
                "description": "Transaction missing unique identifier"
            })
        
        # Check for suspicious amounts
        amount = json_data.get("amount", 0)
        if isinstance(amount, (int, float)):
            if amount == 0:
                anomalies.append({
                    "type": "zero_amount",
                    "field": "amount",
                    "value": amount,
                    "severity": "medium",
                    "description": "Transaction has zero amount"
                })
            elif amount > 50000:
                anomalies.append({
                    "type": "high_value_transaction",
                    "field": "amount",
                    "value": amount,
                    "severity": "high",
                    "description": "Unusually high transaction amount - potential fraud risk"
                })
        
        return anomalies

    def _check_webhook_anomalies(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for webhook-specific anomalies"""
        anomalies = []
        
        # Check for missing or invalid timestamp
        timestamp = json_data.get("timestamp")
        if not timestamp:
            anomalies.append({
                "type": "missing_timestamp",
                "field": "timestamp",
                "value": None,
                "severity": "medium",
                "description": "Webhook missing timestamp"
            })
        
        # Check for unknown event types
        event_type = json_data.get("event_type")
        known_events = ["user.created", "user.updated", "payment.completed", "order.shipped"]
        if event_type and event_type not in known_events:
            anomalies.append({
                "type": "unknown_event_type",
                "field": "event_type",
                "value": event_type,
                "severity": "low",
                "description": f"Unknown event type: {event_type}"
            })
        
        return anomalies

    async def _ai_anomaly_detection(self, json_data: Dict[str, Any], json_type: str) -> List[Dict[str, Any]]:
        """Use AI for advanced anomaly detection"""
        
        prompt = f"""
        Analyze the following {json_type} JSON data for potential anomalies or inconsistencies.
        
        JSON data:
        {json.dumps(json_data, indent=2)}
        
        Look for:
        - Field value mismatches or inconsistencies
        - Unusual patterns or outliers
        - Missing expected relationships between fields
        - Data integrity issues
        
        Respond with JSON in this format:
        {{
            "anomalies": [
                {{
                    "type": "string",
                    "field": "string", 
                    "severity": "low|medium|high",
                    "description": "string"
                }}
            ]
        }}
        """
        
        try:
            response = await self.openai_client.chat_completion(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            return result.get("anomalies", [])
            
        except Exception:
            return []

    async def _extract_business_data(self, json_data: Dict[str, Any], json_type: str) -> Dict[str, Any]:
        """Extract key business data from JSON"""
        
        extracted = {
            "data_type": json_type,
            "key_fields": {},
            "business_metrics": {}
        }
        
        if json_type == "invoice":
            extracted["key_fields"] = {
                "invoice_id": json_data.get("invoice_id"),
                "amount": json_data.get("amount"),
                "customer_id": json_data.get("customer_id"),
                "currency": json_data.get("currency", "USD")
            }
            extracted["business_metrics"] = {
                "total_amount": json_data.get("amount", 0),
                "line_item_count": len(json_data.get("line_items", [])),
                "is_high_value": json_data.get("amount", 0) > 10000
            }
        
        elif json_type == "transaction":
            extracted["key_fields"] = {
                "transaction_id": json_data.get("transaction_id"),
                "amount": json_data.get("amount"),
                "account_id": json_data.get("account_id"),
                "type": json_data.get("type")
            }
            extracted["business_metrics"] = {
                "amount": json_data.get("amount", 0),
                "is_high_risk": json_data.get("amount", 0) > 50000,
                "account_id": json_data.get("account_id")
            }
        
        elif json_type == "webhook":
            extracted["key_fields"] = {
                "event_type": json_data.get("event_type"),
                "timestamp": json_data.get("timestamp"),
                "source": json_data.get("source", "unknown")
            }
            extracted["business_metrics"] = {
                "event_type": json_data.get("event_type"),
                "data_size": len(str(json_data.get("data", {})))
            }
        
        return extracted

    def _assess_risk_level(self, anomalies: List[Dict[str, Any]], json_data: Dict[str, Any]) -> str:
        """Assess overall risk level based on anomalies and data"""
        
        if not anomalies:
            return "low"
        
        high_severity_count = sum(1 for anomaly in anomalies if anomaly.get("severity") == "high")
        medium_severity_count = sum(1 for anomaly in anomalies if anomaly.get("severity") == "medium")
        
        if high_severity_count > 0:
            return "high"
        elif medium_severity_count > 1:
            return "high"
        elif medium_severity_count > 0:
            return "medium"
        else:
            return "low"
