"""
Action Router - Triggers follow-up actions based on agent outputs
Routes to CRM, risk alerts, compliance flags via simulated REST calls
"""

import json
import requests
from typing import Dict, Any, List
from ContextualDecisionEngine.memory.store import MemoryStore

class ActionRouter:
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        
        # Base URL for API calls (assuming same host for simulation)
        self.base_url = "http://localhost:5000"
        
        # Action mapping rules
        self.action_rules = {
            "email": {
                "escalate_immediate": ["crm_escalate", "risk_alert"],
                "escalate_standard": ["crm_escalate"],
                "prioritize": ["crm_log"],
                "log_and_acknowledge": ["crm_log"],
                "standard_response": ["crm_log"]
            },
            "json": {
                "high_risk": ["risk_alert", "compliance_flag"],
                "medium_risk": ["risk_alert"],
                "low_risk": ["log_only"]
            },
            "pdf": {
                "high_value_invoice": ["compliance_flag", "approval_required"],
                "compliance_required": ["compliance_flag", "legal_review"],
                "standard_processing": ["log_only"]
            }
        }

    async def route_action(self, agent_result: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route and trigger follow-up actions based on agent processing results
        
        Args:
            agent_result: Result from specialized agent processing
            classification: Original classification from classifier agent
            
        Returns:
            Dictionary with triggered actions and their results
        """
        try:
            # Determine actions to trigger based on agent type and results
            actions_to_trigger = self._determine_actions(agent_result, classification)
            
            # Execute each action
            action_results = []
            for action in actions_to_trigger:
                result = await self._execute_action(action, agent_result, classification)
                action_results.append(result)
            
            # Aggregate results
            action_summary = {
                "actions_triggered": action_results,
                "total_actions": len(action_results),
                "successful_actions": sum(1 for r in action_results if r.get("success", False)),
                "failed_actions": sum(1 for r in action_results if not r.get("success", False)),
                "routing_timestamp": self.memory_store.get_current_timestamp()
            }
            
            # Log decision
            self.memory_store.log_decision(
                component="action_router",
                decision_type="action_routing",
                decision_data={
                    "agent_type": agent_result.get("agent_type"),
                    "classification": classification,
                    "actions_determined": [a["action_type"] for a in actions_to_trigger]
                },
                reasoning=f"Determined {len(actions_to_trigger)} actions based on agent results"
            )
            
            return action_summary
            
        except Exception as e:
            raise Exception(f"Action routing failed: {str(e)}")

    def _determine_actions(self, agent_result: Dict[str, Any], classification: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine which actions to trigger based on agent results"""
        
        actions = []
        agent_type = agent_result.get("agent_type", "").lower()
        
        if agent_type == "email":
            actions.extend(self._determine_email_actions(agent_result))
        elif agent_type == "json":
            actions.extend(self._determine_json_actions(agent_result))
        elif agent_type == "pdf":
            actions.extend(self._determine_pdf_actions(agent_result))
        
        return actions

    def _determine_email_actions(self, agent_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine actions for email processing results"""
        
        actions = []
        recommended_action = agent_result.get("recommended_action", "standard_response")
        tone = agent_result.get("tone_analysis", {}).get("tone", "neutral")
        urgency = agent_result.get("urgency_level", "medium")
        
        if recommended_action == "escalate_immediate":
            actions.append({
                "action_type": "crm_escalate",
                "priority": "high",
                "data": {
                    "urgency": urgency,
                    "tone": tone,
                    "sender": agent_result.get("extracted_fields", {}).get("sender", "unknown"),
                    "issue_type": agent_result.get("extracted_fields", {}).get("issue_type", "general")
                }
            })
            
        elif recommended_action == "escalate_standard":
            actions.append({
                "action_type": "crm_escalate",
                "priority": "medium",
                "data": {
                    "urgency": urgency,
                    "tone": tone,
                    "sender": agent_result.get("extracted_fields", {}).get("sender", "unknown")
                }
            })
            
        else:
            actions.append({
                "action_type": "crm_log",
                "priority": "low",
                "data": {
                    "action_taken": recommended_action,
                    "sender": agent_result.get("extracted_fields", {}).get("sender", "unknown")
                }
            })
        
        return actions

    def _determine_json_actions(self, agent_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine actions for JSON processing results"""
        
        actions = []
        risk_level = agent_result.get("risk_level", "low")
        anomalies = agent_result.get("anomalies", [])
        
        if risk_level == "high":
            actions.append({
                "action_type": "risk_alert",
                "priority": "high",
                "data": {
                    "risk_level": risk_level,
                    "anomaly_count": len(anomalies),
                    "anomalies": anomalies[:3],  # Top 3 anomalies
                    "json_type": agent_result.get("json_type", "unknown")
                }
            })
            
        elif risk_level == "medium":
            actions.append({
                "action_type": "risk_alert",
                "priority": "medium", 
                "data": {
                    "risk_level": risk_level,
                    "anomaly_count": len(anomalies),
                    "json_type": agent_result.get("json_type", "unknown")
                }
            })
        
        # Check for compliance issues
        if anomalies:
            compliance_anomalies = [a for a in anomalies if a.get("severity") == "high"]
            if compliance_anomalies:
                actions.append({
                    "action_type": "compliance_flag",
                    "priority": "high",
                    "data": {
                        "compliance_issues": compliance_anomalies,
                        "json_type": agent_result.get("json_type", "unknown")
                    }
                })
        
        return actions

    def _determine_pdf_actions(self, agent_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Determine actions for PDF processing results"""
        
        actions = []
        flags = agent_result.get("flags", [])
        compliance_flags = agent_result.get("compliance_flags", [])
        extracted_data = agent_result.get("extracted_data", {})
        
        # Check for high-value invoice flag
        high_value_flags = [f for f in flags if f.get("type") == "high_value_invoice"]
        if high_value_flags:
            actions.append({
                "action_type": "compliance_flag",
                "priority": "high",
                "data": {
                    "flag_type": "high_value_invoice",
                    "amount": high_value_flags[0].get("amount", 0),
                    "requires_approval": True
                }
            })
        
        # Check for compliance requirements
        if compliance_flags:
            for comp_flag in compliance_flags:
                if comp_flag.get("requires_legal_review"):
                    actions.append({
                        "action_type": "compliance_flag",
                        "priority": "high",
                        "data": {
                            "regulation": comp_flag.get("regulation"),
                            "keyword": comp_flag.get("keyword"),
                            "requires_legal_review": True
                        }
                    })
        
        # Standard processing action
        if not actions:
            actions.append({
                "action_type": "log_only",
                "priority": "low",
                "data": {
                    "document_type": agent_result.get("document_type", "unknown"),
                    "processing_status": "completed"
                }
            })
        
        return actions

    async def _execute_action(self, action: Dict[str, Any], agent_result: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific action via API call"""
        
        action_type = action.get("action_type")
        priority = action.get("priority", "medium")
        data = action.get("data", {})
        
        # Prepare payload for API call
        payload = {
            "priority": priority,
            "timestamp": self.memory_store.get_current_timestamp(),
            "source_agent": agent_result.get("agent_type"),
            "classification": {
                "format": classification.get("format"),
                "intent": classification.get("intent")
            },
            "action_data": data
        }
        
        try:
            if action_type == "crm_escalate":
                response = await self._call_crm_escalate(payload)
            elif action_type == "crm_log":
                response = await self._call_crm_log(payload)
            elif action_type == "risk_alert":
                response = await self._call_risk_alert(payload)
            elif action_type == "compliance_flag":
                response = await self._call_compliance_flag(payload)
            elif action_type == "log_only":
                response = {"success": True, "message": "Logged for audit purposes"}
            else:
                response = {"success": False, "error": f"Unknown action type: {action_type}"}
            
            return {
                "action_type": action_type,
                "success": response.get("success", False),
                "response": response,
                "execution_timestamp": self.memory_store.get_current_timestamp()
            }
            
        except Exception as e:
            return {
                "action_type": action_type,
                "success": False,
                "error": str(e),
                "execution_timestamp": self.memory_store.get_current_timestamp()
            }

    async def _call_crm_escalate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call CRM escalation endpoint"""
        try:
            response = requests.post(
                f"{self.base_url}/crm/escalate",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _call_crm_log(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call CRM logging endpoint"""
        try:
            response = requests.post(
                f"{self.base_url}/crm/log",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _call_risk_alert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call risk alert endpoint"""
        try:
            response = requests.post(
                f"{self.base_url}/risk_alert",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _call_compliance_flag(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call compliance flagging endpoint"""
        try:
            response = requests.post(
                f"{self.base_url}/compliance/flag",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
