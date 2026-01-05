import os
import json
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
import google.generativeai as genai

# import from our separate mock classifier module
from mock_classifier import MockClassifier, ClassificationResult

load_dotenv()

class FileClassifier:
    # initilize classifier with Gemini
    def __init__(self, api_key: Optional[str] = None, use_mock: bool = False):
        self.use_mock = use_mock
        
        if use_mock:
            self._mock = MockClassifier()
            return
        
        # import Gemini only if we're using real API
        try:
            import google.generativeai as genai
            self._genai = genai
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. "
                "Run: pip install google-generativeai"
            )
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Gemini API key not found. Either:\n"
                "1. Pass it to FileClassifier(api_key='...')\n"
                "2. Set GEMINI_API_KEY environment variable\n"
                "3. Add it to a .env file"
            )
        
        # confi gemine client
        genai.configure(api_key=self.api_key)
        # init model
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        print("✓ AI Classifier initialized with Gemini 2.0 Flash\n")

    
    # build prompt to set up AI context and role
    def _build_system_prompt(self, existing_folders: list[str]):
        # format folder list nicely
        if existing_folders:
            folder_list = "\n".join(f"  - {folder}" for folder in existing_folders)
        else:
            folder_list = "  (No existing folders)"

        return f'''You are a file organization assistant. Your job is to analyze files 
and decide which folder they belong in.

EXISTING FOLDERS:
{folder_list}

YOUR TASK:
Given a file name, decide where it should be organized. You have two options:
1. Place it in an EXISTING folder (if it's a good match)
2. Suggest a NEW folder name (if no existing folder fits well)

CRITICAL RULES:
- NEVER use "Miscellaneous" or "Uncategorized" as a folder name
- ALWAYS suggest a SPECIFIC, descriptive folder name
- When in doubt, create a new specific folder rather than using a generic one
- Look for context clues: course codes (SOS-231, ORT 111), subjects (Egypt, Biology, Sociology), 
  document types (Essay, Quiz, Assignment, Presentation)

FOLDER NAMING GUIDELINES:
- Use clear, concise folder names (2-4 words max)
- Use Title Case (e.g., "History Essays" not "history essays")
- Be specific: "African History" is better than "History"
- Group by PURPOSE or SUBJECT, not just file type

GOOD FOLDER EXAMPLES:
- "African History" (for Mansa Musa, Egyptian, Diaspora content)
- "Social Sciences" (for sociology, anthropology content)  
- "Biology Coursework" (for biology assignments, labs)
- "Computer Science" (for programming, algorithms)
- "Speech Class" (for speech drafts, presentations)
- "Internship Applications" (for specific job/internship apps)
- "Personal Documents" (for IDs, transcripts, forms)
- "ISA Documents" (for International Students Association files)
- "Research Papers" (for academic research)
- "Hackathon Projects" (for competition/hackathon files)

BAD FOLDER EXAMPLES (NEVER USE):
- "Miscellaneous"
- "Other" 
- "Uncategorized"
- "Random"
- "Stuff" 

RESPOND WITH ONLY A JSON OBJECT in this exact format:
{{
    "suggested_folder": "Specific Folder Name Here",
    "is_new_folder": true or false,
    "confidence": "high" or "medium" or "low",
    "reasoning": "Brief explanation of why this folder fits"
}}

IMPORTANT: 
- Return ONLY the JSON object, no other text
- "is_new_folder" should be true only if the folder doesn't exist in the list above
- Be decisive - pick the BEST option, don't hedge'''
    
    # classify file into folder
    def classify_file(self, file_name: str, file_id: str, existing_folders: list[str], file_content_snippet: Optional[str] = None) -> ClassificationResult:
        # if using mock mode, delegate to mock classifier
        if self.use_mock:
            return self._mock.classify_file(
                file_name, file_id, existing_folders, file_content_snippet
            )
        
        # build user message
        user_message = f"FILE TO CLASSIFY: {file_name}"

        if file_content_snippet:
            user_message += f"\n\nFILE CONTENT PREVIEW:\n{file_content_snippet[:500]}"

        # build full prompt
        full_prompt = self._build_system_prompt(existing_folders) + "\n\n" + user_message

        try:
            # call gemini api
            response = self.model.generate_content(full_prompt)
            # extract text from response
            response_text = response.text.strip()
            # parse JSON response
            result_dict = self._parse_response(response_text)
            # build and return the ClassificationResult
            return ClassificationResult(
                file_id=file_id,
                file_name=file_name,
                suggested_folder=result_dict.get('suggested_folder', 'Uncategorized'),
                is_new_folder=result_dict.get('is_new_folder', True),
                confidence=result_dict.get('confidence', 'low'),
                reasoning=result_dict.get('reasoning', 'No reasoning provided')
            )
        except Exception as e:
            print(f"Error classifying '{file_name}': {e}")
            return ClassificationResult(
                file_id=file_id,
                file_name=file_name,
                suggested_folder="Uncategorized",
                is_new_folder=True,
                confidence="low",
                reasoning=f"Classification failed: {str(e)}"
            )
        
    # parse AI response into a dict
    def _parse_response(self, response_text: str) -> dict:
        text = response_text.strip()
        # remove markdown code blocks if present
        if text.startswith("```"):
            # find the end of the opening ``` line
            first_newline = text.find('\n')
            # find the closing ```
            last_backticks = text.rfind('```')
            if last_backticks > first_newline:
                text = text[first_newline:last_backticks].strip()

        # parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # if JSON parsing fails, try to extract JSON from the text
            import re
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse AI response as JSON: {text[:100]}...")
            
        
    # classify multiple files
    def classify_multiple(self, files: list[str], existing_folders: list[str], extract_content: bool = False, progress_callback = None, service = None) -> list[ClassificationResult]:
        results = []
        total = len(files)

        mode_label = "mock mode" if self.use_mock else "AI mode"
        content_label = " + content reading" if (extract_content and not self.use_mock) else ""
        print(f"Classifying {total} files ({mode_label})...\n")

        all_folders = list(existing_folders) # copy to avoid modifying original

        for i, file in enumerate(files):
            file_name = file.get('name', 'Untitled')
            file_id = file.get('id', '')

            print(f"  [{i+1}/{total}] {file_name[:50]}...")
            
            # extract content if requested and service is available
            content_snippet = None
            if extract_content and service and not self.use_mock:
                try:
                    # import here to avoid circular imports
                    from drive_client import get_file_content_snippet
                    content_snippet = get_file_content_snippet(service, file)
                    if content_snippet:
                        print(f"           (read {len(content_snippet)} chars of content)")
                except Exception as e:
                    pass  

            result = self.classify_file(
                file_name=file_name,
                file_id=file_id,
                existing_folders=all_folders,
                file_content_snippet=content_snippet
            )

            # if suggests new folder, add it to our list
            if result.is_new_folder and result.suggested_folder not in all_folders:
                all_folders.append(result.suggested_folder)
            
            results.append(result)
            # call progress callback if provided
            if progress_callback:
                progress_callback(i + 1, total, result)
            
            print(f"       → {result.suggested_folder} ({result.confidence} confidence)")

        print(f"\n✓ Classification complete!")
        return results
    

if __name__ == "__main__":
    print("=" * 60)
    print(" AI Classifier Test")
    print("=" * 60 + "\n")
    
    # test with some example files
    test_files = [
        {"id": "1", "name": "Newton_Laws_Notes.pdf"},
        {"id": "2", "name": "Resume_2024_Software_Engineer.docx"},
        {"id": "3", "name": "IMG_20240615_vacation_beach.jpg"},
        {"id": "4", "name": "Q3_Budget_Analysis.xlsx"},
        {"id": "5", "name": "Cover_Letter_Google.pdf"},
        {"id": "6", "name": "flight_itinerary_nyc.pdf"},
        {"id": "7", "name": "MANSA MUSA AND ISLAM IN AFRICA.docx"},
        {"id": "8", "name": "SOS-231-1 Chapter 8 Quiz"},
        {"id": "9", "name": "African Diaspora I - Assignment 2"},
        {"id": "10", "name": "ISA Meeting Notes - June 7"},
    ]
    
    # simulate some existing folders
    existing_folders = [
        "Physics Files",
        "Resume",
        "Project",
        "Tech Resources",
        "Uber Career Prep Program Files"
    ]
    
    try:
        # initialize the classifier
        classifier = FileClassifier(use_mock=True)
        
        # classify all test files
        results = classifier.classify_multiple(test_files, existing_folders)
        
        # print summary
        print("\n" + "=" * 60)
        print(" Classification Results")
        print("=" * 60)
        
        # group by folder for nice display
        by_folder = {}
        for r in results:
            folder = r.suggested_folder
            if folder not in by_folder:
                by_folder[folder] = {"files": [], "is_new": r.is_new_folder}
            by_folder[folder]["files"].append(r)
        
        for folder, data in sorted(by_folder.items()):
            status = "NEW" if data["is_new"] else "FOLDER EXISTS"
            print(f"\n{status} {folder}")
            for r in data["files"]:
                print(f"    └── {r.file_name}")
                print(f"        Confidence: {r.confidence} | {r.reasoning[:50]}...")
        
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise
