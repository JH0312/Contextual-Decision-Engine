"""
Shared Memory Store - SQLite-based storage for all agent data
Stores input metadata, extracted fields, chained actions, and agent decision traces
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading

class MemoryStore:
    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self.lock = threading.Lock()

    def init_db(self):
        """Initialize the database schema"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Table for input metadata and classifications
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS classifications (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    format TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    content_preview TEXT,
                    confidence_score REAL,
                    metadata TEXT
                )
            ''')
            
            # Table for agent processing results
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_results (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    classification_id TEXT,
                    result_data TEXT NOT NULL,
                    processing_duration REAL,
                    FOREIGN KEY (classification_id) REFERENCES classifications (id)
                )
            ''')
            
            # Table for action router results
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action_results (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    agent_result_id TEXT,
                    actions_triggered TEXT NOT NULL,
                    success_count INTEGER,
                    failure_count INTEGER,
                    FOREIGN KEY (agent_result_id) REFERENCES agent_results (id)
                )
            ''')
            
            # Table for complete processing traces
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_traces (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    classification_id TEXT,
                    agent_result_id TEXT,
                    action_result_id TEXT,
                    status TEXT NOT NULL,
                    total_processing_time REAL,
                    FOREIGN KEY (classification_id) REFERENCES classifications (id),
                    FOREIGN KEY (agent_result_id) REFERENCES agent_results (id),
                    FOREIGN KEY (action_result_id) REFERENCES action_results (id)
                )
            ''')
            
            # Table for decision audit logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS decision_logs (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    component TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    decision_data TEXT NOT NULL,
                    reasoning TEXT,
                    trace_id TEXT
                )
            ''')
            
            conn.commit()
            conn.close()

    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat()

    def store_classification(self, classification_data: Dict[str, Any]) -> str:
        """Store classification result and return ID"""
        with self.lock:
            classification_id = str(uuid.uuid4())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO classifications 
                (id, timestamp, format, intent, content_preview, confidence_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                classification_id,
                self.get_current_timestamp(),
                classification_data.get('format', 'Unknown'),
                classification_data.get('intent', 'Unknown'),
                classification_data.get('content_preview', ''),
                classification_data.get('confidence_score', 0.0),
                json.dumps(classification_data)
            ))
            
            conn.commit()
            conn.close()
            
            return classification_id

    def store_agent_result(self, agent_type: str, result_data: Dict[str, Any], classification_id: str = None) -> str:
        """Store agent processing result and return ID"""
        with self.lock:
            result_id = str(uuid.uuid4())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO agent_results 
                (id, timestamp, agent_type, classification_id, result_data, processing_duration)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                result_id,
                self.get_current_timestamp(),
                agent_type,
                classification_id,
                json.dumps(result_data),
                result_data.get('processing_duration', 0.0)
            ))
            
            conn.commit()
            conn.close()
            
            return result_id

    def store_action_result(self, action_data: Dict[str, Any], agent_result_id: str = None) -> str:
        """Store action router result and return ID"""
        with self.lock:
            action_id = str(uuid.uuid4())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            actions_triggered = action_data.get('actions_triggered', [])
            success_count = sum(1 for action in actions_triggered if action.get('success', False))
            failure_count = len(actions_triggered) - success_count
            
            cursor.execute('''
                INSERT INTO action_results 
                (id, timestamp, agent_result_id, actions_triggered, success_count, failure_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                action_id,
                self.get_current_timestamp(),
                agent_result_id,
                json.dumps(actions_triggered),
                success_count,
                failure_count
            ))
            
            conn.commit()
            conn.close()
            
            return action_id

    def log_complete_trace(self, classification: Dict[str, Any], agent_result: Dict[str, Any], action_result: Dict[str, Any]) -> str:
        """Log complete processing trace"""
        with self.lock:
            trace_id = str(uuid.uuid4())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get the latest IDs (in a real implementation, these would be passed)
            cursor.execute('SELECT id FROM classifications ORDER BY timestamp DESC LIMIT 1')
            classification_id = cursor.fetchone()
            classification_id = classification_id[0] if classification_id else None
            
            cursor.execute('SELECT id FROM agent_results ORDER BY timestamp DESC LIMIT 1')
            agent_result_id = cursor.fetchone()
            agent_result_id = agent_result_id[0] if agent_result_id else None
            
            cursor.execute('SELECT id FROM action_results ORDER BY timestamp DESC LIMIT 1')
            action_result_id = cursor.fetchone()
            action_result_id = action_result_id[0] if action_result_id else None
            
            cursor.execute('''
                INSERT INTO processing_traces 
                (id, timestamp, classification_id, agent_result_id, action_result_id, status, total_processing_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                trace_id,
                self.get_current_timestamp(),
                classification_id,
                agent_result_id,
                action_result_id,
                'completed',
                0.0  # Would calculate actual processing time
            ))
            
            conn.commit()
            conn.close()
            
            return trace_id

    def log_decision(self, component: str, decision_type: str, decision_data: Dict[str, Any], reasoning: str = "", trace_id: str = None) -> str:
        """Log agent decision for audit purposes"""
        with self.lock:
            decision_id = str(uuid.uuid4())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO decision_logs 
                (id, timestamp, component, decision_type, decision_data, reasoning, trace_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                decision_id,
                self.get_current_timestamp(),
                component,
                decision_type,
                json.dumps(decision_data),
                reasoning,
                trace_id
            ))
            
            conn.commit()
            conn.close()
            
            return decision_id

    def get_classification(self, classification_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve classification by ID"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM classifications WHERE id = ?', (classification_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'timestamp': row[1],
                    'format': row[2],
                    'intent': row[3],
                    'content_preview': row[4],
                    'confidence_score': row[5],
                    'metadata': json.loads(row[6]) if row[6] else {}
                }
            return None

    def get_agent_results(self, agent_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve agent results, optionally filtered by agent type"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if agent_type:
                cursor.execute('''
                    SELECT * FROM agent_results 
                    WHERE agent_type = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (agent_type, limit))
            else:
                cursor.execute('''
                    SELECT * FROM agent_results 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                results.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'agent_type': row[2],
                    'classification_id': row[3],
                    'result_data': json.loads(row[4]) if row[4] else {},
                    'processing_duration': row[5]
                })
            
            return results

    def get_all_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all processing traces with joined data"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    t.id, t.timestamp, t.status, t.total_processing_time,
                    c.format, c.intent, c.content_preview,
                    a.agent_type, a.result_data,
                    ac.actions_triggered, ac.success_count, ac.failure_count
                FROM processing_traces t
                LEFT JOIN classifications c ON t.classification_id = c.id
                LEFT JOIN agent_results a ON t.agent_result_id = a.id  
                LEFT JOIN action_results ac ON t.action_result_id = ac.id
                ORDER BY t.timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            traces = []
            for row in rows:
                traces.append({
                    'trace_id': row[0],
                    'timestamp': row[1],
                    'status': row[2],
                    'total_processing_time': row[3],
                    'classification': {
                        'format': row[4],
                        'intent': row[5],
                        'content_preview': row[6]
                    },
                    'agent_result': {
                        'agent_type': row[7],
                        'result_data': json.loads(row[8]) if row[8] else {}
                    },
                    'action_result': {
                        'actions_triggered': json.loads(row[9]) if row[9] else [],
                        'success_count': row[10],
                        'failure_count': row[11]
                    }
                })
            
            return traces

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get specific trace by ID"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    t.id, t.timestamp, t.status, t.total_processing_time,
                    c.format, c.intent, c.content_preview, c.metadata,
                    a.agent_type, a.result_data,
                    ac.actions_triggered, ac.success_count, ac.failure_count
                FROM processing_traces t
                LEFT JOIN classifications c ON t.classification_id = c.id
                LEFT JOIN agent_results a ON t.agent_result_id = a.id  
                LEFT JOIN action_results ac ON t.action_result_id = ac.id
                WHERE t.id = ?
            ''', (trace_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'trace_id': row[0],
                    'timestamp': row[1],
                    'status': row[2],
                    'total_processing_time': row[3],
                    'classification': {
                        'format': row[4],
                        'intent': row[5],
                        'content_preview': row[6],
                        'metadata': json.loads(row[7]) if row[7] else {}
                    },
                    'agent_result': {
                        'agent_type': row[8],
                        'result_data': json.loads(row[9]) if row[9] else {}
                    },
                    'action_result': {
                        'actions_triggered': json.loads(row[10]) if row[10] else [],
                        'success_count': row[11],
                        'failure_count': row[12]
                    }
                }
            return None

    def get_decision_logs(self, component: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get decision audit logs"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if component:
                cursor.execute('''
                    SELECT * FROM decision_logs 
                    WHERE component = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (component, limit))
            else:
                cursor.execute('''
                    SELECT * FROM decision_logs 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            logs = []
            for row in rows:
                logs.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'component': row[2],
                    'decision_type': row[3],
                    'decision_data': json.loads(row[4]) if row[4] else {},
                    'reasoning': row[5],
                    'trace_id': row[6]
                })
            
            return logs
