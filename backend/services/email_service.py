"""Email service via Brevo SMTP. Patron canonico (APP_GUIDE 10.2)."""
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from models.app_setting import AppSetting


def _send_sync(to: str, subject: str, html: str, text: Optional[str] = None) -> bool:
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        print(f"[email] SMTP no configurado - skip envio a {to}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
    msg["To"] = to
    if text:
        msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as srv:
            srv.starttls()
            srv.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            srv.sendmail(settings.SMTP_FROM, to, msg.as_string())
        print(f"[email] enviado a {to} -- {subject}")
        return True
    except Exception as e:
        print(f"[email] error enviando a {to}: {e}")
        return False


async def send_email(to: str, subject: str, html: str, text: Optional[str] = None) -> bool:
    """Envia un email via Brevo SMTP. Ejecuta SMTP en thread pool para no
    bloquear el event loop. Devuelve True si se envio OK."""
    return await asyncio.to_thread(_send_sync, to, subject, html, text)


async def _notify_enabled(db: AsyncSession, workspace_id: int, key: str, default: bool = True) -> bool:
    """Lee el toggle de notificacion desde app_settings."""
    row = (await db.execute(
        select(AppSetting).where(AppSetting.workspace_id == workspace_id, AppSetting.key == key)
    )).scalar_one_or_none()
    if row is None:
        return default
    return (row.value or "").lower() == "true"


# ============ Templates ============

def _wrap(title: str, body_html: str) -> str:
    """Envuelve el contenido en un template HTML basico TasAR."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8" /></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; padding: 32px; margin: 0; color: #0f172a;">
      <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="background: #0f172a; color: #ffffff; padding: 24px 28px;">
          <div style="font-size: 20px; font-weight: 900; letter-spacing: -0.02em;">TasAR</div>
          <div style="font-size: 11px; opacity: 0.7; letter-spacing: 0.15em; text-transform: uppercase; margin-top: 2px;">Mapa de valor</div>
        </div>
        <div style="padding: 28px;">
          <h2 style="font-size: 22px; font-weight: 800; margin: 0 0 16px 0; letter-spacing: -0.02em;">{title}</h2>
          {body_html}
        </div>
        <div style="background: #f1f5f9; padding: 16px 28px; font-size: 11px; color: #64748b; text-align: center;">
          Enviado automaticamente por TasAR. Gestionas tus notificaciones en Configuracion.
        </div>
      </div>
    </body>
    </html>
    """


async def notify_appraisal_signed(db: AsyncSession, workspace_id: int, to: str, appraisal_id: int, client_name: str, value: float, currency: str) -> bool:
    if not await _notify_enabled(db, workspace_id, "notify_appraisal"):
        return False
    if not to:
        return False
    body = f"""
      <p>Hola,</p>
      <p>La tasacion <b>#TR-{appraisal_id:04d}</b> fue firmada digitalmente.</p>
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; margin: 16px 0;">
        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: #64748b; font-weight: 700;">Valor final</div>
        <div style="font-size: 28px; font-weight: 900; letter-spacing: -0.02em; margin-top: 4px;">{currency} {value:,.0f}</div>
        <div style="font-size: 13px; color: #64748b; margin-top: 8px;">Cliente: {client_name or 'Sin asignar'}</div>
      </div>
      <p style="font-size: 13px; color: #64748b;">El PDF firmado esta disponible en tu workspace.</p>
    """
    return await send_email(to, f"Tasacion #TR-{appraisal_id:04d} firmada", _wrap("Tasacion firmada", body))


async def notify_comment(db: AsyncSession, workspace_id: int, to: str, author: str, study_code: str, snippet: str) -> bool:
    if not await _notify_enabled(db, workspace_id, "notify_comment"):
        return False
    if not to:
        return False
    body = f"""
      <p><b>{author}</b> comento en el estudio <b>{study_code}</b>:</p>
      <blockquote style="border-left: 3px solid #22c55e; padding: 12px 16px; background: #f8fafc; border-radius: 8px; margin: 16px 0; font-size: 14px; color: #334155;">
        {snippet}
      </blockquote>
    """
    return await send_email(to, f"Nuevo comentario en {study_code}", _wrap("Nuevo comentario", body))


async def notify_weekly_summary(db: AsyncSession, workspace_id: int, to: str, full_name: str, kpis: dict) -> bool:
    if not await _notify_enabled(db, workspace_id, "notify_email"):
        return False
    if not to:
        return False
    rows = "".join(
        f'<tr><td style="padding: 8px 0; color: #64748b; font-size: 13px;">{k}</td>'
        f'<td style="padding: 8px 0; text-align: right; font-weight: 700;">{v}</td></tr>'
        for k, v in kpis.items()
    )
    body = f"""
      <p>Hola {full_name.split(' ')[0] if full_name else ''},</p>
      <p>Tu resumen semanal de actividad en TasAR:</p>
      <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">{rows}</table>
    """
    return await send_email(to, "Tu resumen semanal en TasAR", _wrap("Resumen semanal", body))
