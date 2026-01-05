# Agentic-Type Google Drive File Organizer

I felt a little lazy organizing my files in Google Drive into folders, so I figured I could automate this process. This project does the organizing, although I may still need to rename some of the folder names it creates.

## What It Does

- Scans your Google Drive for loose files (files not in any folder)
- Uses AI (Google Gemini) to figure out where each file should go based on its name and content
- Shows you a preview of the proposed organization before making any changes
- Lets you rename folders, skip files, or move things around before approving
- Actually moves the files once you say "yes"

## How It Works (If You're Interested)

### Prerequisites

- Python 3.10+
- A Google Cloud project with the Drive API enabled
- A Gemini API key (free tier works)

### Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/drive-organizer.git
   cd drive-organizer
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Get your Google credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project and enable the Google Drive API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download the JSON and save it as `credentials.json` in the project root

4. **Get a Gemini API key**
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create an API key
   - Create a `.env` file:
     ```
     GEMINI_API_KEY=your_api_key_here
     ```

### Usage

```bash
# See what it would do (no changes made)
python src/drive_organizer/organizer.py --dry-run

# Actually organize your files (with AI)
python src/drive_organizer/organizer.py --ai

# AI + read file contents for smarter classification
python src/drive_organizer/organizer.py --ai --read-content
```

### Options

| Flag | What it does |
|------|--------------|
| `--dry-run` | Preview the plan without executing |
| `--ai` | Use Gemini AI for classification |
| `--read-content` | Read file contents for smarter sorting |
