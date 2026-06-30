import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException
from core.pipeline import PipelineRunner

router = APIRouter()

from fastapi.responses import FileResponse

@router.get("/")
def home():
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "index.html")
    return FileResponse(html_path)

from typing import Optional

@router.post("/transform-profile")
async def transform_profile(
    csv_file: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
    config_file: Optional[UploadFile] = File(None)
):
    csv_path = None
    pdf_path = None
    config_path = None
    try:
        os.makedirs("temp_uploads", exist_ok=True)

        csv_path = f"temp_uploads/{uuid.uuid4()}_{csv_file.filename}"
        pdf_path = f"temp_uploads/{uuid.uuid4()}_{pdf_file.filename}"

        with open(csv_path, "wb") as buffer:
            shutil.copyfileobj(csv_file.file, buffer)

        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(pdf_file.file, buffer)

        if config_file:
            config_path = f"temp_uploads/{uuid.uuid4()}_{config_file.filename}"
            with open(config_path, "wb") as buffer:
                shutil.copyfileobj(config_file.file, buffer)

        pipeline = PipelineRunner()
        result = pipeline.run(csv_path, pdf_path, custom_config_path=config_path)

        return {
            "status": "success",
            "data": result
        }

    except __import__('utils.exceptions').exceptions.ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if csv_path and os.path.exists(csv_path):
            os.remove(csv_path)

        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
            
        if config_path and os.path.exists(config_path):
            os.remove(config_path)
