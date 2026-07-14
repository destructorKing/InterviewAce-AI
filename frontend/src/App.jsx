import React, { useState } from 'react';

function App() {
  const [resumeText, setResumeText] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/api/upload-resume', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setResumeText(data.full_text);
      alert("Resume parsed successfully!");
    } catch (err) {
      console.error("Upload error", err);
    }
  };

  const handleGenerate = async () => {
    if (!resumeText || !jobDescription) {
      alert("Please upload a resume and input a target job description first.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/generate-questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume_text: resumeText, job_description: jobDescription }),
      });
      const data = await res.json();
      setQuestions(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif', maxWidth: '800px', margin: '0 auto' }}>
      <h1>InterviewAce AI Copilot</h1>
      
      <div style={{ marginBottom: '1.5rem' }}>
        <label><strong>1. Upload Resume (PDF Only):</strong></label><br />
        <input type="file" accept=".pdf" onChange={handleFileUpload} />
      </div>

      <div style={{ marginBottom: '1.5rem' }}>
        <label><strong>2. Target Job Description:</strong></label><br />
        <textarea 
          rows="5" 
          style={{ width: '100%', marginTop: '0.5rem' }} 
          placeholder="Paste the job requirements here..."
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
        />
      </div>

      <button 
        onClick={handleGenerate} 
        disabled={loading}
        style={{ padding: '0.75rem 1.5rem', background: '#0070f3', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
      >
        {loading ? 'Analyzing with Gemini...' : 'Generate Interview Path'}
      </button>

      <hr style={{ margin: '2rem 0' }} />

      {questions.length > 0 && (
        <div>
          <h2>Your Tailored Interview Questions</h2>
          {questions.map((q) => (
            <div key={q.id} style={{ border: '1px solid #ddd', padding: '1rem', borderRadius: '8px', marginBottom: '1rem', background: '#f9f9f9' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#0070f3', uppercase: 'true' }}>{q.type}</span>
              <p style={{ margin: '0.5rem 0', fontSize: '1.1rem' }}><strong>{q.question}</strong></p>
              <small style={{ color: '#666' }}>💡 <em>Context: {q.context}</em></small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;