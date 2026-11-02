import logging
import os
import secrets
import io
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import cv2
import numpy as np
from PIL import Image, ImageOps
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from jose import jwt

# --------------------
# Environment
# --------------------
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in environment/.env")

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# --------------------
# Logging Setup
# --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------
# Database
# --------------------
from app.mongodb.connect import connectdb

db = connectdb()
signup_collection = db["signup"]
profile_collection = db["user-profile"]
product_collection = db["products_for_sale"]
lost_and_found_collection = db["lost_and_found"]
lost_and_found_comment_collection = db["lost_and_found_comment"]
refresh_token_collection = db["refresh_tokens"]

# --------------------
# Email Service
# --------------------
from app.services.email_service import send_email

# --------------------
# JWT Helpers
# --------------------
def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)

# --------------------
# Lifespan
# --------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(refresh_token_collection.create_index, "token", unique=True)
    await run_in_threadpool(
        refresh_token_collection.create_index,
        "expires_at",
        expireAfterSeconds=0,
    )
    print("Server started successfully")
    yield

# --------------------
# App Initialization
# --------------------
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://studybazar.vercel.app"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# --------------------
# Moderation Config & Models
# --------------------
NSFW_THRESHOLD = 0.50
PERSON_THRESHOLD = 0.35
TOXICITY_THRESHOLD = 0.75
OCR_MIN_CONF = 0.50
BLOCK_PEOPLE = True  # ✅ Block all humans (faces + bodies)

EXPLICIT_CLASSES = {
    "FEMALE_BREAST_EXPOSED", "FEMALE_GENITALIA_EXPOSED", "MALE_GENITALIA_EXPOSED",
    "MALE_BREAST_EXPOSED", "BUTTOCKS_EXPOSED", "ANUS_EXPOSED",
}

PERSON_CLASSES = EXPLICIT_CLASSES | {
    "FACE_FEMALE", "FACE_MALE", "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED", "FEMALE_GENITALIA_COVERED", "ARMPITS_EXPOSED", "ARMPITS_COVERED",
    "BELLY_EXPOSED", "BELLY_COVERED",
}

_nude = None
_ocr = None
_toxic_prob = None

try:
    logger.info("⏳ Loading Moderation models...")
    
    from nudenet import NudeDetector
    _nude = NudeDetector()
    
    from rapidocr_onnxruntime import RapidOCR
    _ocr = RapidOCR()
    
    from profanity_check import predict_prob
    _toxic_prob = predict_prob
    
    logger.info("✅ NudeNet, RapidOCR, and alt-profanity-check loaded.")
except Exception as e:
    logger.error(f"❌ Failed to load moderation models: {e}")
    logger.warning("⚠️ Moderation endpoints will not work.")

def _is_meaningful_text(text: str) -> bool:
    if not text or len(text.strip()) < 3:
        return False
    if not re.findall(r"[A-Za-z]{3,}", text):
        return False
    letters = sum(c.isalpha() for c in text)
    return letters / max(len(text.replace(" ", "")), 1) >= 0.5

# --------------------
# Base Routes
# --------------------
@app.get("/")
def start_server():
    return {"message": "Server is running successfully"}


@app.post("/moderate-image")
async def moderate_image(
    file: UploadFile = File(...),
    user_email: str = Form(None),
    user_name: str = Form("User"),
):
    """
    Full moderation pipeline:
    1. Nudity check
    2. Human detection (faces + bodies)
    3. OCR text extraction
    4. Text toxicity check
    """
    if not _nude or not _ocr or not _toxic_prob:
        raise HTTPException(status_code=503, detail="Moderation service is currently unavailable.")

    # 1. Read image
    try:
        contents = await file.read()
        img = Image.open(io.BytesIO(contents)).convert("RGB")
        img = ImageOps.exif_transpose(img) # Fix phone rotation
        img_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR) # Convert to BGR for NudeNet/OCR
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")

    reasons = []

    # 2. Nudity & Person Detection
    try:
        dets = _nude.detect(img_np)
    except Exception as e:
        logger.error(f"NudeNet failed: {e}")
        dets = []

    nsfw_score = max([d["score"] for d in dets if d["class"] in EXPLICIT_CLASSES], default=0.0)
    person_score = max([d["score"] for d in dets if d["class"] in PERSON_CLASSES], default=0.0)

    if nsfw_score >= NSFW_THRESHOLD:
        reasons.append(f"Explicit content ({nsfw_score:.2f})")
        await send_legal_warning_email(user_email, user_name, "Explicit/NSFW Image")
    elif BLOCK_PEOPLE and person_score >= PERSON_THRESHOLD:
        reasons.append(f"Human detected ({person_score:.2f})")
        await send_legal_warning_email(user_email, user_name, "Human in image (Policy Violation)")

    # If flagged as NSFW/Person, block immediately
    if reasons:
        logger.warning(f"🚫 Blocked image from {user_email} — {reasons}")
        raise HTTPException(
            status_code=422,
            detail={
                "status": "blocked",
                "reason": "Image contains prohibited content.",
                "flags": reasons
            }
        )

    # 3. OCR
    lines = []
    try:
        result, _ = _ocr(img_np)
        if result:
            for item in result:
                if len(item) >= 3 and float(item[2]) >= OCR_MIN_CONF:
                    lines.append(str(item[1]))
    except Exception as e:
        logger.error(f"OCR failed: {e}")

    extracted_text = " ".join(lines).strip()
    logger.info(f"📄 Extracted text: '{extracted_text}'")

    if not extracted_text:
        return {"status": "safe", "reason": "No text detected", "extracted_text": ""}

    # 4. Toxicity Check
    toxic_score = 0.0
    candidates = [t for t in lines + [extracted_text] if _is_meaningful_text(t)]
    
    if candidates:
        toxic_score = float(max(_toxic_prob(candidates)))
        logger.info(f"☣️ Toxic score: {toxic_score:.2f}")

        if toxic_score >= TOXICITY_THRESHOLD:
            logger.warning(f"🚫 Blocked toxic text from {user_email}")
            await send_legal_warning_email(user_email, user_name, "Toxic/Abusive Text")
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "blocked",
                    "reason": "Image contains toxic text that violates our community guidelines.",
                    "flag": "toxic_text",
                    "score": round(toxic_score, 2),
                }
            )

    return {
        "status": "safe",
        "extracted_text": extracted_text,
        "toxic_score": round(toxic_score, 2),
        "nsfw_score": round(nsfw_score, 2),
        "person_score": round(person_score, 2)
    }


# --------------------
# Helper: Send Legal Warning Email
# --------------------
async def send_legal_warning_email(email: str, name: str, violation_type: str):
    if not email:
        return
        
    subject = "⚠️ OFFICIAL WARNING: Account Violation & Potential Legal Action"
    
    body = f"""
    <div style="font-family: sans-serif; padding: 20px; max-width: 600px; border: 2px solid #FF3B30; border-radius: 8px;">
        <h2 style="color: #FF3B30;">OFFICIAL WARNING</h2>
        <p>Dear <strong>{name}</strong>,</p>
        
        <p>Our automated moderation system detected an attempt to upload content that violates our community guidelines.</p>
        
        <p><strong>Violation Type:</strong> {violation_type}<br/>
        <strong>Date:</strong> {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC</p>
        
        <p>Your upload was <strong>immediately blocked</strong> and was not published on the platform.</p>
        
        <h3 style="color: #d32f2f;">Legal Notice</h3>
        <p>Please be advised that uploading obscene, abusive, or illegal content may constitute a criminal offense under the following laws of India:</p>
        <ul>
            <li><strong>Section 66E of the Information Technology Act, 2000:</strong> Punishment for violation of privacy.</li>
            <li><strong>Section 67 of the Information Technology Act, 2000:</strong> Punishment for publishing or transmitting obscene material in electronic form.</li>
            <li><strong>Section 354A of the Indian Penal Code (IPC):</strong> Sexual harassment.</li>
            <li><strong>Section 509 of the IPC:</strong> Word, gesture or act intended to insult the modesty of a woman.</li>
        </ul>
        <p>We retain the right to share your IP address, account details, and the attempted content with law enforcement authorities if required.</p>
        
        <h3 style="color: #d32f2f;">Consequences</h3>
        <p><strong>This is your final warning.</strong> Any further attempts to upload prohibited content will result in the immediate and permanent deletion of your account.</p>
        
        <p>If you believe this was a system error, please contact our support team immediately.</p>
        
        <br/>
        <p>Regards,<br/>
        <strong>The StudyBazaar Trust & Safety Team</strong></p>
    </div>
    """
    
    try:
        await send_email(subject, [email], body)
        logger.info(f"📧 Legal warning email sent to {email}")
    except Exception as e:
        logger.error(f"❌ Failed to send warning email: {e}")


# --------------------
# Test Route
# --------------------
@app.get("/products-test")
async def test_get_products():
    products = await run_in_threadpool(
        lambda: list(product_collection.find({"is_active": True}).sort("created_at", -1).limit(20))
    )
    for p in products:
        p["_id"] = str(p["_id"])
        if "seller_id" in p:
            p["seller_id"] = str(p["seller_id"])
    return {"status": "ok", "data": {"products": products}}

# --------------------
# Routers
# --------------------
from app.routers import auth, profile, follower, products, lost_and_found, chat
from app.socket_manager import socket_app

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(follower.router)
app.include_router(products.router)
app.include_router(lost_and_found.router)
app.include_router(chat.router)

app.mount("/socket.io", socket_app)