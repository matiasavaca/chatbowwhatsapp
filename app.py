from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

app = Flask(__name__)

# Google Sheets setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/credentials.json", scope)
client = gspread.authorize(creds)

viaje_sheet = client.open("chatbot whatsapp").worksheet("Viaje completo")
hoteles_sheet = client.open("chatbot whatsapp").worksheet("Hoteles")
tours_sheet = client.open("chatbot whatsapp").worksheet("tours")

# Sesiones temporales
sesiones = {}

# Helper para mostrar menú
def mostrar_menu():
    return ("📋 Elige una opción:\n"
            "1. Hotel 🏨\n"
            "2. Alojamiento 🛏️\n"
            "3. Viajes ✈️\n"
            "4. Paquetes 🧳\n"
            "5. Volver al menú")

# Ruta principal del bot
@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip().lower()
    from_number = request.form.get('From')
    resp = MessagingResponse()
    msg = resp.message()
    now = datetime.now()

    # Verificamos sesión activa
    sesion = sesiones.get(from_number)

    if not sesion or (now - sesion['timestamp']) > timedelta(minutes=5):
        # Iniciar nueva sesión
        sesiones[from_number] = {'estado': 'esperando_usuario', 'timestamp': now}
        reply = "👋 Welcome! Sign in with your *username* to get your trip information:"
        msg.body(reply)
        print(f"➡️ Bot: {reply}")
        return str(resp)

    # Actualizamos tiempo de sesión
    sesiones[from_number]['timestamp'] = now
    estado = sesiones[from_number]['estado']

    if estado == 'esperando_usuario':
        username = incoming_msg
        try:
            data = viaje_sheet.get_all_records()
            user_data = next((row for row in data if row['usuario'].strip().lower() == username), None)
            if not user_data:
                reply = "⚠️ No encontramos tus datos. Asegurate de haber ingresado correctamente tu nombre de usuario."
            else:
                sesiones[from_number]['estado'] = 'menu'
                sesiones[from_number]['usuario'] = username
                sesiones[from_number]['user_data'] = user_data
                reply = "✅ Usuario reconocido.\n\n" + mostrar_menu()
        except Exception as e:
            print(f"❌ Error accediendo al sheet: {e}")
            reply = "❌ Error consultando tu información. Intenta más tarde."

    elif estado == 'menu':
        user_data = sesiones[from_number]['user_data']
        paquete = user_data['tipo de paquete'].strip().lower()

        if incoming_msg == '1':
            hotel = user_data['hotel alojamiento']
            hotel_info = next((h for h in hoteles_sheet.get_all_records() if h['Nombre'].strip().lower() == hotel.strip().lower()), None)
            if hotel_info:
                reply = (f"🏨 *{hotel}*\n"
                         f"📍 Dirección: {hotel_info['Direccion']}\n"
                         f"🛏️ Comodidades: {hotel_info['Comodidades']}\n"
                         f"💎 Paquete: {hotel_info['Paquete']}")
            else:
                reply = f"❌ No se encontró información del hotel {hotel}."

        elif incoming_msg == '2':
            reply = f"🛏️ Tu alojamiento es *{user_data['hotel alojamiento']}*, incluido en el paquete *{user_data['tipo de paquete']}*."

        elif incoming_msg == '3':
            reply = (f"✈️ *Viaje de {user_data['lugar salida']} a {user_data['lugar de destino']}*\n"
                     f"📅 Salida: {user_data['fecha salida']} a las {user_data['hora vuelo']}\n"
                     f"📅 Llegada: {user_data['fecha llegada']} a las {user_data['hora de llegada']}\n"
                     f"🔢 Vuelo: {user_data['numero de vuelo']}")

        elif incoming_msg == '4':
            tours_data = tours_sheet.get_all_records()
            tours_filtrados = [tour for tour in tours_data if tour['paquete'].strip().lower() == paquete]
            if tours_filtrados:
                reply = f"🧳 Estos son tus tours incluidos en el paquete *{paquete.title()}*:\n"
                for tour in tours_filtrados:
                    reply += f"\n🔹 *{tour['nombre']}*\n{tour['decripcion']}"
            else:
                reply = "❌ No se encontraron tours para tu paquete."

        elif incoming_msg == '5':
            reply = mostrar_menu()

        else:
            reply = "❓ Opción inválida. Por favor escribe un número del 1 al 5."

    else:
        reply = "❌ Estado desconocido. Inicia de nuevo escribiendo cualquier mensaje."

    msg.body(reply)
    print(f"➡️ Bot: {reply}")
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "Bot de WhatsApp activo ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
