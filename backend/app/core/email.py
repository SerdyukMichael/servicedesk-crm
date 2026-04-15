"""
Минимальная SMTP-утилита для отправки уведомлений.

Поддерживаемые провайдеры (STARTTLS, порт 587):
  Brevo:   smtp-relay.brevo.com
  Yandex:  smtp.yandex.ru
  Mail.ru: smtp.mail.ru
  Gmail:   smtp.gmail.com

Если smtp_host / smtp_user / smtp_password не заданы в .env — функция
возвращает без действий (graceful no-op), система работает без email.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_addresses: List[str], subject: str, body_html: str) -> None:
    """Отправить HTML-письмо через SMTP.

    Если SMTP не настроен (smtp_host/smtp_user/smtp_password отсутствуют) —
    запись в лог и возврат без ошибки.
    """
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        logger.debug("SMTP не настроен, письмо пропущено: %s", subject)
        return

    recipients = [addr for addr in to_addresses if addr]
    if not recipients:
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(settings.smtp_user, recipients, msg.as_string())
        logger.info("Email отправлен: '%s' → %s", subject, recipients)
    except Exception:
        logger.exception("Ошибка отправки email: '%s' → %s", subject, recipients)
