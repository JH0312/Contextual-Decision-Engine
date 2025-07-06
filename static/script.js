/**
 * Multi-Format Autonomous AI System - Frontend JavaScript
 * Handles form submission, file uploads, and result display
 */

// Global variables
let currentTraceId = null;
let processingStartTime = null;

// Document ready initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadTraces();
});

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
    const form = document.getElementById('processForm');
    const fileInput = document.getElementById('fileInput');
    const textInput = document.getElementById('textInput');

    // Form submission
    form.addEventListener('submit', handleFormSubmission);

    // File input change
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            textInput.value = '';
            autoDetectFileType(this.files[0]);
        }
    });

    // Text input change
    textInput.addEventListener('input', function() {
        if (this.value.trim()) {
            fileInput.value = '';
        }
    });
}

/**
 * Handle form submission
 */
async function handleFormSubmission(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const fileInput = document.getElementById('fileInput');
    const textInput = document.getElementById('textInput');
    
    // Validate input
    if (!fileInput.files.length && !textInput.value.trim()) {
        showAlert('Please provide either a file or text input.', 'warning');
        return;
    }
    
    try {
        showProcessingStatus(true);
        processingStartTime = Date.now();
        
        const response = await fetch('/process', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            currentTraceId = result.trace_id;
            displayResults(result);
            showAlert('Input processed successfully!', 'success');
            loadTraces(); // Refresh traces
        } else {
            throw new Error(result.error || 'Processing failed');
        }
        
    } catch (error) {
        console.error('Processing error:', error);
        showAlert(`Processing failed: ${error.message}`, 'danger');
        displayError(error.message);
    } finally {
        showProcessingStatus(false);
    }
}

/**
 * Auto-detect file type and set input type
 */
function autoDetectFileType(file) {
    const inputTypeSelect = document.getElementById('inputType');
    const fileName = file.name.toLowerCase();
    
    if (fileName.endsWith('.pdf')) {
        inputTypeSelect.value = 'PDF';
    } else if (fileName.endsWith('.json')) {
        inputTypeSelect.value = 'JSON';
    } else if (fileName.endsWith('.eml') || fileName.endsWith('.txt')) {
        inputTypeSelect.value = 'Email';
    } else {
        inputTypeSelect.value = '';
    }
}

/**
 * Show/hide processing status
 */
function showProcessingStatus(show) {
    const statusCard = document.getElementById('statusCard');
    const processBtn = document.getElementById('processBtn');
    
    if (show) {
        statusCard.style.display = 'block';
        processBtn.disabled = true;
        processBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
    } else {
        statusCard.style.display = 'none';
        processBtn.disabled = false;
        processBtn.innerHTML = '<i class="fas fa-cogs me-2"></i>Process Input';
    }
}

/**
 * Display processing results
 */
function displayResults(result) {
    const container = document.getElementById('resultsContainer');
    const processingTime = processingStartTime ? Date.now() - processingStartTime : 0;
    
    container.innerHTML = `
        <div class="alert alert-success mb-4">
            <h6 class="alert-heading mb-2">
                <i class="fas fa-check-circle me-2"></i>Processing Complete
            </h6>
            <div class="d-flex justify-content-between">
                <span>Trace ID: <code>${result.trace_id}</code></span>
                <span>Processing Time: ${processingTime}ms</span>
            </div>
        </div>
        
        ${renderClassificationResults(result.classification)}
        ${renderAgentResults(result.agent_result)}
        ${renderActionResults(result.actions_triggered)}
    `;
}

/**
 * Render classification results
 */
function renderClassificationResults(classification) {
    const formatBadge = getFormatBadge(classification.format);
    const intentBadge = getIntentBadge(classification.intent);
    
    return `
        <div class="results-section">
            <h6><i class="fas fa-search me-2"></i>Classification Results</h6>
            <div class="row">
                <div class="col-md-6">
                    <strong>Format:</strong> ${formatBadge}
                </div>
                <div class="col-md-6">
                    <strong>Intent:</strong> ${intentBadge}
                </div>
            </div>
            <div class="mt-2">
                <strong>Confidence:</strong> 
                <span class="badge bg-info">${(classification.confidence_score * 100).toFixed(1)}%</span>
            </div>
            <div class="mt-2">
                <strong>Content Preview:</strong>
                <div class="code-block mt-1">${escapeHtml(classification.content_preview)}</div>
            </div>
        </div>
    `;
}

/**
 * Render agent processing results
 */
function renderAgentResults(agentResult) {
    const agentType = agentResult.agent_type;
    let specificResults = '';
    
    if (agentType === 'Email') {
        specificResults = renderEmailResults(agentResult);
    } else if (agentType === 'JSON') {
        specificResults = renderJSONResults(agentResult);
    } else if (agentType === 'PDF') {
        specificResults = renderPDFResults(agentResult);
    }
    
    return `
        <div class="results-section">
            <h6><i class="fas fa-cog me-2"></i>${agentType} Agent Results</h6>
            ${specificResults}
        </div>
    `;
}

/**
 * Render email-specific results
 */
function renderEmailResults(result) {
    const toneClass = getToneClass(result.tone_analysis?.tone);
    const urgencyClass = getUrgencyClass(result.urgency_level);
    
    return `
        <div class="row">
            <div class="col-md-6">
                <h6 class="h7">Extracted Fields</h6>
                <table class="table table-sm">
                    <tr><td><strong>Sender:</strong></td><td>${escapeHtml(result.extracted_fields?.sender || 'N/A')}</td></tr>
                    <tr><td><strong>Subject:</strong></td><td>${escapeHtml(result.extracted_fields?.subject || 'N/A')}</td></tr>
                    <tr><td><strong>Issue Type:</strong></td><td>${escapeHtml(result.extracted_fields?.issue_type || 'N/A')}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6 class="h7">Analysis</h6>
                <p><strong>Tone:</strong> <span class="badge ${toneClass}">${result.tone_analysis?.tone || 'Unknown'}</span></p>
                <p><strong>Urgency:</strong> <span class="badge ${urgencyClass}">${result.urgency_level || 'Unknown'}</span></p>
                <p><strong>Recommended Action:</strong> <span class="badge bg-primary">${result.recommended_action || 'None'}</span></p>
            </div>
        </div>
    `;
}

/**
 * Render JSON-specific results
 */
function renderJSONResults(result) {
    const riskClass = getRiskClass(result.risk_level);
    
    return `
        <div class="row">
            <div class="col-md-6">
                <h6 class="h7">Validation Results</h6>
                <p><strong>JSON Type:</strong> <span class="badge bg-info">${result.json_type}</span></p>
                <p><strong>Schema Valid:</strong> ${result.schema_validation?.is_valid ? 
                    '<span class="badge bg-success">Yes</span>' : 
                    '<span class="badge bg-danger">No</span>'}</p>
                <p><strong>Risk Level:</strong> <span class="badge ${riskClass}">${result.risk_level}</span></p>
            </div>
            <div class="col-md-6">
                <h6 class="h7">Anomalies</h6>
                ${result.anomalies?.length ? 
                    result.anomalies.map(anomaly => `
                        <div class="alert alert-warning alert-sm py-2">
                            <strong>${anomaly.type}:</strong> ${anomaly.description}
                        </div>
                    `).join('') : 
                    '<p class="text-muted">No anomalies detected</p>'
                }
            </div>
        </div>
    `;
}

/**
 * Render PDF-specific results
 */
function renderPDFResults(result) {
    return `
        <div class="row">
            <div class="col-md-6">
                <h6 class="h7">Document Info</h6>
                <p><strong>Type:</strong> <span class="badge bg-info">${result.document_type}</span></p>
                <p><strong>Text Length:</strong> ${result.text_length} characters</p>
                ${result.extracted_data?.total_amount ? 
                    `<p><strong>Total Amount:</strong> $${result.extracted_data.total_amount.toLocaleString()}</p>` : 
                    ''
                }
            </div>
            <div class="col-md-6">
                <h6 class="h7">Flags & Compliance</h6>
                ${result.flags?.length ? 
                    result.flags.map(flag => `
                        <div class="alert alert-warning alert-sm py-2">
                            <strong>${flag.type}:</strong> ${flag.description}
                        </div>
                    `).join('') : 
                    '<p class="text-muted">No flags raised</p>'
                }
                ${result.compliance_flags?.length ? 
                    result.compliance_flags.map(flag => `
                        <div class="alert alert-danger alert-sm py-2">
                            <strong>${flag.regulation}:</strong> ${flag.description}
                        </div>
                    `).join('') : 
                    ''
                }
            </div>
        </div>
    `;
}

/**
 * Render action results
 */
function renderActionResults(actionResult) {
    const successCount = actionResult.successful_actions || 0;
    const failedCount = actionResult.failed_actions || 0;
    const totalCount = actionResult.total_actions || 0;
    
    return `
        <div class="results-section">
            <h6><i class="fas fa-bolt me-2"></i>Actions Triggered</h6>
            <div class="row mb-3">
                <div class="col-md-4">
                    <div class="text-center">
                        <div class="h4 text-primary">${totalCount}</div>
                        <small class="text-muted">Total Actions</small>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="text-center">
                        <div class="h4 text-success">${successCount}</div>
                        <small class="text-muted">Successful</small>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="text-center">
                        <div class="h4 text-danger">${failedCount}</div>
                        <small class="text-muted">Failed</small>
                    </div>
                </div>
            </div>
            
            ${actionResult.actions_triggered?.length ? `
                <h6 class="h7">Action Details</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Action Type</th>
                                <th>Status</th>
                                <th>Response</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${actionResult.actions_triggered.map(action => `
                                <tr>
                                    <td><span class="badge bg-secondary">${action.action_type}</span></td>
                                    <td>
                                        ${action.success ? 
                                            '<span class="badge bg-success">Success</span>' : 
                                            '<span class="badge bg-danger">Failed</span>'
                                        }
                                    </td>
                                    <td>
                                        ${action.response?.message || action.error || 'No details'}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            ` : '<p class="text-muted">No actions were triggered</p>'}
        </div>
    `;
}

/**
 * Load and display processing traces
 */
async function loadTraces() {
    try {
        const response = await fetch('/memory/traces');
        const result = await response.json();
        
        if (result.success) {
            displayTraces(result.traces);
        } else {
            throw new Error(result.error || 'Failed to load traces');
        }
    } catch (error) {
        console.error('Error loading traces:', error);
        document.getElementById('tracesContainer').innerHTML = `
            <div class="alert alert-danger">
                Failed to load processing history: ${error.message}
            </div>
        `;
    }
}

/**
 * Display processing traces
 */
function displayTraces(traces) {
    const container = document.getElementById('tracesContainer');
    
    if (!traces || traces.length === 0) {
        container.innerHTML = `
            <div class="text-muted text-center py-3">
                <i class="fas fa-clock fa-2x mb-3"></i>
                <p>No processing history yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = traces.map(trace => `
        <div class="trace-item">
            <div class="trace-header">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>Trace:</strong> <code>${trace.trace_id}</code>
                        <span class="ms-3">
                            ${getFormatBadge(trace.classification?.format)} 
                            ${getIntentBadge(trace.classification?.intent)}
                        </span>
                    </div>
                    <div>
                        <small class="text-muted">${formatTimestamp(trace.timestamp)}</small>
                        <span class="status-indicator status-${trace.status} ms-2">
                            <i class="fas fa-check-circle"></i> ${trace.status}
                        </span>
                    </div>
                </div>
            </div>
            <div class="trace-body">
                <div class="row">
                    <div class="col-md-4">
                        <h6 class="h7">Agent Processing</h6>
                        <p><strong>Type:</strong> ${trace.agent_result?.agent_type || 'Unknown'}</p>
                        <p><strong>Content:</strong> ${escapeHtml(trace.classification?.content_preview || 'N/A')}</p>
                    </div>
                    <div class="col-md-4">
                        <h6 class="h7">Actions Triggered</h6>
                        <p><strong>Total:</strong> ${trace.action_result?.actions_triggered?.length || 0}</p>
                        <p><strong>Success:</strong> ${trace.action_result?.success_count || 0}</p>
                        <p><strong>Failed:</strong> ${trace.action_result?.failure_count || 0}</p>
                    </div>
                    <div class="col-md-4">
                        <button class="btn btn-outline-primary btn-sm" onclick="viewTraceDetails('${trace.trace_id}')">
                            <i class="fas fa-eye me-2"></i>View Details
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * View detailed trace information
 */
async function viewTraceDetails(traceId) {
    try {
        const response = await fetch(`/memory/trace/${traceId}`);
        const result = await response.json();
        
        if (result.success) {
            showTraceModal(result.trace);
        } else {
            throw new Error(result.error || 'Failed to load trace details');
        }
    } catch (error) {
        console.error('Error loading trace details:', error);
        showAlert(`Failed to load trace details: ${error.message}`, 'danger');
    }
}

/**
 * Show trace details in modal
 */
function showTraceModal(trace) {
    const modalHtml = `
        <div class="modal fade" id="traceModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Trace Details: ${trace.trace_id}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="accordion" id="traceAccordion">
                            <div class="accordion-item">
                                <h2 class="accordion-header">
                                    <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#classification">
                                        Classification Data
                                    </button>
                                </h2>
                                <div id="classification" class="accordion-collapse collapse show">
                                    <div class="accordion-body">
                                        <pre class="code-block">${JSON.stringify(trace.classification, null, 2)}</pre>
                                    </div>
                                </div>
                            </div>
                            <div class="accordion-item">
                                <h2 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#agent">
                                        Agent Results
                                    </button>
                                </h2>
                                <div id="agent" class="accordion-collapse collapse">
                                    <div class="accordion-body">
                                        <pre class="code-block">${JSON.stringify(trace.agent_result, null, 2)}</pre>
                                    </div>
                                </div>
                            </div>
                            <div class="accordion-item">
                                <h2 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#actions">
                                        Action Results
                                    </button>
                                </h2>
                                <div id="actions" class="accordion-collapse collapse">
                                    <div class="accordion-body">
                                        <pre class="code-block">${JSON.stringify(trace.action_result, null, 2)}</pre>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('traceModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('traceModal'));
    modal.show();
}

/**
 * Load sample data functions
 */
function loadSampleEmail() {
    fetch('/samples/sample_email.txt')
        .then(response => response.text())
        .then(text => {
            document.getElementById('textInput').value = text;
            document.getElementById('fileInput').value = '';
            document.getElementById('inputType').value = 'Email';
        })
        .catch(error => {
            console.error('Error loading sample email:', error);
            document.getElementById('textInput').value = 'From: customer@company.com\nTo: support@business.com\nSubject: Urgent Issue with Recent Order\n\nDear Support Team,\n\nI am extremely disappointed with the quality of service I received with my recent order #12345. The product arrived damaged and I need immediate assistance to resolve this issue.\n\nThis is unacceptable and I expect a prompt response.\n\nRegards,\nJohn Smith';
            document.getElementById('inputType').value = 'Email';
        });
}

function loadSampleJSON() {
    fetch('/samples/sample_invoice.json')
        .then(response => response.text())
        .then(text => {
            document.getElementById('textInput').value = text;
            document.getElementById('fileInput').value = '';
            document.getElementById('inputType').value = 'JSON';
        })
        .catch(error => {
            console.error('Error loading sample JSON:', error);
            document.getElementById('textInput').value = '{\n  "invoice_id": "INV-2024-001",\n  "customer_id": "CUST-12345",\n  "amount": 15000.00,\n  "currency": "USD",\n  "line_items": [\n    {"description": "Professional Services", "amount": 12000.00, "quantity": 1},\n    {"description": "Additional Consulting", "amount": 3000.00, "quantity": 1}\n  ],\n  "invoice_date": "2024-01-15",\n  "due_date": "2024-02-15"\n}';
            document.getElementById('inputType').value = 'JSON';
        });
}

function loadSamplePolicy() {
    fetch('/samples/sample_policy.txt')
        .then(response => response.text())
        .then(text => {
            document.getElementById('textInput').value = text;
            document.getElementById('fileInput').value = '';
            document.getElementById('inputType').value = 'PDF';
        })
        .catch(error => {
            console.error('Error loading sample policy:', error);
            document.getElementById('textInput').value = 'COMPANY PRIVACY POLICY\n\nEffective Date: January 1, 2024\n\nThis policy describes how we handle personal data in compliance with GDPR requirements.\n\n1. DATA COLLECTION\nWe collect personal information necessary for business operations.\n\n2. GDPR COMPLIANCE\nAll data processing follows General Data Protection Regulation guidelines.\n\n3. USER RIGHTS\nIndividuals have the right to access, rectify, and delete their personal data.\n\n4. VIOLATIONS\nAny violation of this policy may result in disciplinary action and legal consequences.\n\nFor questions, contact: privacy@company.com';
            document.getElementById('inputType').value = 'PDF';
        });
}

/**
 * Display error message
 */
function displayError(message) {
    const container = document.getElementById('resultsContainer');
    container.innerHTML = `
        <div class="alert alert-danger">
            <h6 class="alert-heading">
                <i class="fas fa-exclamation-triangle me-2"></i>Processing Failed
            </h6>
            <p class="mb-0">${escapeHtml(message)}</p>
        </div>
    `;
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert alert at top of page
    const container = document.querySelector('.container-fluid');
    container.insertAdjacentHTML('afterbegin', alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alert = container.querySelector('.alert');
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 5000);
}

/**
 * Utility functions for badges and styling
 */
function getFormatBadge(format) {
    const badges = {
        'Email': 'bg-primary',
        'JSON': 'bg-warning text-dark',
        'PDF': 'bg-danger'
    };
    return `<span class="badge ${badges[format] || 'bg-secondary'}">${format}</span>`;
}

function getIntentBadge(intent) {
    const badges = {
        'RFQ': 'bg-info',
        'Complaint': 'bg-danger', 
        'Invoice': 'bg-success',
        'Regulation': 'bg-warning text-dark',
        'Fraud Risk': 'bg-dark'
    };
    return `<span class="badge ${badges[intent] || 'bg-secondary'}">${intent}</span>`;
}

function getToneClass(tone) {
    const classes = {
        'polite': 'bg-success',
        'escalation': 'bg-warning text-dark',
        'threatening': 'bg-danger',
        'neutral': 'bg-secondary',
        'urgent': 'bg-info'
    };
    return classes[tone] || 'bg-secondary';
}

function getUrgencyClass(urgency) {
    const classes = {
        'high': 'bg-danger',
        'medium': 'bg-warning text-dark',
        'low': 'bg-success'
    };
    return classes[urgency] || 'bg-secondary';
}

function getRiskClass(risk) {
    const classes = {
        'high': 'bg-danger',
        'medium': 'bg-warning text-dark',
        'low': 'bg-success'
    };
    return classes[risk] || 'bg-secondary';
}

function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
