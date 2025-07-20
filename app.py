from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Inicializar la app Flask
app = Flask(__name__)

# Autenticación con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_url("ChatbotDatos").sheet1  # Cambiar si la hoja tiene otro nombre

# Diccionario de sesión temporal por número de WhatsApp
sessions = {}

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip()
    phone_number = request.form.get('From')  # Ejemplo: 'whatsapp:+54911xxxxxxx'

    resp = MessagingResponse()
    msg = resp.message()
    lower_msg = incoming_msg.lower()

    # Paso 1: Si el número no está en sesión, tomamos el mensaje como nombre y apellido
    if phone_number not in sessions:
        try:
            nombre, apellido = lower_msg.split()
            all_records = sheet.get_all_records()
            for row in all_records:
                if row['nombre'].lower() == nombre and row['apellido'].lower() == apellido:
                    sessions[phone_number] = row
                    msg.body(f"👋 ¡Hola {nombre.capitalize()}! Ya estás identificado. Escribí 'menu' para ver tus opciones.")
                    return str(resp)
            msg.body("❌ No encontré tus datos. Asegurate de escribir tu nombre y apellido tal como figuran.")
            return str(resp)
        except:
            msg.body("✍️ Por favor, escribí tu nombre y apellido (ejemplo: Matias Avaca) para empezar.")
            return str(resp)

    # Paso 2: Usuario identificado, respondemos según el input
    datos = sessions[phone_number]

    if lower_msg in ['menu', 'opciones', 'start']:
        reply = ("📋 ¿Qué querés consultar?\n"
                 "1. Vuelo ✈️\n"
                 "2. Hotel 🏨\n"
                 "3. Paquete 🎁\n"
                 "4. Tours 🚌\n"
                 "Escribí el número o palabra clave.")
    elif lower_msg in ['1', 'vuelo']:
        reply = (f"✈️ Tu vuelo sale el {datos['fecha salida']} a las {datos['hora vuelo']} desde {datos['lugar salida']} "
                 f"hacia {datos['lugar de destino']}. Número de vuelo: {datos['numero de vuelo']}.\n"
                 f"Llega el {datos['fecha llegada']} a las {datos['hora de llegada']}.")
    elif lower_msg in ['2', 'hotel']:
        reply = f"🏨 Tu hotel es: {datos['hotel alojamiento']}."
    elif lower_msg in ['3', 'paquete']:
        reply = f"🎁 Paquete contratado: {datos['tipo de paquete']} | Alquiler de auto: {datos['alquiler de auto']}."
    elif lower_msg in ['4', 'tour', 'tours']:
        reply = f"🚌 Tours contratados: {datos['tours contratados']}."
    else:
        reply = "❓ No entendí tu mensaje. Escribí 'menu' para ver las opciones disponibles."

    msg.body(reply)
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
