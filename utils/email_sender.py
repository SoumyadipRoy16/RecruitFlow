import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Union, List
from utils.config import Config
import logging

logger = logging.getLogger(__name__)

class EmailSender:
    @staticmethod
    def send_email(
        recipient_email: Union[str, List[str]],
        subject: str,
        body: Union[str, Dict],
        is_html: bool = False,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Dict[str, Union[str, bytes]]]] = None
    ) -> bool:
        """
        Send an email to one or more recipients with optional attachments.
        
        Args:
            recipient_email: Email address(es) of the recipient(s)
            subject: Email subject
            body: Email body content (string or dictionary)
            is_html: Whether the body is HTML formatted
            cc: CC recipient(s)
            bcc: BCC recipient(s)
            attachments: List of attachments (each as dict with 'filename' and 'content')
            
        Returns:
            bool: True if email was sent successfully, False otherwise
            
        Raises:
            ValueError: If recipient_email is empty or invalid
            TypeError: If body cannot be converted to string
        """
        # Validate and normalize recipients
        recipients = EmailSender._normalize_recipients(recipient_email)
        if not recipients:
            raise ValueError("At least one recipient email is required")
        
        # Convert body to string if it's a dictionary
        if isinstance(body, dict):
            body = EmailSender._dict_to_email_body(body, is_html)
        
        if not isinstance(body, str):
            raise TypeError(f"Body must be string or dict, got {type(body).__name__}")
        
        # Create message container
        message = MIMEMultipart()
        message["From"] = Config.EMAIL_ADDRESS
        message["To"] = ", ".join(recipients) if isinstance(recipient_email, list) else recipient_email
        message["Subject"] = subject
        
        # Add CC/BCC if specified
        if cc:
            cc_recipients = EmailSender._normalize_recipients(cc)
            message["Cc"] = ", ".join(cc_recipients)
            recipients.extend(cc_recipients)
            
        if bcc:
            bcc_recipients = EmailSender._normalize_recipients(bcc)
            recipients.extend(bcc_recipients)
        
        # Attach the body
        message.attach(MIMEText(body, "html" if is_html else "plain"))
        
        # Add attachments if specified
        if attachments:
            from email.mime.application import MIMEApplication
            from email.mime.base import MIMEBase
            for attachment in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment['content'])
                part.add_header('Content-Disposition', f'attachment; filename="{attachment["filename"]}"')
                message.attach(part)
        
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
                    recipients,  # Send to all recipients (To, Cc, Bcc)
                    message.as_string()
                )
            logger.info(f"Email sent successfully to {recipients}")
            return True
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
        return False

    @staticmethod
    def _normalize_recipients(recipients: Union[str, List[str]]) -> List[str]:
        """Convert recipient input to list of email strings."""
        if isinstance(recipients, str):
            return [email.strip() for email in recipients.split(",") if email.strip()]
        elif isinstance(recipients, list):
            return [email.strip() for email in recipients if isinstance(email, str) and email.strip()]
        return []

    @staticmethod
    def _dict_to_email_body(data: Dict, is_html: bool = False) -> str:
        """Convert dictionary to formatted email body."""
        if is_html:
            return "<br>".join(f"<b>{k}:</b> {v}" for k, v in data.items())
        return "\n".join(f"{k}: {v}" for k, v in data.items())