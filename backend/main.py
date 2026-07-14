import os
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_load

load_dotenv()

app = FastAPI(title="InterviewAce AI API")

# Allow your React frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the official Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.get("/")
def read_root():
    return {"status": "InterviewAce AI API is running"}

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    try:
        # Read file into memory
        contents = await file.read()
        
        # Open PDF with PyMuPDF
        doc = fitz.open(stream=contents, filetype="pdf")
        extracted_text = ""
        for page in doc:
            extracted_text += page.get_text()
            
        doc.close()
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
            
        return {"filename": file.filename, "text_preview": extracted_text[:500], "full_text": extracted_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing PDF: {str(e)}")

class JobDescriptionPayload(BaseModel):
    resume_text: str
    job_description: str

@app.post("/api/generate-questions")
def generate_questions(payload: JobDescriptionPayload):
    prompt = f"""
    You are an expert technical interviewer and ATS system analyzer.
    Analyze the following candidate resume text and target job description.
    
    Candidate Resume:
    {payload.resume_text}
    
    Target Job Description:
    {payload.job_description}
    
    Generate a list of 5 high-quality interview questions. 
    Include 3 technical questions specifically targeting their technical stack/gaps and 2 behavioral questions.
    """
    
    try:
        # Requesting a structured JSON output matching a specific Pydantic model structure
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "INTEGER"},
                            "type": {"type": "STRING"}, # "Technical" or "Behavioral"
                            "question": {"type": "STRING"},
                            "context": {"type": "STRING"} # Why this question is being asked based on the resume
                        },
                        "required": ["id", "type", "question", "context"]
                    }
                }
            )
        )
        import json
        return json.loads(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")