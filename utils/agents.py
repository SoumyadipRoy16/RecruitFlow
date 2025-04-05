import json
import groq
import logging
from typing import Dict, Optional, Union
from utils.config import Config
from utils.database import DatabaseManager
from utils.email_sender import EmailSender

logger = logging.getLogger(__name__)

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
        self.client = groq.Groq(api_key=Config.GROQ_API_KEY)
        self.db = DatabaseManager()
        self.email_sender = EmailSender()
        self.max_retries = 3
    
    def _generate_email_template(
        self,
        email_type: str,
        job_title: str,
        candidate_name: str,
        match_details: Optional[Dict] = None,
        interview_date: Optional[str] = None
    ) -> Dict:
        """Core template generation logic for all email types"""
        templates = {
            "interview": {
                "prompt": f"""
                Write a professional interview invitation email in JSON format with:
                - "subject": string
                - "body": string
                - "html_body": string (optional)
                
                Include:
                - Personalized greeting
                - Job title at {Config.COMPANY_NAME}
                - Positive feedback
                - Interview details: {interview_date or 'To be scheduled'}
                - Confirmation instructions
                - Professional closing
                
                Candidate: {candidate_name}
                Match Score: {match_details.get('match_score', 'N/A')}%
                Missing Skills: {', '.join(match_details.get('missing_skills', [])) or 'None'}
                """,
                "required_fields": ["subject", "body"]
            },
            "rejection": {
                "prompt": f"""
                Write a professional rejection email in JSON format with:
                - "subject": string
                - "body": string
                - "html_body": string (optional)
                
                Include:
                - Personalized greeting
                - Thanks for applying to {job_title}
                - Positive remarks
                - Encouragement for future roles
                - Professional closing
                
                Candidate: {candidate_name}
                Company: {Config.COMPANY_NAME}
                """,
                "required_fields": ["subject", "body"]
            }
        }
        
        template = templates.get(email_type)
        if not template:
            raise ValueError(f"Invalid email type: {email_type}")

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=Config.MODEL_NAME,
                    messages=[{"role": "user", "content": template["prompt"]}],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                email_content = json.loads(response.choices[0].message.content)
                
                # Validate response structure
                if not all(field in email_content for field in template["required_fields"]):
                    raise ValueError("Missing required email fields")
                    
                return {
                    'success': True,
                    'email_content': email_content
                }
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    return {
                        'success': False,
                        'error': str(e),
                        'email_content': None
                    }

    def generate_interview_email(
        self,
        job_title: str,
        candidate_name: str,
        candidate_email: Optional[str] = None,
        match_details: Optional[Dict] = None,
        interview_date: Optional[str] = None
    ) -> Dict:
        """Generate and optionally send interview invitation"""
        if match_details is None:
            match_details = {}
            
        result = self._generate_email_template(
            email_type="interview",
            job_title=job_title,
            candidate_name=candidate_name,
            match_details=match_details,
            interview_date=interview_date
        )
        
        if not result['success']:
            return result
            
        # Send email if recipient provided
        if candidate_email:
            send_result = self._send_email(
                email_content=result['email_content'],
                recipient_email=candidate_email
            )
            if not send_result['success']:
                return send_result
                
        return result

    def generate_rejection_email(
        self,
        job_title: str,
        candidate_name: str,
        candidate_email: Optional[str] = None
    ) -> Dict:
        """Generate and optionally send rejection email"""
        result = self._generate_email_template(
            email_type="rejection",
            job_title=job_title,
            candidate_name=candidate_name
        )
        
        if not result['success']:
            return result
            
        # Send email if recipient provided
        if candidate_email:
            send_result = self._send_email(
                email_content=result['email_content'],
                recipient_email=candidate_email
            )
            if not send_result['success']:
                return send_result
                
        return result

    def _send_email(
        self,
        email_content: Dict,
        recipient_email: str
    ) -> Dict:
        """Shared email sending logic"""
        try:
            success = self.email_sender.send_email(
                recipient_email=recipient_email,
                subject=email_content['subject'],
                body=email_content.get('html_body', email_content['body']),
                is_html='html_body' in email_content
            )
            
            if success:
                logger.info(f"Email sent to {recipient_email}")
                return {'success': True}
                
            logger.error(f"Failed to send email to {recipient_email}")
            return {
                'success': False,
                'error': 'Email sending failed',
                'email_content': email_content
            }
            
        except Exception as e:
            logger.error(f"Email error for {recipient_email}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'email_content': email_content
            }