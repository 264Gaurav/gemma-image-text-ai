# ⚡ Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Start Ollama

Open a terminal and run:
```bash
ollama serve
```

### 2. Start Backend

Open a new terminal:
```bash
cd backend
# Activate virtual environment
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

python main.py
```

### 3. Start Frontend

Open another terminal:
```bash
cd frontend
npm start
```

The app will open at `http://localhost:3000`

## 🎯 How to Use

### Analyze an Image

1. **Upload an Image**:
   - Click "Upload Image"
   - Select an image file from your computer
   - Or click "Image URL" and paste an image URL

2. **Ask a Question**:
   - Enter a question like "What is in this image?"
   - Click "Analyze Image"

3. **View Results**:
   - See the AI's analysis appear in the right panel

### Text-Only Chat

1. **Leave Image Fields Empty**
2. **Enter Your Question**:
   - Type any question or prompt
   - Click "Chat"
3. **Get Response**:
   - See the AI's response appear in the right panel

## 💡 Example Questions

### For Images:
- "What is in this image?"
- "Describe the scene in detail"
- "What objects do you see?"
- "What colors are prominent?"
- "Analyze the composition"

### For Text Chat:
- "Explain quantum computing"
- "What is machine learning?"
- "How does a neural network work?"
- "Tell me about AI"

## 🛠️ Troubleshooting

**Problem**: "Failed to connect to Ollama"  
**Solution**: Make sure `ollama serve` is running

**Problem**: "Model not found"  
**Solution**: Run `ollama pull gemma3:latest`

**Problem**: Image won't upload  
**Solution**: Check file size (max 10MB) and format (jpg, png, etc.)

## 📝 Notes

- First request may take a bit longer as the model loads
- Keep Ollama running while using the app
- Both image analysis and text chat work seamlessly!

