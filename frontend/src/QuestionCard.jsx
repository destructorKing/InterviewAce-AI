import React, { useState } from 'react';

export default function QuestionCard({ q }) {
  const [answer, setAnswer] = useState('');
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);

  const submitAnswer = async () => {
    if (!answer.trim()) return alert("Please type an answer first.");
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/evaluate-answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: q.id,  // <-- CHANGED: Pass the database integer ID
          user_answer: answer // <-- Pass the typed response string
        }),
      });
      
      if (!res.ok) throw new Error("Failed to evaluate answer");
      
      const data = await res.json();
      setEvaluation(data);
    } catch (err) {
      console.error(err);
      alert("Error getting evaluation. Check if your backend server is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ border: '1px solid #ddd', padding: '1.5rem', borderRadius: '8px', marginBottom: '1.5rem', background: '#f9f9f9', textAlign: 'left' }}>
      <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#0070f3', textTransform: 'uppercase' }}>{q.type}</span>
      <p style={{ margin: '0.5rem 0', fontSize: '1.1rem' }}><strong>{q.question}</strong></p>
      <small style={{ color: '#666', display: 'block', marginBottom: '1rem' }}>💡 Context: {q.context}</small>
      
      {!evaluation ? (
        <div>
          <textarea
            rows="4"
            style={{ width: '100%', padding: '0.5rem', boxSizing: 'border-box', borderRadius: '4px', border: '1px solid #ccc' }}
            placeholder={q.type === 'Technical' ? "Write your technical explanation or pseudo-code..." : "Use the STAR method to describe your experience..."}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
          />
          <button 
            onClick={submitAnswer} 
            disabled={loading}
            style={{ marginTop: '0.5rem', padding: '0.5rem 1rem', background: '#10b981', color: '#fff', border: 'none', borderRadius: '4px', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}
          >
            {loading ? 'Evaluating performance...' : 'Submit Answer'}
          </button>
        </div>
      ) : (
        <div style={{ marginTop: '1rem', borderTop: '2px solid #eee', paddingTop: '1rem' }}>
          <h3 style={{ margin: '0 0 0.5rem 0' }}>Performance Metrics</h3>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: evaluation.score >= 70 ? '#10b981' : '#f59e0b', marginBottom: '1rem' }}>
            Score: {evaluation.score}/100
          </div>
          
          <h4>Constructive Feedback:</h4>
          <ul style={{ paddingLeft: '20px' }}>
            {evaluation.feedback.map((item, idx) => (
              <li key={idx} style={{ marginBottom: '0.25rem' }}>{item}</li>
            ))}
          </ul>

          <div style={{ background: '#eff6ff', padding: '1rem', borderRadius: '4px', marginTop: '1rem', borderLeft: '4px solid #3b82f6' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: '#1e40af' }}>💡 Suggested Response Upgrade:</h4>
            <p style={{ fontSize: '0.95rem', color: '#1e3a8a', lineHeight: '1.4', margin: 0 }}>{evaluation.suggested_improvement}</p>
          </div>
        </div>
      )}
    </div>
  );
}