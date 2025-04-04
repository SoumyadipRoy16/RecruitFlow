import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from utils.config import Config

class EmailSender:
    @staticmethod
    def send_email(
        recipient_email: str,
        subject: str,
        body: str,
        is_html: bool = False
    ) -> bool:
        """
        Send an email to the recipient
        
        Args:
            recipient_email: Email address of the recipient
            subject: Email subject
            body: Email body content
            is_html: Whether the body is HTML formatted
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not recipient_email:
            raise ValueError("Recipient email is required")
        
        message = MIMEMultipart()
        message["From"] = Config.EMAIL_ADDRESS
        message["To"] = recipient_email
        message["Subject"] = subject
        
        # Attach the body
        if is_html:
            message.attach(MIMEText(body, "html"))
        else:
            message.attach(MIMEText(body, "plain"))
        
        try:
            # Create secure connection
            context = ssl.create_default_context()
            
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(Config.EMAIL_ADDRESS, Config.EMAIL_PASSWORD)
                server.sendmail(
                    Config.EMAIL_ADDRESS,
                    recipient_email,
                    message.as_string()
                )
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False