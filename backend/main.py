from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import base64
import os
from io import BytesIO
from PIL import Image
import logging
from typing import Optional
import requests
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gemma3 Vision API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama API configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "gemma3:latest")

class TextRequest(BaseModel):
    prompt: str
    stream: bool = False

class VisionRequest(BaseModel):
    prompt: str
    image_url: Optional[str] = None
    stream: bool = False

class ChatResponse(BaseModel):
    response: str
    success: bool
    message: str = "Response generated successfully"

def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

async def download_image_from_url(url: str) -> bytes:
    """Download image from URL"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Verify it's an image
        img = Image.open(BytesIO(response.content))
        img.verify()
        
        return response.content
    except Exception as e:
        logger.error(f"Error downloading image from URL: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to download image from URL: {str(e)}")

def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64"""
    return base64.b64encode(image_bytes).decode('utf-8')

async def call_ollama_vision(prompt: str, image_base64: str) -> str:
    """Call Ollama API for vision tasks"""
    try:
        logger.info(f"Attempting to connect to Ollama at {OLLAMA_BASE_URL} with model {MODEL_NAME}")
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False
                }
            )
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "")
            if not response_text:
                logger.warning("Ollama returned empty response")
            return response_text
    except httpx.TimeoutException:
        logger.error(f"Request to Ollama timed out after 120 seconds")
        raise HTTPException(
            status_code=504, 
            detail=f"Request to Ollama timed out. Please check if Ollama is running at {OLLAMA_BASE_URL} and try again."
        )
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to Ollama at {OLLAMA_BASE_URL}: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail=f"Failed to connect to Ollama at {OLLAMA_BASE_URL}. Please ensure Ollama is running and accessible. Error: {str(e)}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error when calling Ollama: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail=f"Failed to connect to Ollama: {str(e)}. Please check if Ollama is running at {OLLAMA_BASE_URL}"
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama returned HTTP error {e.response.status_code}: {e.response.text}")
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned error {e.response.status_code}: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Error calling Ollama API: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calling Ollama: {str(e)}")

async def call_ollama_text(prompt: str) -> str:
    """Call Ollama API for text-only tasks"""
    try:
        logger.info(f"Attempting to connect to Ollama at {OLLAMA_BASE_URL} with model {MODEL_NAME}")
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            result = response.json()
            response_text = result.get("response", "")
            if not response_text:
                logger.warning("Ollama returned empty response")
            return response_text
    except httpx.TimeoutException:
        logger.error(f"Request to Ollama timed out after 120 seconds")
        raise HTTPException(
            status_code=504, 
            detail=f"Request to Ollama timed out. Please check if Ollama is running at {OLLAMA_BASE_URL} and try again."
        )
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to Ollama at {OLLAMA_BASE_URL}: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail=f"Failed to connect to Ollama at {OLLAMA_BASE_URL}. Please ensure Ollama is running and accessible. Error: {str(e)}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error when calling Ollama: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail=f"Failed to connect to Ollama: {str(e)}. Please check if Ollama is running at {OLLAMA_BASE_URL}"
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama returned HTTP error {e.response.status_code}: {e.response.text}")
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned error {e.response.status_code}: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Error calling Ollama API: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calling Ollama: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    # Check if Ollama is accessible
    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                ollama_status = "connected"
            else:
                ollama_status = "error"
    except:
        ollama_status = "disconnected"
    
    return {
        "status": "healthy",
        "message": "Gemma3 Vision API is running",
        "ollama_status": ollama_status,
        "ollama_url": OLLAMA_BASE_URL,
        "model": MODEL_NAME
    }

@app.get("/health")
async def health():
    """Health check endpoint with Ollama connectivity check"""
    ollama_status = "disconnected"
    ollama_error = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                ollama_status = "connected"
                # Check if model is available
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if MODEL_NAME not in model_names:
                    ollama_status = "model_not_found"
                    ollama_error = f"Model '{MODEL_NAME}' not found. Available models: {', '.join(model_names[:5])}"
            else:
                ollama_status = "error"
                ollama_error = f"Ollama returned status {response.status_code}"
    except httpx.ConnectError as e:
        ollama_status = "disconnected"
        ollama_error = f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. Please ensure Ollama is running."
    except Exception as e:
        ollama_status = "error"
        ollama_error = str(e)
    
    return {
        "status": "ok",
        "ollama_status": ollama_status,
        "ollama_url": OLLAMA_BASE_URL,
        "model": MODEL_NAME,
        "ollama_error": ollama_error
    }

@app.post("/analyze", response_model=ChatResponse)
async def analyze_image(
    prompt: str = Form(...),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None)
):
    """Analyze an image with a text prompt using Ollama"""
    try:
        # Normalize prompt - handle empty strings and whitespace
        prompt = prompt.strip() if prompt else ""
        
        # Determine if we have an image (upload or URL)
        has_image = image is not None or (image_url and image_url.strip())
        
        # If no prompt provided but we have an image, use default prompt
        if not prompt and has_image:
            prompt = "What is in this image? Describe it in detail."
        elif not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required when no image is provided")
        
        if has_image:
            # Handle image from upload
            if image:
                try:
                    image_bytes = await image.read()
                    if not image_bytes:
                        raise HTTPException(status_code=400, detail="Uploaded image file is empty")
                    image_base64 = encode_image_to_base64(image_bytes)
                    logger.info(f"Processing uploaded image for vision analysis (size: {len(image_bytes)} bytes)")
                except Exception as e:
                    logger.error(f"Error reading uploaded image: {str(e)}")
                    raise HTTPException(status_code=400, detail=f"Error processing uploaded image: {str(e)}")
            # Handle image from URL
            elif image_url and image_url.strip():
                image_url = image_url.strip()
                if not is_valid_url(image_url):
                    raise HTTPException(status_code=400, detail=f"Invalid image URL: {image_url}")
                try:
                    image_bytes = await download_image_from_url(image_url)
                    image_base64 = encode_image_to_base64(image_bytes)
                    logger.info(f"Processing image from URL for vision analysis: {image_url[:50]}...")
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Error processing image URL: {str(e)}")
                    raise HTTPException(status_code=400, detail=f"Error processing image URL: {str(e)}")
            else:
                raise HTTPException(status_code=400, detail="Either image file or image_url must be provided")
            
            # Call Ollama vision API
            logger.info(f"Calling Ollama vision API with prompt: {prompt[:100]}...")
            response_text = await call_ollama_vision(prompt, image_base64)
        else:
            # Text-only query
            logger.info(f"Processing text-only query: {prompt[:100]}...")
            response_text = await call_ollama_text(prompt)
        
        return ChatResponse(
            response=response_text,
            success=True,
            message="Analysis completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: TextRequest):
    """Text-only chat with Ollama"""
    try:
        if not request.prompt or not request.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        logger.info("Processing text-only chat request")
        response_text = await call_ollama_text(request.prompt)
        
        return ChatResponse(
            response=response_text,
            success=True,
            message="Response generated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
