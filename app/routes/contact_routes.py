import os

from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint

from app.utils.require_api_key import require_api_key
from app.utils.send_email import send_email

contact_bp = Blueprint(
    "contact",
    "contact",
    url_prefix="/contact",
)

GMAIL_TO = os.getenv("GMAIL_TO", "alenz@uneb.br")


@contact_bp.route("")
class Contact(MethodView):
    decorators = [require_api_key]

    @contact_bp.response(200)
    def post(self):
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        message = (data.get("message") or "").strip()
        subject = (data.get("subject") or "").lower().strip()

        if not name or not email or not message or not subject:
            return {"error": "Preencha todos os campos."}, 400

        try:
            send_email(
                subject=f"[LUMM] Contato - {subject.title()} - {name}",
                body=f"Nome: {name}\nAssunto: {subject}\nEmail: {email}\n\nMensagem:\n{message}\n",
                to=GMAIL_TO,
                reply_to=email,
            )
            return {"ok": True}
        except Exception as e:
            return {"error": "Falha ao enviar email", "detail": str(e)}, 500
