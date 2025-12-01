# 🔍 Gemma3 Vision - AI Image Analysis & Chat

A beautiful web application for analyzing images and chatting with text using Ollama's Gemma3 model.

![Gemma3 Vision](https://img.shields.io/badge/Gemma3-Vision-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![React](https://img.shields.io/badge/React-Frontend-61dafb)

## 🎨 Features

- **Image Analysis**: Upload images or provide image URLs and ask questions about them
- **Vision Capabilities**: Get detailed descriptions, object detection, scene analysis, and more
- **Text-Only Chat**: Ask questions without images for general conversation
- **Flexible Input**: Support for image file uploads or image URLs
- **Beautiful UI**: Modern, responsive interface built with React
- **Ollama Integration**: Powered by local Ollama instance with Gemma3 model

## 🏗️ Architecture

- **Backend**: FastAPI server handling image analysis and text chat with Ollama
- **Frontend**: React.js application with modern UI components
- **Model**: Gemma3 via Ollama (running locally)

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- [Ollama](https://ollama.ai/) installed and running
- Gemma3 model installed in Ollama:
  ```bash
  ollama pull gemma3:latest
  ```

## 🚀 Installation

### 1. Install Ollama

Download and install Ollama from [https://ollama.ai/](https://ollama.ai/)

### 2. Install Gemma3 Model

```bash
ollama pull gemma3:latest
```

Verify installation:
```bash
ollama list
```

### 3. Set Up Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Set Up Frontend

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install
```

## 🎯 Usage

### Starting Ollama

Make sure Ollama is running:

```bash
ollama serve
```

By default, Ollama runs on `http://localhost:11434`

### Starting the Backend Server

```bash
cd backend
# Make sure your virtual environment is activated
python main.py
```

The API server will start on `http://localhost:8000`

### Starting the Frontend

Open a new terminal:

```bash
cd frontend
npm start
```

The React app will start on `http://localhost:3000`

### Using the Application

1. **Image Analysis**:
   - Upload an image file or provide an image URL
   - Enter a question about the image (e.g., "What is in this image?", "Describe the scene")
   - Click "Analyze Image"
   - Get detailed AI-powered analysis

2. **Text-Only Chat**:
   - Leave image fields empty
   - Enter your question or prompt
   - Click "Chat"
   - Get AI-generated response

## ⚙️ Configuration

### Backend Configuration

Environment variables (optional) in `backend/main.py` or as environment variables:

- `OLLAMA_BASE_URL`: Default `http://localhost:11434`
- `OLLAMA_MODEL`: Default `gemma3:latest`

You can also modify these directly in `backend/main.py`:

```python
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "gemma3:latest")
```

### Frontend Configuration

Create a `.env` file in the `frontend` directory to configure the API URL:

```env
REACT_APP_API_URL=http://localhost:8000
```

## 📝 API Endpoints

### `GET /`
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "message": "Gemma3 Vision API is running",
  "ollama_status": "connected",
  "ollama_url": "http://localhost:11434",
  "model": "gemma3:latest"
}
```

### `GET /health`
Health check endpoint

### `POST /analyze`
Analyze an image with a text prompt

**Request (Form Data):**
- `prompt` (required): Text question or prompt
- `image` (optional): Image file upload
- `image_url` (optional): URL to an image

**Response:**
```json
{
  "response": "This image shows...",
  "success": true,
  "message": "Analysis completed successfully"
}
```

### `POST /chat`
Text-only chat

**Request:**
```json
{
  "prompt": "Explain quantum computing",
  "stream": false
}
```

**Response:**
```json
{
  "response": "Quantum computing is...",
  "success": true,
  "message": "Response generated successfully"
}
```

## 🐛 Troubleshooting

### Ollama Connection Issues

- **Ollama not running**: Make sure Ollama is running (`ollama serve`)
- **Wrong port**: Check if Ollama is running on the default port (11434)
- **Model not found**: Ensure gemma3 is installed (`ollama pull gemma3:latest`)

### Image Upload Issues

- **File size**: Maximum file size is 10MB
- **File type**: Only image files are supported (jpg, png, gif, webp, etc.)
- **URL errors**: Ensure image URLs are publicly accessible

### Backend Connection Issues

- Ensure the backend is running on port 8000
- Check CORS settings in `backend/main.py`
- Verify `REACT_APP_API_URL` in frontend `.env` file

### Timeout Issues

- Large images or complex prompts may take longer
- Default timeout is 3 minutes
- Check Ollama logs if requests fail

## 💡 Example Prompts

### Image Analysis:
- "What is in this image?"
- "Describe the scene in detail"
- "What objects do you see?"
- "What is the main subject of this image?"
- "Analyze the composition and colors"

### Text-Only:
- "Explain machine learning in simple terms"
- "What is the difference between AI and ML?"
- "Tell me about neural networks"
- "How does computer vision work?"

## 🔗 Links

- [Ollama Website](https://ollama.ai/)
- [Ollama GitHub](https://github.com/ollama/ollama)
- [Gemma3 Model](https://ollama.ai/library/gemma3)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

## 📄 License

This project is open source and available for personal and commercial use.

## 🙏 Acknowledgments

- Ollama team for the amazing local LLM infrastructure
- Google for the Gemma models

## 🛠️ Development

### Project Structure

```
Z-Image-Turbo/
├── backend/
│   ├── main.py              # FastAPI server
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js          # Main React component
│   │   ├── App.css         # Styles
│   │   ├── index.js        # React entry point
│   │   └── index.css       # Global styles
│   └── package.json        # Node dependencies
├── .gitignore
└── README.md
```

## 📝 Notes

- Make sure Ollama is running before starting the backend
- The first request may take longer as the model loads
- For best results, use clear and specific prompts
- Image analysis works best with clear, well-lit images
- Text-only mode works for any general questions or conversation
