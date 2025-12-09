# server.py
import os
import json
import logging
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from urllib.parse import urlparse
from io import BytesIO
from PIL import Image

import httpx

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gemma3-server")

# App
app = FastAPI(title="Gemma3 Vision API", version="1.0.0")

# CORS - allow your React dev origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama config
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "gemma3:latest")

# Pydantic models
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

# Utilities
def is_valid_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return bool(p.scheme and p.netloc)
    except Exception:
        return False

async def download_image_from_url(url: str) -> bytes:
    """Async download image and verify using PIL."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            content = r.content
            img = Image.open(BytesIO(content))
            img.verify()
            return content
    except httpx.HTTPError as e:
        logger.error("HTTP error downloading image: %s", e)
        raise HTTPException(status_code=400, detail=f"Failed to download image: {str(e)}")
    except Exception as e:
        logger.exception("Error validating image from URL")
        raise HTTPException(status_code=400, detail=f"Invalid image or error downloading image: {str(e)}")

def encode_image_to_base64(image_bytes: bytes) -> str:
    import base64
    return base64.b64encode(image_bytes).decode("utf-8")

# Non-streaming calls (kept for backward compatibility)
async def call_ollama_text(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            # Ollama responses may differ; adjust here if needed
            return data.get("response", "") or json.dumps(data)
    except httpx.HTTPStatusError as e:
        logger.error("Ollama returned HTTP error: %s", e)
        raise HTTPException(status_code=502, detail=f"Ollama error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error("Network error connecting to Ollama: %s", e)
        raise HTTPException(status_code=503, detail=f"Cannot reach Ollama: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error calling Ollama")
        raise HTTPException(status_code=500, detail=str(e))

async def call_ollama_vision(prompt: str, image_base64: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "") or json.dumps(data)
    except httpx.HTTPStatusError as e:
        logger.error("Ollama returned HTTP error: %s", e)
        raise HTTPException(status_code=502, detail=f"Ollama error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error("Network error connecting to Ollama: %s", e)
        raise HTTPException(status_code=503, detail=f"Cannot reach Ollama: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error calling Ollama")
        raise HTTPException(status_code=500, detail=str(e))

# SSE streaming proxy to Ollama
async def stream_ollama(prompt: str, image_base64: Optional[str] = None) -> AsyncGenerator[str, None]:
    """
    Proxy Ollama's streaming /api/generate to SSE.
    Each yield is a complete SSE event string (ending with double newline).
    We JSON-wrap the chunk text so the client can parse safely.
    """
    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": True}
    if image_base64:
        payload["images"] = [image_base64]

    url = f"{OLLAMA_BASE_URL}/api/generate"
    logger.info("Opening stream to Ollama: %s", url)

    try:
        # timeout=None allows long-running stream
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=payload) as resp:
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError:
                    # forward error to client as SSE event and stop
                    text = (await resp.aread()).decode("utf-8", errors="ignore")
                    err_payload = {"error": True, "status_code": resp.status_code, "body": text}
                    yield f"data: {json.dumps(err_payload)}\n\n"
                    return

                # Stream JSON lines from Ollama and convert to SSE format
                async for line_bytes in resp.aiter_lines():
                    if not line_bytes:
                        continue
                    line = line_bytes.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse Ollama's JSON response
                        ollama_data = json.loads(line)
                        # Extract the response text chunk
                        if "response" in ollama_data:
                            chunk_text = ollama_data["response"]
                            # Send as SSE event
                            yield f"data: {json.dumps({'text': chunk_text})}\n\n"
                        
                        # Check if done
                        if ollama_data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        # If not JSON, try to send as text
                        if line:
                            yield f"data: {json.dumps({'text': line})}\n\n"

    except httpx.ConnectError as e:
        logger.error("Connection error streaming from Ollama: %s", e)
        yield f"data: {json.dumps({'error': True, 'message': 'Failed to connect to Ollama', 'detail': str(e)})}\n\n"
    except Exception as e:
        logger.exception("Unexpected exception while streaming from Ollama")
        yield f"data: {json.dumps({'error': True, 'message': 'Internal server error', 'detail': str(e)})}\n\n"

    # signal done
    yield "event: done\ndata: {}\n\n"

# Health endpoints
@app.get("/")
async def root():
    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            ollama_status = "connected" if r.status_code == 200 else "error"
    except Exception:
        ollama_status = "disconnected"
    return {
        "status": "healthy",
        "message": "Gemma3 Vision API is running",
        "ollama_status": ollama_status,
        "ollama_url": OLLAMA_BASE_URL,
        "model": MODEL_NAME,
    }

@app.get("/health")
async def health():
    ollama_status = "disconnected"
    ollama_error = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                ollama_status = "connected"
            else:
                ollama_status = "error"
                ollama_error = f"Ollama returned {resp.status_code}"
    except httpx.RequestError:
        ollama_status = "disconnected"
        ollama_error = f"Cannot connect to Ollama at {OLLAMA_BASE_URL}"
    except Exception as e:
        ollama_status = "error"
        ollama_error = str(e)

    return {
        "status": "ok",
        "ollama_status": ollama_status,
        "ollama_url": OLLAMA_BASE_URL,
        "model": MODEL_NAME,
        "ollama_error": ollama_error,
    }

# Existing analyze endpoint (non-streaming) - with async image download fix
@app.post("/analyze", response_model=ChatResponse)
async def analyze_image(
    prompt: str = Form(...),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
):
    prompt = (prompt or "").strip()
    has_image = image is not None or (image_url and image_url.strip())

    if not prompt and has_image:
        prompt = "What is in this image? Describe it in detail."
    elif not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required when no image is provided")

    try:
        if has_image:
            if image:
                image_bytes = await image.read()
                if not image_bytes:
                    raise HTTPException(status_code=400, detail="Uploaded image is empty")
                image_base64 = encode_image_to_base64(image_bytes)
            else:
                image_url = image_url.strip()
                if not is_valid_url(image_url):
                    raise HTTPException(status_code=400, detail=f"Invalid image URL: {image_url}")
                image_bytes = await download_image_from_url(image_url)
                image_base64 = encode_image_to_base64(image_bytes)

            logger.info("Calling Ollama vision (non-streaming)")
            response_text = await call_ollama_vision(prompt, image_base64)
        else:
            logger.info("Calling Ollama text (non-streaming)")
            response_text = await call_ollama_text(prompt)

        return ChatResponse(response=response_text, success=True, message="Analysis completed successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error analyzing image")
        raise HTTPException(status_code=500, detail=str(e))

# Chat endpoint: still supports non-streaming POST
@app.post("/chat", response_model=ChatResponse)
async def chat(request: TextRequest):
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    if request.stream:
        # client asked for streaming but POST-based EventSource can't include body.
        # We support streaming using GET /stream (below) for EventSource.
        # For now, return an informative error.
        raise HTTPException(status_code=400, detail="Streaming from POST is not supported. Use GET /stream?prompt=... for SSE.")
    logger.info("Processing non-streaming chat request")
    response_text = await call_ollama_text(request.prompt)
    return ChatResponse(response=response_text, success=True)

# SSE GET stream endpoint (use EventSource from the browser)
from fastapi import Query as FastAPIQuery

@app.get("/stream")
async def stream(prompt: str = FastAPIQuery(..., min_length=1)):
    """
    SSE endpoint to stream model tokens in real-time (text-only).
    Usage (browser): new EventSource(`/stream?prompt=${encodeURIComponent(prompt)}`)
    """
    gen = stream_ollama(prompt=prompt, image_base64=None)
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(gen, media_type="text/event-stream", headers=headers)

# SSE POST stream endpoint (supports images via FormData)
@app.post("/stream-analyze")
async def stream_analyze(
    prompt: str = Form(...),
    image: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
):
    """
    SSE endpoint to stream model tokens in real-time with image support.
    Supports both uploaded images and image URLs.
    """
    prompt = (prompt or "").strip()
    has_image = image is not None or (image_url and image_url.strip())
    image_base64 = None

    if not prompt and has_image:
        prompt = "What is in this image? Describe it in detail."
    elif not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required when no image is provided")

    try:
        if has_image:
            if image:
                image_bytes = await image.read()
                if not image_bytes:
                    raise HTTPException(status_code=400, detail="Uploaded image is empty")
                image_base64 = encode_image_to_base64(image_bytes)
            else:
                image_url = image_url.strip()
                if not is_valid_url(image_url):
                    raise HTTPException(status_code=400, detail=f"Invalid image URL: {image_url}")
                image_bytes = await download_image_from_url(image_url)
                image_base64 = encode_image_to_base64(image_bytes)

        gen = stream_ollama(prompt=prompt, image_base64=image_base64)
        headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(gen, media_type="text/event-stream", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in stream_analyze")
        raise HTTPException(status_code=500, detail=str(e))

# If you want a streaming analyze (images) flow, implement an upload-first workflow:
# 1) Upload the image to /upload -> returns an id or URL
# 2) Call /stream-analyze?prompt=...&image_id=... (GET) which will stream using that stored image.
# I'll implement that if you ask.

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")





















# from fastapi import FastAPI, HTTPException, File, UploadFile, Form
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# import httpx
# import base64
# import os
# from io import BytesIO
# from PIL import Image
# import logging
# from typing import Optional
# import requests
# from urllib.parse import urlparse

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# app = FastAPI(title="Gemma3 Vision API", version="1.0.0")

# # Enable CORS for React frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Ollama API configuration
# OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# MODEL_NAME = os.getenv("OLLAMA_MODEL", "gemma3:latest")

# class TextRequest(BaseModel):
#     prompt: str
#     stream: bool = False

# class VisionRequest(BaseModel):
#     prompt: str
#     image_url: Optional[str] = None
#     stream: bool = False

# class ChatResponse(BaseModel):
#     response: str
#     success: bool
#     message: str = "Response generated successfully"

# def is_valid_url(url: str) -> bool:
#     """Check if URL is valid"""
#     try:
#         result = urlparse(url)
#         return all([result.scheme, result.netloc])
#     except:
#         return False

# async def download_image_from_url(url: str) -> bytes:
#     """Download image from URL"""
#     try:
#         response = requests.get(url, timeout=30)
#         response.raise_for_status()
        
#         # Verify it's an image
#         img = Image.open(BytesIO(response.content))
#         img.verify()
        
#         return response.content
#     except Exception as e:
#         logger.error(f"Error downloading image from URL: {str(e)}")
#         raise HTTPException(status_code=400, detail=f"Failed to download image from URL: {str(e)}")

# def encode_image_to_base64(image_bytes: bytes) -> str:
#     """Encode image bytes to base64"""
#     return base64.b64encode(image_bytes).decode('utf-8')

# async def call_ollama_vision(prompt: str, image_base64: str) -> str:
#     """Call Ollama API for vision tasks"""
#     try:
#         logger.info(f"Attempting to connect to Ollama at {OLLAMA_BASE_URL} with model {MODEL_NAME}")
#         async with httpx.AsyncClient(timeout=120.0) as client:
#             response = await client.post(
#                 f"{OLLAMA_BASE_URL}/api/generate",
#                 json={
#                     "model": MODEL_NAME,
#                     "prompt": prompt,
#                     "images": [image_base64],
#                     "stream": False
#                 }
#             )
#             response.raise_for_status()
#             result = response.json()
#             response_text = result.get("response", "")
#             if not response_text:
#                 logger.warning("Ollama returned empty response")
#             return response_text
#     except httpx.TimeoutException:
#         logger.error(f"Request to Ollama timed out after 120 seconds")
#         raise HTTPException(
#             status_code=504, 
#             detail=f"Request to Ollama timed out. Please check if Ollama is running at {OLLAMA_BASE_URL} and try again."
#         )
#     except httpx.ConnectError as e:
#         logger.error(f"Failed to connect to Ollama at {OLLAMA_BASE_URL}: {str(e)}")
#         raise HTTPException(
#             status_code=503, 
#             detail=f"Failed to connect to Ollama at {OLLAMA_BASE_URL}. Please ensure Ollama is running and accessible. Error: {str(e)}"
#         )
#     except httpx.RequestError as e:
#         logger.error(f"Request error when calling Ollama: {str(e)}")
#         raise HTTPException(
#             status_code=503, 
#             detail=f"Failed to connect to Ollama: {str(e)}. Please check if Ollama is running at {OLLAMA_BASE_URL}"
#         )
#     except httpx.HTTPStatusError as e:
#         logger.error(f"Ollama returned HTTP error {e.response.status_code}: {e.response.text}")
#         raise HTTPException(
#             status_code=502,
#             detail=f"Ollama returned error {e.response.status_code}: {e.response.text}"
#         )
#     except Exception as e:
#         logger.error(f"Error calling Ollama API: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Error calling Ollama: {str(e)}")

# async def call_ollama_text(prompt: str) -> str:
#     """Call Ollama API for text-only tasks"""
#     try:
#         logger.info(f"Attempting to connect to Ollama at {OLLAMA_BASE_URL} with model {MODEL_NAME}")
#         async with httpx.AsyncClient(timeout=120.0) as client:
#             response = await client.post(
#                 f"{OLLAMA_BASE_URL}/api/generate",
#                 json={
#                     "model": MODEL_NAME,
#                     "prompt": prompt,
#                     "stream": False
#                 }
#             )
#             response.raise_for_status()
#             result = response.json()
#             response_text = result.get("response", "")
#             if not response_text:
#                 logger.warning("Ollama returned empty response")
#             return response_text
#     except httpx.TimeoutException:
#         logger.error(f"Request to Ollama timed out after 120 seconds")
#         raise HTTPException(
#             status_code=504, 
#             detail=f"Request to Ollama timed out. Please check if Ollama is running at {OLLAMA_BASE_URL} and try again."
#         )
#     except httpx.ConnectError as e:
#         logger.error(f"Failed to connect to Ollama at {OLLAMA_BASE_URL}: {str(e)}")
#         raise HTTPException(
#             status_code=503, 
#             detail=f"Failed to connect to Ollama at {OLLAMA_BASE_URL}. Please ensure Ollama is running and accessible. Error: {str(e)}"
#         )
#     except httpx.RequestError as e:
#         logger.error(f"Request error when calling Ollama: {str(e)}")
#         raise HTTPException(
#             status_code=503, 
#             detail=f"Failed to connect to Ollama: {str(e)}. Please check if Ollama is running at {OLLAMA_BASE_URL}"
#         )
#     except httpx.HTTPStatusError as e:
#         logger.error(f"Ollama returned HTTP error {e.response.status_code}: {e.response.text}")
#         raise HTTPException(
#             status_code=502,
#             detail=f"Ollama returned error {e.response.status_code}: {e.response.text}"
#         )
#     except Exception as e:
#         logger.error(f"Error calling Ollama API: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Error calling Ollama: {str(e)}")

# @app.get("/")
# async def root():
#     """Health check endpoint"""
#     # Check if Ollama is accessible
#     ollama_status = "unknown"
#     try:
#         async with httpx.AsyncClient(timeout=5.0) as client:
#             response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
#             if response.status_code == 200:
#                 ollama_status = "connected"
#             else:
#                 ollama_status = "error"
#     except:
#         ollama_status = "disconnected"
    
#     return {
#         "status": "healthy",
#         "message": "Gemma3 Vision API is running",
#         "ollama_status": ollama_status,
#         "ollama_url": OLLAMA_BASE_URL,
#         "model": MODEL_NAME
#     }

# @app.get("/health")
# async def health():
#     """Health check endpoint with Ollama connectivity check"""
#     ollama_status = "disconnected"
#     ollama_error = None
#     try:
#         async with httpx.AsyncClient(timeout=5.0) as client:
#             response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
#             if response.status_code == 200:
#                 ollama_status = "connected"
#                 # Check if model is available
#                 models = response.json().get("models", [])
#                 model_names = [m.get("name", "") for m in models]
#                 if MODEL_NAME not in model_names:
#                     ollama_status = "model_not_found"
#                     ollama_error = f"Model '{MODEL_NAME}' not found. Available models: {', '.join(model_names[:5])}"
#             else:
#                 ollama_status = "error"
#                 ollama_error = f"Ollama returned status {response.status_code}"
#     except httpx.ConnectError as e:
#         ollama_status = "disconnected"
#         ollama_error = f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. Please ensure Ollama is running."
#     except Exception as e:
#         ollama_status = "error"
#         ollama_error = str(e)
    
#     return {
#         "status": "ok",
#         "ollama_status": ollama_status,
#         "ollama_url": OLLAMA_BASE_URL,
#         "model": MODEL_NAME,
#         "ollama_error": ollama_error
#     }

# @app.post("/analyze", response_model=ChatResponse)
# async def analyze_image(
#     prompt: str = Form(...),
#     image: Optional[UploadFile] = File(None),
#     image_url: Optional[str] = Form(None)
# ):
#     """Analyze an image with a text prompt using Ollama"""
#     try:
#         # Normalize prompt - handle empty strings and whitespace
#         prompt = prompt.strip() if prompt else ""
        
#         # Determine if we have an image (upload or URL)
#         has_image = image is not None or (image_url and image_url.strip())
        
#         # If no prompt provided but we have an image, use default prompt
#         if not prompt and has_image:
#             prompt = "What is in this image? Describe it in detail."
#         elif not prompt:
#             raise HTTPException(status_code=400, detail="Prompt is required when no image is provided")
        
#         if has_image:
#             # Handle image from upload
#             if image:
#                 try:
#                     image_bytes = await image.read()
#                     if not image_bytes:
#                         raise HTTPException(status_code=400, detail="Uploaded image file is empty")
#                     image_base64 = encode_image_to_base64(image_bytes)
#                     logger.info(f"Processing uploaded image for vision analysis (size: {len(image_bytes)} bytes)")
#                 except Exception as e:
#                     logger.error(f"Error reading uploaded image: {str(e)}")
#                     raise HTTPException(status_code=400, detail=f"Error processing uploaded image: {str(e)}")
#             # Handle image from URL
#             elif image_url and image_url.strip():
#                 image_url = image_url.strip()
#                 if not is_valid_url(image_url):
#                     raise HTTPException(status_code=400, detail=f"Invalid image URL: {image_url}")
#                 try:
#                     image_bytes = await download_image_from_url(image_url)
#                     image_base64 = encode_image_to_base64(image_bytes)
#                     logger.info(f"Processing image from URL for vision analysis: {image_url[:50]}...")
#                 except HTTPException:
#                     raise
#                 except Exception as e:
#                     logger.error(f"Error processing image URL: {str(e)}")
#                     raise HTTPException(status_code=400, detail=f"Error processing image URL: {str(e)}")
#             else:
#                 raise HTTPException(status_code=400, detail="Either image file or image_url must be provided")
            
#             # Call Ollama vision API
#             logger.info(f"Calling Ollama vision API with prompt: {prompt[:100]}...")
#             response_text = await call_ollama_vision(prompt, image_base64)
#         else:
#             # Text-only query
#             logger.info(f"Processing text-only query: {prompt[:100]}...")
#             response_text = await call_ollama_text(prompt)
        
#         return ChatResponse(
#             response=response_text,
#             success=True,
#             message="Analysis completed successfully"
#         )
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error analyzing image: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Error analyzing: {str(e)}")

# @app.post("/chat", response_model=ChatResponse)
# async def chat(request: TextRequest):
#     """Text-only chat with Ollama"""
#     try:
#         if not request.prompt or not request.prompt.strip():
#             raise HTTPException(status_code=400, detail="Prompt is required")
        
#         logger.info("Processing text-only chat request")
#         response_text = await call_ollama_text(request.prompt)
        
#         return ChatResponse(
#             response=response_text,
#             success=True,
#             message="Response generated successfully"
#         )
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error in chat: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
