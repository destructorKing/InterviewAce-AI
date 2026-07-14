import os
import json
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Import our modular database layer
from database import init_db, get_db, InterviewSession, QuestionModel

load_dotenv()

app = FastAPI(title="InterviewAce AI API with DB Layer")

# Initialize database on app startup
@app.on_event("startup")
def startup_event():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class GenerationPayload(BaseModel):
    filename: str
    resume_text: str
    job_description: str

class AnswerSubmissionPayload(BaseModel):
    question_id: int
    user_answer: str

@app.get("/")
def read_root():
    return {"status": "InterviewAce AI API running with DB connectivity"}

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    try:
        contents = await file.read()
        doc = fitz.open(stream=contents, filetype="pdf")
        extracted_text = "".join([page.get_text() for page in doc])
        doc.close()
        
        return {"filename": file.filename, "full_text": extracted_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing PDF: {str(e)}")

@app.post("/api/generate-questions")
def generate_questions(payload: GenerationPayload, db: Session = Depends(get_db)):
    prompt = f"""
    You are an expert interviewer. Analyze the candidate resume and target description.
    Resume: {payload.resume_text}
    Target Job: {payload.job_description}
    Generate 5 custom interview questions (3 Technical, 2 Behavioral).
    """
    try:
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
                            "type": {"type": "STRING"},
                            "question": {"type": "STRING"},
                            "context": {"type": "STRING"}
                        },
                        "required": ["type", "question", "context"]
                    }
                }
            )
        )
        ai_questions = json.loads(response.text)

        # 1. Store the overarching session meta details
        new_session = InterviewSession(
            filename=payload.filename,
            resume_text=payload.resume_text,
            job_description=payload.job_description
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # 2. Add each individual generated structural card row
        question_objects = []
        for q in ai_questions:
            db_q = QuestionModel(
                session_id=new_session.id,
                type=q["type"],
                question=q["question"],
                context=q["context"]
            )
            db.add(db_q)
            question_objects.append(db_q)
        
        db.commit()

        # Format output payload for modern frontend processing loops
        return {
            "session_id": new_session.id,
            "questions": [{"id": q.id, "type": q.type, "question": q.question, "context": q.context} for q in question_objects]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation or save failure: {str(e)}")

@app.post("/api/evaluate-answer")
def evaluate_answer(payload: AnswerSubmissionPayload, db: Session = Depends(get_db)):
    # Pull the targeted question record out dynamically
    db_question = db.query(QuestionModel).filter(QuestionModel.id == payload.question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Question entry not located in tracking schema")

    criteria = "technical correctness and optimization metrics" if db_question.type == "Technical" else "STAR method layout flow framework styles"
    prompt = f"Question: {db_question.question}\nAnswer: {payload.user_answer}\nEvaluate performance based on {criteria}."
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "score": {"type": "INTEGER"},
                        "feedback": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "suggested_improvement": {"type": "STRING"}
                    },
                    "required": ["score", "feedback", "suggested_improvement"]
                }
            )
        )
        evaluation_data = json.loads(response.text)

        # Update historical database records with persistent evaluation results
        db_question.user_answer = payload.user_answer
        db_question.score = evaluation_data["score"]
        db_question.feedback = json.dumps(evaluation_data["feedback"]) # Serialize string arrays cleanly
        db_question.suggested_improvement = evaluation_data["suggested_improvement"]
        
        db.commit()

        return {
            "score": db_question.score,
            "feedback": evaluation_data["feedback"],
            "suggested_improvement": db_question.suggested_improvement
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation execution failed: {str(e)}")

# History Analytics Retrieval Endpoint
@app.get("/api/analytics/history")
def get_historical_perf_metrics(db: Session = Depends(get_db)):
    sessions = db.query(InterviewSession).all()
    history_report = []
    
    for s in sessions:
        scored_qs = [q.score for q in s.questions if q.score is not None]
        avg_score = sum(scored_qs) / len(scored_qs) if scored_qs else 0
        
        history_report.append({
            "session_id": s.id,
            "filename": s.filename,
            "date": s.created_at.strftime("%Y-%m-%d %H:%M"),
            "questions_count": len(s.questions),
            "answered_count": len(scored_qs),
            "average_score": round(avg_score, 1)
        })
    return history_report