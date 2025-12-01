# 🔧 PowerShell Setup Guide

## Quick PowerShell Commands for Windows

### Step 1: Create Virtual Environment

```powershell
cd "C:\Users\gaura\OneDrive\Desktop\AI projects\Z-Image-Turbo\backend"
python -m venv venv
```

### Step 2: Activate Virtual Environment

**Option 1: Direct activation**
```powershell
.\venv\Scripts\Activate.ps1
```

**Option 2: Using the helper script**
```powershell
.\activate_venv.ps1
```

**Option 3: If you get execution policy error, first run:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then try activating again with Option 1 or 2.

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Start Backend Server

```powershell
python main.py
```

## Common Issues and Solutions

### Issue: "cannot be loaded because running scripts is disabled on this system"

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

This allows PowerShell scripts to run. You'll need to type `Y` to confirm.

### Issue: "The module '.venv' could not be loaded"

**Solution:** Use the correct activation command:
- ✅ Correct: `.\venv\Scripts\Activate.ps1`
- ❌ Wrong: `.venv\Scripts\activate` (this is bash syntax)

### Issue: Virtual environment not found

**Solution:** Make sure you created it first:
```powershell
python -m venv venv
```

## Quick Reference

| Task | PowerShell Command |
|------|-------------------|
| Create venv | `python -m venv venv` |
| Activate venv | `.\venv\Scripts\Activate.ps1` |
| Deactivate venv | `deactivate` |
| Check Python | `python --version` |
| Install packages | `pip install -r requirements.txt` |

## Alternative: Use Command Prompt

If PowerShell gives you trouble, you can use Command Prompt (cmd) instead:

```cmd
cd "C:\Users\gaura\OneDrive\Desktop\AI projects\Z-Image-Turbo\backend"
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
python main.py
```

Or use the batch file:
```cmd
activate_venv.bat
```

## Verify Installation

After activation, you should see `(venv)` at the start of your prompt:
```powershell
(venv) PS C:\Users\gaura\OneDrive\Desktop\AI projects\Z-Image-Turbo\backend>
```

