"""
SendGrid email service for newsletter and notifications
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@freshmotors.net')
        self.from_name = os.getenv('SENDGRID_FROM_NAME', 'Fresh Motors')
        
        if not self.api_key:
            logger.warning('SENDGRID_API_KEY not set - email sending disabled')
            self.client = None
        else:
            self.client = SendGridAPIClient(self.api_key)
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None):
        """Send email via SendGrid"""
        if not self.client:
            logger.warning(f'Email not sent to {to_email} - SendGrid not configured')
            return False
        
        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            if text_content:
                message.plain_text_content = Content("text/plain", text_content)
            
            response = self.client.send(message)
            logger.info(f'Email sent to {to_email}: {response.status_code}')
            return response.status_code in [200, 201, 202]
        except Exception as e:
            logger.error(f'Failed to send email to {to_email}: {str(e)}')
            return False
    
    def send_newsletter_welcome(self, to_email: str):
        """Send welcome email to new newsletter subscriber"""
        subject = "Welcome to Fresh Motors Newsletter! 🚗"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚗 Welcome to Fresh Motors!</h1>
                </div>
                <div class="content">
                    <h2>Thanks for subscribing!</h2>
                    <p>You're now part of the Fresh Motors community. Get ready to receive:</p>
                    <ul>
                        <li>📰 Latest automotive news and industry insights</li>
                        <li>🚙 In-depth car reviews and comparisons</li>
                        <li>💡 Expert tips and buying guides</li>
                        <li>🔥 Exclusive content and early access to articles</li>
                    </ul>
                    <p>We'll send you weekly updates with the best automotive content, straight to your inbox.</p>
                    <a href="https://freshmotors.net" class="button">Visit Fresh Motors</a>
                    <p style="margin-top: 30px; font-size: 14px; color: #666;">
                        Don't want to receive these emails? <a href="https://freshmotors.net/unsubscribe?email={to_email}">Unsubscribe</a>
                    </p>
                </div>
                <div class="footer">
                    <p>© 2026 Fresh Motors. All rights reserved.</p>
                    <p>You're receiving this because you subscribed to our newsletter at freshmotors.net</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Fresh Motors Newsletter!
        
        Thanks for subscribing! You're now part of the Fresh Motors community.
        
        You'll receive:
        - Latest automotive news and industry insights
        - In-depth car reviews and comparisons
        - Expert tips and buying guides
        - Exclusive content and early access to articles
        
        Visit us at: https://freshmotors.net
        
        Don't want to receive these emails? Unsubscribe: https://freshmotors.net/unsubscribe?email={to_email}
        
        © 2026 Fresh Motors. All rights reserved.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)

# Global instance
email_service = EmailService()
