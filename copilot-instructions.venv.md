## Windows Batch Setup Script Requirements

Create a Windows batch script (`setup.bat`) that automates virtual environment setup and application execution.

### Python Version Selection
- **Check requirements.txt for LLM/ML packages**: If the file contains any of these packages: `transformers`, `torch`, `tensorflow`, `langchain`, `openai`, `llama-cpp-python`, `sentence-transformers`, `diffusers`, `accelerate`, `bitsandbytes`, use `C:\Python311\python.exe`
- **Otherwise**: Use system `python` command
- **Implementation**: Parse requirements.txt line-by-line, check each package name against the LLM package list

### Virtual Environment Workflow

**If venv doesn't exist:**
1. Create virtual environment using selected Python interpreter
2. Activate the virtual environment (`call venv\Scripts\activate.bat`)
3. Upgrade pip: `python -m pip install --upgrade pip`
4. Install packages from requirements.txt: `pip install -r requirements.txt`

**If venv exists:**
1. Activate existing virtual environment
2. Verify all packages from requirements.txt are installed by attempting to import them
3. If any packages are missing, upgrade pip and run `pip install -r requirements.txt`

### Progress Display Format
Use this exact format for section headers:
```
echo ================================================
echo [M/N] Section Description Here
echo ================================================
```

Where M is the current step number and N is the total number of steps (typically 4):
- `[1/4] Creating virtual environment...` or `[1/4] Activating virtual environment...`
- `[2/4] Installing packages from requirements.txt...` or `[2/4] Verifying installed packages...`
- `[3/4] Running <ApplicationName>...`
- `[4/4] Application closed!`

### Error Handling
- Check `errorlevel` after critical operations (venv creation, pip install)
- Display clear error messages with `echo ERROR: <description>`
- Pause with `pause` to let user read error messages
- Exit with `exit /b 1` on fatal errors

### User Interaction Points
- **Before running app**: `pause` with message "Press any key to run the application..."
- **After app closes**: `pause` with message "Press any key to exit..."
- This ensures console output remains visible and is not lost

### Output Clarity
- Use `echo.` for blank lines between sections
- Use `echo [INFO]` prefix for informational messages
- Use `echo ERROR:` prefix for error messages
- Suppress unnecessary output with `>nul` or `2>nul` where appropriate