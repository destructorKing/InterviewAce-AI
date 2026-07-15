import os
import json
import time
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from database import init_db, get_db, InterviewSession, QuestionModel

load_dotenv()

app = FastAPI(title="InterviewAce AI Core API")

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

# =====================================================================
#                 PYDANTIC SCHEMAS FOR NATIVE GEMINI SDK
# =====================================================================

class QuestionSchema(BaseModel):
    type: str = Field(description="Must be 'Technical' or 'Behavioral'")
    question: str = Field(description="The core interview question text")
    context: str = Field(description="Subtle context or structural parameters about the question")

class QuestionGenerationList(BaseModel):
    questions: list[QuestionSchema]

class EvaluationSchema(BaseModel):
    score: int = Field(description="Overall performance evaluation score from 0 to 100")
    feedback: list[str] = Field(description="Detailed critique bullet points analyzing the response")
    suggested_improvement: str = Field(description="Refined response alignment model upgrade text")

class ATSAnalysisSchema(BaseModel):
    match_percentage: int
    missing_keywords: list[str]
    formatting_issues: list[str]
    optimization_suggestions: str

# =====================================================================
#                       REQUEST PAYLOAD MODELS
# =====================================================================

class GenerationPayload(BaseModel):
    filename: str
    resume_text: str
    job_description: str

class AnswerSubmissionPayload(BaseModel):
    question_id: int
    user_answer: str

# =====================================================================
#                             API ROUTING
# =====================================================================

@app.get("/")
def read_root():
    return {"status": "InterviewAce AI API active"}

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
    You are an expert technical interviewer. Analyze the following candidate resume text and target job description.
    Candidate Resume: {payload.resume_text}
    Target Job Description: {payload.job_description}
    Generate a list of 5 high-quality interview questions. Include 3 technical questions specifically targeting their technical stack/gaps and 2 behavioral questions.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QuestionGenerationList,
            )
        )
    except APIError as e:
        if e.code == 429:
            # STAGGER 1: Fast retry lane for questions (2 seconds)
            print("[RATE_LIMIT]: 429 caught on question generation. Retrying in 2 seconds...")
            time.sleep(2)
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=QuestionGenerationList,
                    )
                )
            except Exception:
                raise HTTPException(status_code=429, detail="API rate limit ceiling persisted on retry. Please try again shortly.")
        else:
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"[GENERATE_ERROR]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI generation or database sync failure: {str(e)}")

    try:
        validated_data = QuestionGenerationList.model_validate_json(response.text)
        ai_questions = validated_data.questions

        new_session = InterviewSession(
            filename=payload.filename,
            resume_text=payload.resume_text,
            job_description=payload.job_description
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        question_objects = []
        for q in ai_questions:
            db_q = QuestionModel(
                session_id=new_session.id,
                type=q.type,
                question=q.question,
                context=q.context
            )
            db.add(db_q)
            question_objects.append(db_q)
        
        db.commit()

        return {
            "session_id": new_session.id,
            "questions": [{"id": q.id, "type": q.type, "question": q.question, "context": q.context} for q in question_objects]
        }
    except Exception as e:
        print(f"[PARSING_ERROR]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database synchronization error: {str(e)}")

@app.post("/api/evaluate-answer")
def evaluate_answer(payload: AnswerSubmissionPayload, db: Session = Depends(get_db)):
    db_question = db.query(QuestionModel).filter(QuestionModel.id == payload.question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Target question configuration row not located")

    criteria = "accuracy, edge cases, and architectural core patterns" if db_question.type.lower() == "technical" else "STAR methodology format parameters"
    prompt = f"Question Asked: {db_question.question}\nCandidate Response: {payload.user_answer}\nEvaluate performance precisely under: {criteria}."
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EvaluationSchema,
            )
        )
    except APIError as e:
        if e.code == 429:
            print("[RATE_LIMIT]: 429 caught on answer evaluation. Retrying in 3 seconds...")
            time.sleep(3)
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=EvaluationSchema,
                    )
                )
            except Exception:
                raise HTTPException(status_code=429, detail="Evaluation Rate limit reached. Please wait a moment.")
        else:
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"[EVALUATE_ERROR]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Evaluation pipeline runtime failure: {str(e)}")

    try:
        validated_eval = EvaluationSchema.model_validate_json(response.text)
        
        db_question.user_answer = payload.user_answer
        db_question.score = validated_eval.score
        db_question.feedback = json.dumps(validated_eval.feedback) 
        db_question.suggested_improvement = validated_eval.suggested_improvement
        
        db.commit()

        return {
            "score": db_question.score,
            "feedback": validated_eval.feedback,
            "suggested_improvement": db_question.suggested_improvement
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database evaluation update failure: {str(e)}")

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

@app.post("/api/analyze-ats", response_model=ATSAnalysisSchema)
def analyze_ats_compatibility(payload: GenerationPayload):
    prompt = f"""
    Compare the following candidate resume text against the target job description.
    Resume Text:
    {payload.resume_text}
    Target Job Description:
    {payload.job_description}
    Perform a strict compliance and keyword density check.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ATSAnalysisSchema,
            )
        )
    except APIError as e:
        if e.code == 429:
            # STAGGER 2: Delayed retry lane for ATS (5 seconds) to prevent collisions
            print("[RATE_LIMIT]: 429 caught on ATS analysis. Retrying in 5 seconds...")
            time.sleep(5)
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ATSAnalysisSchema,
                    )
                )
            except Exception:
                raise HTTPException(status_code=429, detail="ATS Engine Rate limit reached. Please retry shortly.")
        else:
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"[ATS_ERROR]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ATS pipeline engine execution breakdown: {str(e)}")

    return ATSAnalysisSchema.model_validate_json(response.text)