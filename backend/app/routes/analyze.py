from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import Analysis
from ..services.parser import analyze_text
from ..services.recommender import make_recommendations


router = APIRouter(prefix="/api", tags=["analyze"])

class AnalyzeRequests(BaseModel):
    source: str= Field(default="paste", examples=["paste"])
    text: str= Field(..., min_length=1)


class LineResult(BaseModel):
    line: str
    serverity: str
    label: str
    confidence: float


class AnalyzeResponse(BaseModel):
    analyze_id: str
    summary: Dict[str,Any]
    top_patterns: List[Dict[str, Any]]
    recommendations: List[str]
    results_preview: List[LineResult]


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequests, db: Session=Depends(get_db)) -> Dict[str, Any]: 
    analyze_id = uuid.uuid4().hex[:8]

    payload = analyze_text(req.text)

    # Build recommendations based on top labels
    top_labels = [x ["label"] for x in payload["summary"]["top_labels"][:2]]
    payload["recommendations"] = make_recommendations(top_labels)

    response: Dict[str,Any] = {"analysis_id": analyze_id, **payload}

    #save to DB
    record = Analysis(
        analyze_id= analyze_id,
        source=req.source,
        total_lines=int(payload["summary"]["total_lines"]),
        error_lines=int(payload["summary"]["error_lines"]),
        top_label=(payload["summary"]["top_labels"][0]["label"] if payload["summary"]["top_labels"] else "unknown"),
        payload_json=json.dumps(response),
    )

    db.add(record)
    db.commit()

    return response


@router.post("/analyze/upload", response_model=AnalyzeResponse)
async def analyze_upload(
    file: UploadFile = File(...),
    source: str = Form("upload"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if not file.  filename:
        raise HTTPException(status_code=400, detail="Missing filename.")
    
    raw= await file.read()
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to decode file as UTF-8 text.")
    

    analyze_id=uuid.uuid4().hex[:8]
    payload = analyze_text(text)

    top_labels = [x["label"] for x in payload["summary"]["top_labels"][:2]]
    payload["recommendations"] = make_recommendations(top_labels)

    response: Dict[str, Any] = {"anaysis_id" : analyze_id, **payload}

    record = Analysis(
        analyze_id = analyze_id,
        source= source,
        total_lines=int(payload["summary"]["total_lines"]),
        error_lines=int(payload["summary"]["error_lines"]),
        top_label=(payload["summary"]["top_labels"][0] if payload["summary"]["top_labels"] else "unknown"),
        payload_json=json.dumps(response),
    )

    db.add(record)
    db.commit()

    return response




