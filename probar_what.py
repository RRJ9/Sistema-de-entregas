from twilio.rest import Client
import os

# Opcional: cargar variables desde un archivo .env
from dotenv import load_dotenv
load_dotenv()

# 🚨 Asegúrate de tener estas variables en tu entorno o en un archivo .env
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
from_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")  # Ej: whatsapp:+14155238886

# 📞 Número destino (ya debe estar unido al sandbox si estás en modo prueba)
to_whatsapp_number = "whatsapp:+5216563063195"  # ← Cambia por el número que quieres probar

# ✉️ Mensaje a enviar
mensaje = "✅ Prueba de envío desde script Python con Twilio y WhatsApp."

# Inicializa el cliente
client = Client(account_sid, auth_token)

# Envío
try:
    message = client.messages.create(
        body=mensaje,
        from_=from_whatsapp_number,
        to=to_whatsapp_number
    )
    print("✅ Mensaje enviado con éxito. SID:", message.sid)
except Exception as e:
    print("❌ Error al enviar mensaje:", str(e))