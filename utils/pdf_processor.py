import re
import PyPDF2
from pdfminer.high_level import extract_text
from typing import Dict, List, Optional
from pathlib import Path

class PDFProcessor:
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """Extract text from PDF using PyPDF2 (faster) and fallback to pdfminer if needed"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text.strip()
        except Exception as e:
            print(f"PyPDF2 extraction failed, falling back to pdfminer: {e}")
            return extract_text(pdf_path)
    
    @staticmethod
    def extract_candidate_info(text: str) -> Dict[str, str]:
        """Extract basic candidate info from CV text"""
        info = {
            'name': PDFProcessor._extract_name(text),
            'email': PDFProcessor._extract_email(text),
            'phone': PDFProcessor._extract_phone(text),
            'skills': PDFProcessor._extract_section(text, 'skills', ['technical skills', 'skills']),
            'experience': PDFProcessor._extract_section(text, 'experience', ['work experience', 'experience']),
            'education': PDFProcessor._extract_section(text, 'education', ['education', 'academic background']),
        }
        return info
    
    @staticmethod
    def _extract_name(text: str) -> Optional[str]:
        # Simple pattern to find names (capitalized words)
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and line[0].isupper() and ' ' in line and len(line.split()) <= 3:
                return line
        return None
    
    @staticmethod
    def _extract_email(text: str) -> Optional[str]:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None
    
    @staticmethod
    def _extract_phone(text: str) -> Optional[str]:
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        match = re.search(phone_pattern, text)
        return match.group(0) if match else None
    
    @staticmethod
    def _extract_section(text: str, section_name: str, possible_headers: List[str]) -> Optional[str]:
        """Extract a section from the CV based on possible headers"""
        text_lower = text.lower()
        for header in possible_headers:
            header_pos = text_lower.find(header.lower())
            if header_pos != -1:
                # Find the end of the section (next section header or end of text)
                next_section_pos = len(text)
                for other_header in possible_headers:
                    if other_header != header:
                        pos = text_lower.find(other_header.lower(), header_pos + len(header))
                        if pos != -1 and pos < next_section_pos:
                            next_section_pos = pos
                
                section_text = text[header_pos + len(header):next_section_pos].strip()
                return section_text
        return None