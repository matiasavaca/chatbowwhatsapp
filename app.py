from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

app = Flask(__name__)

# Autenticación con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/credentials.json", scope)
client = gspread.authorize(creds)

viaje_sheet = client.open("chatbot whatsapp").worksheet("Viaje completo")
hoteles_sheet = client.open("chatbot whatsapp").worksheet("Hoteles")
tours_sheet = client.open("chatbot whatsapp").worksheet("tours")

# Sesiones activas
sessions = {}  # phone_number: {"data": row, "last_active": datetime, "state": "menu"}

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip()
    phone_number = request.form.get('From')
    resp = MessagingResponse()
    msg = resp.message()
    lower_msg = incoming_msg.lower()
    now = datetime.now()

    # Limpiar sesiones inactivas
    if phone_number in sessions:
        last_active = sessions[phone_number]["last_active"]
        if now - last_active > timedelta(minutes=5):
            del sessions[phone_number]  # expira sesión

    # Si no hay sesión: pedir usuario
    if phone_number not in sessions:
        username_input = ''.join(lower_msg.lower().split())
        all_records = viaje_sheet.get_all_records()

        for row in all_records:
            usuario = ''.join(str(row.get('usuario', '')).lower().split())
            if username_input == usuario:
                sessions[phone_number] = {
                    "data": row,
                    "last_active": now,
                    "state": "menu"
                }
                nombre = row.get('nombre', '').capitalize()
                msg.body(f"👋 ¡Hola {nombre}! Ya estás identificado.\n\n📋 Escribí `menu` para ver tus opciones.")
                return str(resp)

        msg.body("👤 Por favor escribí tu nombre de usuario para comenzar (sin espacios, ejemplo: `matiasavaca`).")
        return str(resp)

    # Usuario ya identificado
    sessions[phone_number]["last_active"] = now
    user_data = sessions[phone_number]["data"]
    state = sessions[phone_number]["state"]

    if lower_msg in ['menu', 'opciones', 'volver', 'start']:
        sessions[phone_number]["state"] = "menu"
        msg.body("📋 ¿Qué querés consultar?\n1. Vuelo ✈️\n2. Hotel 🏨\n3. Paquete 🎁\n4. Tours 🚌\n\nEscribí el número o palabra clave.")
        return str(resp)

    if state == "menu":
        if lower_msg in ['1', 'vuelo']:
            reply = (f"✈️ Tu vuelo sale el {user_data['fecha salida']} a las {user_data['hora vuelo']} desde {user_data['lugar salida']} "
                     f"con destino a {user_data['lugar de destino']}. Número: {user_data['numero de vuelo']}.\n"
                     f"Llega el {user_data['fecha llegada']} a las {user_data['hora de llegada']}.")
        elif lower_msg in ['2', 'hotel']:
            hotel_nombre = user_data['hotel alojamiento']
            hoteles = hoteles_sheet.get_all_records()
            hotel_info = next((h for h in hoteles if h['Nombre'].lower() == hotel_nombre.lower()), None)
            if hotel_info:
                reply = (f"🏨 Hotel: {hotel_info['Nombre']}\n📍 Dirección: {hotel_info['Direccion']}\n"
                         f"🛏️ Comodidades: {hotel_info['Comodidades']}\n💎 Paquete: {hotel_info['Paquete']}")
            else:
                reply = f"🏨 Hotel asignado: {hotel_nombre} (no encontrado en base de datos)."
        elif lower_msg in ['3', 'paquete']:
            reply = f"🎁 Paquete contratado: {user_data['tipo de paquete']} | Alquiler de auto: {user_data['alquiler de auto']}."
        elif lower_msg in ['4', 'tour', 'tours']:
            paquete = user_data['tipo de paquete'].lower()
            tours = tours_sheet.get_all_records()
            tours_filtrados = [t for t in tours if t['paquete'].lower() == paquete]
            if tours_filtrados:
                reply = "🚌 Tours incluidos:\n"
                for t in tours_filtrados:
                    reply += f"• {t['nombre']}: {t['decripcion']}\n"
            else:
                reply = f"❌ No hay tours asignados al paquete {user_data['tipo de paquete']}."
        else:
            reply = "❓ No entendí tu mensaje. Escribí `menu` para ver las opciones."
        reply += "\n\n🔙 Escribí `volver` para regresar al menú."
        msg.body(reply)
        return str(resp)

    msg.body("❓ No entendí tu mensaje. Escribí `menu` para comenzar de nuevo.")
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
