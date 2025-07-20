from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Flask app
app = Flask(__name__)

# Google Sheets auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("ChatbotDatos").sheet1  # cambia por el nombre de tu hoja

# Sesiones por número de WhatsApp
sessions = {}

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip()
    phone_number = request.form.get('From')  # formato: whatsapp:+54911...
    resp = MessagingResponse()
    msg = resp.message()

    lower_msg = incoming_msg.lower()

    # Paso 1: Si no está identificado, asumimos que está enviando "nombre apellido"
    if phone_number not in sessions:
        try:
            nombre, apellido = incoming_msg.strip().lower().split()
            all_records = sheet.get_all_records()
            for row in all_records:
                if row['nombre'].lower() == nombre and row['apellido'].lower() == apellido:
                    sessions[phone_number] = row
                    msg.body(f"Hola {nombre.capitalize()}! Ya estás identificado. Escribí 'menu' para ver opciones.")
                    return str(resp)
            msg.body("❌ Nombre y apellido no encontrados. Intentalo de nuevo.")
            return str(resp)
        except:
            msg.body("Por favor, enviá tu nombre y apellido (ej: Matias Avaca) para empezar.")
            return str(resp)

    # Ya está identificado
    datos_usuario = sessions[phone_number]

    if lower_msg in ['menu', 'start', 'opciones']:
        reply = ("👋 ¿Qué información querés ver?\n"
                 "1. Hotel 🏨\n"
                 "2. Paquete 🎁\n"
                 "3. Vuelo ✈️\n"
                 "4. Tours 🚌\n"
                 "Escribí el número o palabra.")
    elif lower_msg in ['1', 'hotel']:
        reply = f"Tu hotel asignado es: {datos_usuario['hotel alojamiento']}."
    elif lower_msg in ['2', 'paquete']:
        reply = f"Tu paquete es: {datos_usuario['tipo de paquete']}."
    elif lower_msg in ['3', 'vuelo']:
        reply = (f"Tu vuelo sale el {datos_usuario['fecha salida']} a las {datos_usuario['hora vuelo']}, "
                 f"desde {datos_usuario['lugar salida']} hacia {datos_usuario['lugar de destino']}. "
                 f"Número de vuelo: {datos_usuario['numero de vuelo']}")
    elif lower_msg in ['4', 'tour', 'tours']:
        reply = f"Tours contratados: {datos_usuario['tours contratados']}"
    else:
        reply = "No entendí tu mensaje. Escribí 'menu' para ver opciones disponibles."

    msg.body(reply)
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
