import React, { useState } from 'react';
import QuestionCard from './QuestionCard';
import AnalyticsDashboard from './AnalyticsDashboard'; // Import dashboard layer

function App() {
  const [view, setView] = useState('practice'); // 'practice' or 'analytics'
  const [filename, setFilename] = useState('');
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
      setFilename(data.filename);
      alert("Resume parsed successfully!");
    } catch (err) {
      console.error("Upload error", err);
      alert("Error parsing resume.");
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
        body: JSON.stringify({ 
          filename: filename || "Uploaded_Resume.pdf", 
          resume_text: resumeText, 
          job_description: jobDescription 
        }),
      });
      const data = await res.json();
      setQuestions(data.questions || []);
    } catch (err) {
      console.error(err);
      alert("Failed to generate questions.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
      <h1>InterviewAce AI Copilot</h1>
      
      {/* Navigation Tabs */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginBottom: '2rem' }}>
        <button 
          onClick={() => setView('practice')}
          style={{
            padding: '0.5rem 1.5rem',
            background: view === 'practice' ? '#0070f3' : '#e2e8f0',
            color: view === 'practice' ? '#fff' : '#333',
            border: 'none', borderRadius: '20px', cursor: 'pointer', fontWeight: 'bold'
          }}
        >
          Practice Arena
        </button>
        <button 
          onClick={() => setView('analytics')}
          style={{
            padding: '0.5rem 1.5rem',
            background: view === 'analytics' ? '#0070f3' : '#e2e8f0',
            color: view === 'analytics' ? '#fff' : '#333',
            border: 'none', borderRadius: '20px', cursor: 'pointer', fontWeight: 'bold'
          }}
        >
          Performance History
        </button>
      </div>

      <hr style={{ marginBottom: '2rem', borderColor: '#eaeaea' }} />

      {/* Conditional View Rendering */}
      {view === 'analytics' ? (
        <AnalyticsDashboard />
      ) : (
        <div>
          <p style={{ color: '#666' }}>Upload your resume, paste a target description, and practice your responses.</p>
          
          <div style={{ marginBottom: '1.5rem', textAlign: 'left', background: '#fff', padding: '1rem', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <label><strong>1. Upload Resume (PDF Only):</strong></label><br />
            <input type="file" accept=".pdf" onChange={handleFileUpload} style={{ marginTop: '0.5rem' }} />
            {filename && <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.85rem', color: '#10b981' }}>📄 {filename}</p>}
          </div>

          <div style={{ marginBottom: '1.5rem', textAlign: 'left' }}>
            <label><strong>2. Target Job Description:</strong></label><br />
            <textarea 
              rows="5" 
              style={{ width: '100%', marginTop: '0.5rem', padding: '0.5rem', boxSizing: 'border-box', borderRadius: '4px', border: '1px solid #ccc' }} 
              placeholder="Paste the target job description requirements here..."
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
            />
          </div>

          <button 
            onClick={handleGenerate} 
            disabled={loading}
            style={{ padding: '0.75rem 1.5rem', background: '#0070f3', color: '#fff', border: 'none', borderRadius: '4px', cursor: loading ? 'not-allowed' : 'pointer', fontSize: '1rem' }}
          >
            {loading ? 'Analyzing with Gemini...' : 'Generate Interview Path'}
          </button>

          {questions.length > 0 && (
            <div style={{ marginTop: '2.5rem' }}>
              <h2 style={{ marginBottom: '1.5rem' }}>Your Tailored Interview Questions</h2>
              {questions.map((q) => (
                <QuestionCard key={q.id} q={q} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;