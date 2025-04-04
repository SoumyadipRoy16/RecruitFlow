import json
import groq
from typing import Dict, Optional
from utils.config import Config
from utils.database import DatabaseManager
from utils.email_sender import EmailSender

class JobDescriptionSummarizer:
    def __init__(self):
        self.client = groq.Client(api_key=Config.GROQ_API_KEY)
        self.db = DatabaseManager()
    
    def summarize_job_description(self, job_description: str) -> Dict:
        prompt = f"""
        Analyze the following job description and extract key information in JSON format with these fields:
        - required_skills (list)
        - required_experience (string)
        - required_qualifications (list)
        - key_responsibilities (list)
        - preferred_qualifications (list, optional)
        - soft_skills (list, optional)
        
        Job Description:
        {job_description}
        
        Return ONLY the JSON object, no additional text or explanation.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            return json.loads(summary)
        except Exception as e:
            print(f"Error summarizing job description: {e}")
            return None

class RecruitingAgent:
    def __init__(self):
        self.client = groq.Client(api_key=Config.GROQ_API_KEY)
        self.db = DatabaseManager()
    
    def extract_candidate_data(self, cv_text: str) -> Dict:
        prompt = f"""
        Analyze the following CV text and extract structured information in JSON format with these fields:
        - name (string)
        - email (string, optional)
        - phone (string, optional)
        - skills (list)
        - experience (list of objects with fields: title, company, duration, description)
        - education (list of objects with fields: degree, institution, year)
        - certifications (list, optional)
        - projects (list of objects with fields: name, description, technologies, optional)
        
        CV Text:
        {cv_text}
        
        Return ONLY the JSON object, no additional text or explanation.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            
            extracted_data = response.choices[0].message.content
            return json.loads(extracted_data)
        except Exception as e:
            print(f"Error extracting candidate data: {e}")
            return None
    
    def calculate_match_score(self, job_summary: Dict, candidate_data: Dict) -> float:
        prompt = f"""
        Calculate a match score between 0 and 100 for this candidate against the job requirements.
        Consider skills match (50% weight), experience match (30% weight), and qualifications match (20% weight).
        
        Job Requirements:
        {json.dumps(job_summary, indent=2)}
        
        Candidate Profile:
        {json.dumps(candidate_data, indent=2)}
        
        Return ONLY a JSON object with these fields:
        - match_score (float)
        - skills_match (percentage)
        - experience_match (percentage)
        - qualifications_match (percentage)
        - missing_skills (list)
        - missing_experience (list)
        - missing_qualifications (list)
        
        No additional text or explanation.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            match_result = response.choices[0].message.content
            return json.loads(match_result)
        except Exception as e:
            print(f"Error calculating match score: {e}")
            return {"match_score": 0.0}

class InterviewScheduler:
    def __init__(self):
        self.client = groq.Client(api_key=Config.GROQ_API_KEY)
        self.db = DatabaseManager()
        self.email_sender = EmailSender()
    
def generate_interview_email(self, job_title: str, candidate_name: str, 
                           candidate_email: str = None, match_details: dict = None, 
                           interview_date: str = None) -> Dict:
    """
    Generate interview email content and optionally send it
    
    Args:
        job_title: Title of the job position
        candidate_name: Name of the candidate
        candidate_email: Email address (optional)
        match_details: Dictionary of matching info (optional)
        interview_date: Scheduled interview datetime (optional)
        
    Returns:
        Dict: {
            'success': bool,
            'email_content': dict,
            'error': str (if any)
        }
    """
    if match_details is None:
        match_details = {}
    
    prompt = f"""
    Write a professional interview invitation email for a candidate who has been shortlisted.
    The email should be in JSON format with these exact keys:
    - "subject": string (email subject line)
    - "body": string (plain text email content)
    - "html_body": string (optional HTML version)

    Include these elements:
    - Personalized greeting
    - Mention of job title at {Config.COMPANY_NAME}
    - Positive comment about their application
    - Interview details if available
    - Instructions for confirmation
    - Professional closing
    
    Job Title: {job_title}
    Candidate Name: {candidate_name}
    Company: {Config.COMPANY_NAME}
    Match Score: {match_details.get('match_score', 'N/A')}%
    Interview Date: {interview_date or 'To be scheduled'}
    """
    
    try:
        response = self.client.chat.completions.create(
            model=Config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        # Safely parse the JSON response
        try:
            email_content = json.loads(response.choices[0].message.content)
            
            # Validate the response structure
            if not isinstance(email_content, dict) or 'subject' not in email_content or 'body' not in email_content:
                return {
                    'success': False,
                    'error': 'Invalid email content structure',
                    'email_content': None
                }
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'Failed to parse email content: {str(e)}',
                'email_content': None
            }
        
        # Send email if recipient provided
        if candidate_email:
            success = self.email_sender.send_email(
                recipient_email=candidate_email,
                subject=email_content['subject'],
                body=email_content.get('html_body', email_content['body']),
                is_html='html_body' in email_content
            )
            
            if not success:
                return {
                    'success': False,
                    'email_content': email_content,
                    'error': 'Email sending failed'
                }
        
        return {
            'success': True,
            'email_content': email_content
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'email_content': None
        }
    
    def generate_rejection_email(self, job_title: str, candidate_name: str, 
                               candidate_email: str) -> Dict:
        """
        Generate and send rejection email
        
        Returns:
            Dict: {
                'success': bool,
                'email_content': str,
                'error': str (if any)
            }
        """
        prompt = f"""
        Write a professional rejection email for a candidate who applied but wasn't selected.
        Include:
        - Personalized greeting
        - Thank them for their time and application
        - Mention the job title and company name ({Config.COMPANY_NAME})
        - Encourage them to apply for future positions
        - Professional closing
        
        Job Title: {job_title}
        Candidate Name: {candidate_name}
        Company Name: {Config.COMPANY_NAME}
        
        Return a JSON object with these fields:
        - subject (email subject line)
        - body (email body text)
        - html_body (HTML formatted email body, optional)
        """
        
        try:
            response = self.client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            
            email_content = json.loads(response.choices[0].message.content)
            
            # Send the email
            if candidate_email:
                success = self.email_sender.send_email(
                    recipient_email=candidate_email,
                    subject=email_content['subject'],
                    body=email_content.get('html_body', email_content['body']),
                    is_html='html_body' in email_content
                )
                
                if not success:
                    return {
                        'success': False,
                        'email_content': email_content,
                        'error': 'Failed to send email'
                    }
            
            return {
                'success': True,
                'email_content': email_content
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }