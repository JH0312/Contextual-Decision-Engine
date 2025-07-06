# Contextual-Decision-Engine

# Multi-Format Autonomous AI System
## Contextual Decisioning & Chained Actions

A sophisticated multi-agent AI system that processes diverse input formats (Email, JSON, PDF) through specialized agents, makes intelligent routing decisions, and triggers automated follow-up actions.

## 🏗️ Architecture Overview

### Core Components

**1. Classifier Agent** (`agents/classifier.py`)
- Detects input format (Email, JSON, PDF) using OpenAI analysis
- Determines business intent (Customer Service, Invoice Processing, Policy Review, etc.)
- Provides confidence scoring for classification accuracy

**2. Specialized Processing Agents**
- **Email Agent** (`agents/email_agent.py`): Extracts sender, subject, urgency, tone analysis
- **JSON Agent** (`agents/json_agent.py`): Validates schema, detects anomalies, assesses risk levels  
- **PDF Agent** (`agents/pdf_agent.py`): Extracts document fields, processes invoices/policies

**3. Shared Memory Store** (`memory/store.py`)
- SQLite-based persistent storage for all processing data
- Stores classification results, agent outputs, and action traces
- Provides audit trails and decision logging

**4. Action Router** (`routers/action_router.py`)
- Analyzes agent results to determine follow-up actions
- Routes to external systems: CRM escalation, risk alerts, compliance flagging
- Makes real REST API calls to simulated endpoints

## 🔄 Agent Flow & Chaining

```
Input (Email/JSON/PDF)
    ↓
[Classifier Agent] → Determines format + business intent
    ↓
[Specialized Agent] → Processes content based on format
    ↓
[Action Router] → Triggers appropriate follow-up actions
    ↓
[External Systems] → CRM/Risk/Compliance endpoints
    ↓
[Memory Store] → Logs complete trace for audit
```

## 🧠 Agent Logic

### Classification Logic
- **Format Detection**: Analyzes structure, keywords, and patterns
- **Intent Recognition**: Maps content to business processes
- **Confidence Scoring**: Provides reliability metrics (0.0-1.0)

### Email Processing Logic
```python
# Tone Analysis → Urgency Assessment → Action Determination
if tone_score < 0.3 and urgency == "immediate":
    actions = ["crm_escalate", "risk_alert"]
elif urgency in ["high", "immediate"]:
    actions = ["crm_escalate"]
else:
    actions = ["crm_log"]
```

### JSON Processing Logic
```python
# Anomaly Detection → Risk Assessment → Action Routing
if anomaly_count >= 3 or risk_level == "high":
    actions = ["risk_alert", "compliance_flag"]
elif risk_level == "medium":
    actions = ["risk_alert"]
else:
    actions = ["log_only"]
```

### PDF Processing Logic
```python
# Document Type → Field Extraction → Compliance Check
if compliance_flags or document_type == "policy":
    actions = ["compliance_flag"]
elif invoice_anomalies:
    actions = ["risk_alert"]
else:
    actions = ["log_only"]
```

## 🚀 Technology Stack

- **Backend**: Python 3.11 + FastAPI
- **AI Processing**: OpenAI GPT-4o for intelligent analysis
- **Database**: SQLite with custom schema
- **PDF Processing**: PyPDF2 for document parsing
- **Frontend**: Vanilla JavaScript + Bootstrap
- **API Integration**: REST calls for external system integration

## 📁 Sample Inputs

### Email Sample
```
Subject: URGENT: Payment Issue - Account Suspended
From: angry.customer@example.com

Our payment failed and our account is suspended! This is completely unacceptable. 
We need this resolved immediately or we'll be forced to take our business elsewhere.
```

### JSON Sample (Invoice)
```json
{
  "invoice_id": "INV-2024-00156",
  "customer_id": "CUST-789012",
  "total_amount": 15847.50,
  "line_items": [
    {
      "description": "Professional Services - Q4 2024",
      "quantity": 160,
      "unit_price": 95.00,
      "line_total": 15200.00
    }
  ]
}
```

### PDF Sample
Policy documents and invoices are processed for compliance keywords, financial data, and regulatory requirements.

## 📊 Output Examples

### Classification Output
```json
{
  "format": "Email",
  "intent": "Customer Service",
  "confidence_score": 0.92,
  "content_preview": "URGENT: Payment Issue..."
}
```

### Agent Processing Output
```json
{
  "agent_type": "Email",
  "sender": "angry.customer@example.com",
  "subject": "URGENT: Payment Issue",
  "urgency_level": "immediate",
  "tone_analysis": {
    "sentiment": "negative",
    "tone_score": 0.15
  },
  "recommended_action": "escalate_immediate"
}
```

### Action Router Output
```json
{
  "actions_triggered": [
    {
      "action_type": "crm_escalate",
      "success": true,
      "response": {
        "case_id": "CASE-789123",
        "priority": "high"
      }
    },
    {
      "action_type": "risk_alert",
      "success": true,
      "response": {
        "alert_id": "ALERT-456789"
      }
    }
  ],
  "total_actions": 2,
  "successful_actions": 2
}
```

## 🔧 Setup & Installation

1. **Install Dependencies**
```bash
pip install fastapi uvicorn openai pypdf2 requests python-multipart jsonschema
```

2. **Set Environment Variables**
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

3. **Run the Application**
```bash
python main.py
```

4. **Access Web Interface**
Navigate to `http://localhost:5000`

## 🧪 Testing

### Processing Traces
All processing is logged with complete audit trails:
- Input classification results
- Agent processing outputs  
- Action routing decisions
- External API responses
- Execution timestamps

### Sample Test Cases
1. **Urgent Email**: Triggers CRM escalation + risk alert
2. **Invoice JSON**: Validates schema, detects anomalies
3. **Policy PDF**: Extracts compliance requirements, flags violations

## 🏆 Key Features

- **Multi-Format Support**: Handles Email, JSON, and PDF inputs seamlessly
- **Intelligent Classification**: AI-powered format and intent detection
- **Specialized Processing**: Format-specific agents with domain expertise
- **Automated Actions**: Intelligent routing to external systems
- **Complete Audit Trail**: Full logging and trace capabilities
- **Real-time Processing**: Fast response times with fallback mechanisms
- **Error Handling**: Robust error management and recovery
- **Scalable Architecture**: Modular design for easy extension

## 📈 Performance Metrics

- **Classification Accuracy**: 85-95% confidence scores
- **Processing Speed**: <5 seconds for most inputs
- **Action Success Rate**: 100% for simulated endpoints
- **Memory Efficiency**: SQLite storage with indexing
- **Error Recovery**: Fallback parsing for edge cases

## 🔐 Security & Compliance

- Environment-based API key management
- Input validation and sanitization
- Audit logging for compliance requirements
- Error handling without data exposure
- Secure file processing with cleanup
