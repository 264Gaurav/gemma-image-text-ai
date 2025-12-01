# 🚀 Quick Setup Guide - Gemma3 Vision

## Step-by-Step Installation

### Step 1: Install Ollama

1. **Download Ollama**:
   - Visit [https://ollama.ai/](https://ollama.ai/)
   - Download and install for your operating system

2. **Verify Installation**:
   ```bash
   ollama --version
   ```

### Step 2: Install Gemma3 Model

```bash
ollama pull gemma3:latest
```

This will download the model (approximately 3.3GB). Verify installation:
```bash
ollama list
```

You should see `gemma3:latest` in the list.

### Step 3: Start Ollama Server

```bash
ollama serve
```

Keep this terminal open. Ollama will run on `http://localhost:11434` by default.

### Step 4: Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   
   **Windows PowerShell:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
   
   **Note**: If you get an execution policy error, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
   
   **Windows Command Prompt:**
   ```cmd
   python -m venv venv
   venv\Scripts\activate.bat
   ```
   
   **Or use the helper script:**
   ```powershell
   .\activate_venv.ps1
   ```
   
   **Linux/Mac:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the backend server:**
   ```bash
   python main.py
   ```
   
   The server will start on `http://localhost:8000`
   
   **Note**: Make sure Ollama is running first!

### Step 5: Frontend Setup

1. **Open a new terminal and navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the React app:**
   ```bash
   npm start
   ```
   
   The app will open automatically in your browser at `http://localhost:3000`

## 🎯 Quick Start Commands

### Windows

**Terminal 1 - Ollama:**
```bash
ollama serve
```

**Terminal 2 - Backend:**
```bash
cd backend
venv\Scripts\activate
python main.py
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm start
```

### Linux/Mac

**Terminal 1 - Ollama:**
```bash
ollama serve
```

**Terminal 2 - Backend:**
```bash
cd backend
source venv/bin/activate
python main.py
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm start
```

## ✅ Verification

1. **Check Ollama**: Visit `http://localhost:11434/api/tags` - should return JSON with your models
2. **Check Backend**: Visit `http://localhost:8000` - should show API status
3. **Check Frontend**: Should open automatically at `http://localhost:3000`

## 🐛 Common Issues

### Issue: "Failed to connect to Ollama"
**Solutions**:
- Make sure Ollama is running: `ollama serve`
- Check if Ollama is on the correct port (default: 11434)
- Verify with: `curl http://localhost:11434/api/tags`

### Issue: "Model not found"
**Solution**: Install the model:
```bash
ollama pull gemma3:latest
```

### Issue: "Connection refused" when accessing API
**Solutions**:
- Ensure backend is running on port 8000
- Check firewall settings
- Verify no other service is using port 8000

### Issue: Frontend can't connect to backend
**Solutions**:
- Ensure backend is running on port 8000
- Check CORS settings in `backend/main.py`
- Verify `REACT_APP_API_URL` in frontend `.env` file (optional, defaults to localhost:8000)

### Issue: Image upload fails
**Solutions**:
- Check file size (max 10MB)
- Ensure file is an image format (jpg, png, gif, webp, etc.)
- For URLs, ensure the image is publicly accessible

### Issue: Slow response times
**Solutions**:
- First request may be slower as the model loads
- Larger images take longer to process
- Consider using GPU-accelerated Ollama for faster inference

## ⚙️ Configuration

### Change Ollama URL or Model

Edit `backend/main.py`:
```python
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "gemma3:latest")
```

Or set environment variables:
```bash
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=gemma3:latest
```

### Change API Port

Edit `backend/main.py`:
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # Change port here
```

### Frontend API URL

Create `frontend/.env`:
```
REACT_APP_API_URL=http://localhost:8000
```

## 💡 Tips

- Keep Ollama running in a separate terminal
- The first image analysis may take longer as the model initializes
- Use clear, descriptive prompts for better results
- Image analysis works best with high-quality, well-lit images
- Text-only mode is great for general questions and explanations

## 🔧 Testing

### Test Ollama Directly

```bash
ollama run gemma3:latest
```

Then try a prompt in the interactive session.

### Test Backend API

```bash
curl http://localhost:8000/
```

### Test Image Analysis

Use the web interface or curl:
```bash
curl -X POST http://localhost:8000/analyze \
  -F "prompt=What is in this image?" \
  -F "image_url=https://example.com/image.jpg"
```

## 📚 Additional Resources

- [Ollama Documentation](https://github.com/ollama/ollama)
- [Gemma3 Model Card](https://ollama.ai/library/gemma3)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
