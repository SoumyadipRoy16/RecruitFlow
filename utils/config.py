import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    DATABASE_PATH = "database/screening.db"
    JOBS_FILE = "data/jobs.json"
    CVS_FOLDER = "data/cvs/"
    MODEL_NAME = "llama3-70b-8192"
    
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    COMPANY_NAME = os.getenv("COMPANY_NAME", "Our Company")
    
    @staticmethod
    def validate():
        if not Config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in environment variables")
        if not Config.EMAIL_ADDRESS or not Config.EMAIL_PASSWORD:
            raise ValueError("Email credentials not set in environment variables")

if not all([Config.SMTP_SERVER, Config.EMAIL_ADDRESS]):
    raise ValueError("SMTP configuration incomplete")