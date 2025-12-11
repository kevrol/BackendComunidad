import emails
from emails.template import JinjaTemplate
from .config import settings

def send_email(email_to: str, subject: str, html_content: str):
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.emails_from_name, settings.emails_from_email)
    )
    
    smtp_options = {
        "host": settings.email_host,
        "port": settings.email_port,
        "tls": True,
        "user": settings.email_username,
        "password": settings.email_password
    }
    
    response = message.send(to=email_to, smtp=smtp_options)
    return response

def send_verification_email(email_to: str, username: str, token: str):
    verification_url = f"{settings.frontend_url}/verify-email?token={token}"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #007a99; text-align: center;">¡Bienvenido a Kaimo!</h2>
                <p>Hola <strong>{username}</strong>,</p>
                <p>Gracias por registrarte. Para completar tu registro, por favor verifica tu correo electrónico haciendo clic en el siguiente botón:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                        style="background-color: #007a99; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Verificar Correo
                    </a>
                </div>
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    Si no creaste esta cuenta, puedes ignorar este correo.
                </p>
            </div>
        </body>
    </html>
    """
    
    send_email(
        email_to=email_to,
        subject="Verifica tu correo electrónico",
        html_content=html_content
    )