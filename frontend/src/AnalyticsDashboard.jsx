import React, { useState, useEffect } from 'react';

export default function AnalyticsDashboard() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/analytics/history')
      .then((res) => res.json())
      .then((data) => {
        setHistory(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching metrics:", err);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Loading performance history...</p>;

  return (
    <div style={{ textAlign: 'left', marginTop: '1rem' }}>
      <h2>Performance Tracking Dashboard</h2>
      <p style={{ color: '#666' }}>Track your interview metrics and preparation consistency over time.</p>
      
      {history.length === 0 ? (
        <div style={{ padding: '2rem', background: '#f9f9f9', borderRadius: '8px', textAlign: 'center', border: '1px dashed #ccc' }}>
          <p style={{ color: '#666', margin: 0 }}>No interview history found yet. Complete a session to see analytics!</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {history.map((session) => (
            <div 
              key={session.session_id} 
              style={{ 
                padding: '1.25rem', 
                border: '1px solid #e2e8f0', 
                borderRadius: '8px', 
                background: '#fff',
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
              }}
            >
              <div>
                <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '1.1rem' }}>📄 {session.filename}</h4>
                <small style={{ color: '#888' }}>Date: {session.date}</small>
                <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: '#4a5568' }}>
                  Progress: <strong>{session.answered_count} / {session.questions_count}</strong> questions evaluated
                </div>
              </div>
              
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.8rem', color: '#718096', fontWeight: 'bold', textTransform: 'uppercase' }}>Avg Score</div>
                <div 
                  style={{ 
                    fontSize: '1.75rem', 
                    fontWeight: 'bold', 
                    color: session.average_score >= 70 ? '#10b981' : session.average_score >= 40 ? '#f59e0b' : '#ef4444' 
                  }}
                >
                  {session.average_score}%
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}