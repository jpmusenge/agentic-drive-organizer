import re
from dataclasses import dataclass
from typing import Optional

# represents AI's decision about where a file should go
@dataclass
class ClassificationResult:
    file_id: str                  
    file_name: str          
    suggested_folder: str  
    is_new_folder: bool          
    reasoning: str  


class MockClassifier:
    # Keywords that map to folder categories
    KEYWORD_RULES = [
        (r'sos[-_ ]?231', 'Social Sciences'),
        (r'ort[-_ ]?11[12]', 'Oral Communication'),
        (r'comp[-_ ]?ii', 'Computer Science'),
        (r'c\+\+', 'Computer Science'),
        (r'python', 'Computer Science'),
        
        (r'mansa.?musa', 'African History'),
        (r'mali(an)?.*empire', 'African History'),
        (r'african.*diaspora', 'African History'),
        (r'egypt(ian)?', 'African History'),
        (r'pharaoh', 'African History'),
        (r'mesopotamia', 'World History'),
        (r'fertile.?crescent', 'World History'),
        
        (r'physics', 'Physics Files'),
        (r'newton', 'Physics Files'),
        (r'quantum', 'Physics Files'),
        (r'thermodynamics', 'Physics Files'),
        (r'biology', 'Biology Coursework'),
        (r'muscular', 'Biology Coursework'),
        (r'digestive', 'Biology Coursework'),
        (r'immune.*system', 'Biology Coursework'),
        (r'organs', 'Biology Coursework'),
        (r'calculus', 'Mathematics'),
        (r'algorithm', 'Computer Science'),
        (r'dijstra', 'Computer Science'),
        (r'kruskal', 'Computer Science'),
        
        (r'resume', 'Resume'),
        (r'cv\b', 'Resume'),
        (r'curriculum.?vitae', 'Resume'),
        (r'cover[_\s]?letter', 'Job Applications'),
        (r'application', 'Job Applications'),
        (r'internship', 'Job Applications'),
        (r'job.*description', 'Job Applications'),
        (r'interview', 'Interview Prep'),
        (r'behavioral.*interview', 'Interview Prep'),
        
        (r'treehacks', 'Hackathon Projects'),
        (r'nexhacks', 'Hackathon Projects'),
        (r'hackathon', 'Hackathon Projects'),
        (r'microsoft', 'Job Applications'),
        (r'google', 'Job Applications'),
        (r'uber', 'Job Applications'),
        (r'meta\b', 'Job Applications'),
        (r'amazon', 'Job Applications'),
        (r'd\.?e\.?\s*shaw', 'Job Applications'),
        (r'codepath', 'Tech Programs'),
        (r'code2040', 'Tech Programs'),
        (r'new.?technologists', 'Tech Programs'),
        
        (r'\bisa\b', 'ISA Documents'),
        (r'international.*student', 'ISA Documents'),
        (r'\bgdsc\b', 'GDSC Documents'),
        (r'google.*developer', 'GDSC Documents'),
        
        (r'study.?notes', 'Course Notes'),
        (r'notes', 'Course Notes'),
        (r'lecture', 'Course Notes'),
        (r'assignment', 'Course Notes'),
        (r'homework', 'Course Notes'),
        (r'\bquiz\b', 'Course Notes'),
        (r'\bexam\b', 'Course Notes'),
        (r'\bessay\b', 'Essays'),
        (r'research.*paper', 'Research Papers'),
        (r'speech', 'Speech Class'),
        (r'presentation', 'Presentations'),
        
        (r'receipt', 'Financial Records'),
        (r'invoice', 'Financial Records'),
        (r'budget', 'Financial Records'),
        (r'tax', 'Financial Records'),
        (r'bank', 'Financial Records'),
        (r'statement', 'Financial Records'),
        
        (r'transcript', 'Personal Documents'),
        (r'certificate', 'Certificates'),
        (r'certification', 'Certificates'),
        (r'diploma', 'Certificates'),
        (r'recommendation', 'Recommendations'),
        (r'reference', 'Recommendations'),
        
        (r'photo', 'Photos'),
        (r'\bimg\b', 'Photos'),
        (r'image', 'Photos'),
        (r'\.jpe?g$', 'Photos'),
        (r'\.png$', 'Photos'),
        (r'screenshot', 'Screenshots'),
        (r'screen.?recording', 'Screen Recordings'),
        (r'\.mp4$', 'Videos'),
        (r'\.mov$', 'Videos'),
        (r'vid[-_]', 'Videos'),
        
        (r'project', 'Projects'),
        (r'github', 'Projects'),
        (r'firebase', 'Projects'),
    ]
    
    def __init__(self):
        print("✓ Mock Classifier initialized (no API calls)\n")
        print("  ℹ This uses keyword matching to simulate AI classification.")
        print("  ℹ Switch to real AI by setting use_mock=False once quota resets.\n")
    
    # classify file using regex
    def classify_file(self,
                      file_name: str,
                      file_id: str,
                      existing_folders: list[str],
                      file_content_snippet: Optional[str] = None) -> ClassificationResult:

        name_lower = file_name.lower()
        
        # try to match patterns
        suggested_folder = None
        matched_pattern = None
        
        for pattern, folder in self.KEYWORD_RULES:
            if re.search(pattern, name_lower):
                suggested_folder = folder
                matched_pattern = pattern
                break
        
        # check if the suggested folder exists
        if suggested_folder:
            is_new = True
            for existing in existing_folders:
                if existing.lower() == suggested_folder.lower():
                    suggested_folder = existing 
                    is_new = False
                    break
            
            return ClassificationResult(
                file_id=file_id,
                file_name=file_name,
                suggested_folder=suggested_folder,
                is_new_folder=is_new,
                confidence="high",
                reasoning=f"Matched pattern '{matched_pattern}' in filename"
            )
        
        # no pattern match - try to infer from file structure
        if 'untitled' in name_lower:
            return ClassificationResult(
                file_id=file_id,
                file_name=file_name,
                suggested_folder="Drafts",
                is_new_folder="Drafts" not in existing_folders,
                confidence="low",
                reasoning="Untitled document - likely a draft"
            )
        
        # last resort, but NOT Miscellaneous
        return ClassificationResult(
            file_id=file_id,
            file_name=file_name,
            suggested_folder="To Sort",
            is_new_folder="To Sort" not in existing_folders,
            confidence="low",
            reasoning="No clear category detected - needs manual review"
        )
    
    # add new classification rule
    def add_rule(self, pattern: str, folder: str, priority: int = -1) -> None:
        rule = (pattern, folder)
        if priority == -1:
            self.KEYWORD_RULES.append(rule)
        else:
            self.KEYWORD_RULES.insert(priority, rule)
    
    # get all patterns that map to specific folder
    def get_rules_for_folder(self, folder: str) -> list[str]:
        return [pattern for pattern, f in self.KEYWORD_RULES if f == folder]