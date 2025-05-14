"""
Email Notification Provider
----------------------
Provides integration with email services for notifications.
"""

import os
import logging
import aiosmtplib
import asyncio
from typing import Dict, Any, List, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..base import NotificationProvider

# Setup logger
logger = logging.getLogger(__name__)


class EmailProvider(NotificationProvider):
    """Email notification provider."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for SMTP settings
        host = self.config.get('smtp_host') or os.getenv('SMTP_HOST')
        if not host:
            raise ValueError("SMTP host is required. Set 'smtp_host' in config or SMTP_HOST environment variable.")
        
        # Set default values
        self.config.setdefault('smtp_host', host)
        self.config.setdefault('smtp_port', int(os.getenv('SMTP_PORT', '587')))
        self.config.setdefault('smtp_user', self.config.get('smtp_user') or os.getenv('SMTP_USER'))
        self.config.setdefault('smtp_password', self.config.get('smtp_password') or os.getenv('SMTP_PASSWORD'))
        self.config.setdefault('use_tls', os.getenv('SMTP_USE_TLS', 'true').lower() == 'true')
        self.config.setdefault('from_email', self.config.get('from_email') or os.getenv('EMAIL_FROM'))
        self.config.setdefault('to_email', self.config.get('to_email') or os.getenv('EMAIL_TO'))
        self.config.setdefault('timeout', int(os.getenv('SMTP_TIMEOUT', '30')))
        
        # Check for from email
        if not self.config['from_email']:
            raise ValueError("From email is required. Set 'from_email' in config or EMAIL_FROM environment variable.")
    
    def initialize(self) -> None:
        """Initialize the email provider."""
        try:
            logger.info(f"Initialized email notification provider with server: {self.config['smtp_host']}:{self.config['smtp_port']}")
        except Exception as e:
            logger.error(f"Error initializing email provider: {str(e)}")
            raise
    
    async def send_notification(self, 
                               message: str, 
                               title: Optional[str] = None, 
                               level: str = "info", 
                               recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send a notification via email.
        
        Args:
            message: Notification message
            title: Optional notification title
            level: Notification level (info, warning, error, success)
            recipients: Optional list of recipients (email addresses)
            
        Returns:
            Dictionary with send status
        """
        try:
            # Determine recipients
            to_emails = []
            if recipients:
                to_emails = recipients
            elif self.config['to_email']:
                # Parse comma-separated emails
                to_emails = [email.strip() for email in self.config['to_email'].split(',')]
            else:
                # If no recipients and no default email, fail
                raise ValueError("No email recipients specified. Provide recipients or set default to_email.")
            
            # Create email subject
            subject = title if title else f"{level.capitalize()} Notification from Scout Agent"
            
            # Create HTML message with nice formatting
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .header {{ background-color: #f8f9fa; padding: 20px; border-bottom: 1px solid #ddd; }}
                    .content {{ padding: 20px; }}
                    .footer {{ background-color: #f8f9fa; padding: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #777; }}
                    .info {{ border-left: 4px solid #3498db; }}
                    .success {{ border-left: 4px solid #2ecc71; }}
                    .warning {{ border-left: 4px solid #f39c12; }}
                    .error {{ border-left: 4px solid #e74c3c; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>{subject}</h2>
                    </div>
                    <div class="content {level.lower()}">
                        <p>{message.replace('\\n', '<br>')}</p>
                    </div>
                    <div class="footer">
                        <p>Sent from Scout Agent at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                        <p>Level: {level.capitalize()}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create plain text version
            plain_text = f"""
            {subject}
            
            {message}
            
            Sent from Scout Agent at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            Level: {level.capitalize()}
            """
            
            # Send email to each recipient
            results = []
            
            for to_email in to_emails:
                # Create message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.config['from_email']
                msg['To'] = to_email
                
                # Attach plain text and HTML versions
                msg.attach(MIMEText(plain_text, 'plain'))
                msg.attach(MIMEText(html_content, 'html'))
                
                # Connect to SMTP server and send
                try:
                    smtp = aiosmtplib.SMTP(
                        hostname=self.config['smtp_host'],
                        port=self.config['smtp_port'],
                        timeout=self.config['timeout']
                    )
                    
                    if self.config['use_tls']:
                        await smtp.starttls()
                    
                    if self.config['smtp_user'] and self.config['smtp_password']:
                        await smtp.login(self.config['smtp_user'], self.config['smtp_password'])
                    
                    send_result = await smtp.send_message(msg)
                    await smtp.quit()
                    
                    results.append({
                        "recipient": to_email,
                        "success": True,
                        "response": str(send_result)
                    })
                
                except Exception as e:
                    results.append({
                        "recipient": to_email,
                        "success": False,
                        "error": str(e)
                    })
            
            # Check if all emails were sent successfully
            all_success = all(result["success"] for result in results)
            
            return {
                "success": all_success,
                "provider": "email",
                "results": results
            }
        
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            
            return {
                "success": False,
                "provider": "email",
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the email integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple connection to check if the SMTP server is accessible
            loop = asyncio.get_event_loop()
            
            async def check():
                smtp = aiosmtplib.SMTP(
                    hostname=self.config['smtp_host'],
                    port=self.config['smtp_port'],
                    timeout=self.config['timeout']
                )
                
                await smtp.connect()
                
                if self.config['use_tls']:
                    await smtp.starttls()
                
                if self.config['smtp_user'] and self.config['smtp_password']:
                    await smtp.login(self.config['smtp_user'], self.config['smtp_password'])
                
                await smtp.quit()
                return True
            
            is_connected = loop.run_until_complete(check())
            
            if is_connected:
                return {
                    "status": "healthy",
                    "provider": "email",
                    "details": {
                        "smtp_host": self.config['smtp_host'],
                        "smtp_port": self.config['smtp_port'],
                        "from_email": self.config['from_email']
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "email",
                    "error": "Failed to connect to SMTP server"
                }
        
        except Exception as e:
            logger.error(f"Email health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "email",
                "error": str(e)
            }