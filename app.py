from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re, time

app = Flask(__name__)

# Configurar conexión con Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/credentials.json", scope)
client = gspread.authorize(creds)

# Conectar a las hojas
viaje_sheet = client.open("chatbot whatsapp").worksheet("Viaje completo")
hoteles_sheet = client.open("chatbot whatsapp").worksheet("Hoteles")
tours_sheet = client.open("chatbot whatsapp").worksheet("tours")

# Sesiones temporales de usuarios (se resetean tras 5 minutos)
sessions = {}
SESSION_TIMEOUT = 300  # 5 minutos

# Opciones del menú
menu_opciones = (
    "📋 Elige una opción:\n"
    "1. Hotel 🏨\n"
    "2. Alojamiento 🛏️\n"
    "3. Viajes ✈️\n"
    "4. Paquetes 🧳"
)

def clean_text(text):
    """Elimina caracteres invisibles o no compatibles con WhatsApp"""
    return re.sub(r'[^\x00-\x7F¡-ÿ€£¥₿…–—‘’“”•™°±©®¶§†‡¤]', '', text)

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip()
    phone = request.form.get('From')
    username = phone.split(":")[-1].lower()
    now = time.time()

    # Verificamos si hay sesión activa y no expiró
    session = sessions.get(phone)
    if session and now - session.get('last_active', 0) > SESSION_TIMEOUT:
        print(f"⏰ Sesión expirada para {phone}")
        sessions.pop(phone)

    resp = MessagingResponse()
    msg = resp.message()

    # Si no hay sesión, pedimos username
    if not session:
        sessions[phone] = {'estado': 'esperando_username', 'last_active': now}
        reply = "👋 Welcome! Sign in with your *username* to get your trip information:"
        print(f"➡️ Bot: {reply}")
        msg.body(clean_text(reply))
        return str(resp)

    estado = session.get('estado')
    print(f"📨 {username} escribió: '{incoming_msg}' | Estado: {estado}")

    # Validar nombre de usuario
    if estado == 'esperando_username':
        try:
            data = viaje_sheet.get_all_records()
            user_row = next((row for row in data if row['usuario'].strip().lower() == incoming_msg.strip().lower()), None)
            if user_row:
                sessions[phone] = {
                    'estado': 'menu_principal',
                    'last_active': now,
                    'user_data': user_row
                }
                reply = f"✅ Usuario reconocido.\n{menu_opciones}"
            else:
                reply = "⚠️ No encontramos tus datos. Asegurate de haber ingresado correctamente tu usuario."
        except Exception as e:
            print(f"❌ Error buscando usuario: {e}")
            reply = "❌ Error consultando el sistema. Intenta más tarde."
        print(f"➡️ Bot: {reply}")
        msg.body(clean_text(reply))
        return str(resp)

    # Ya logueado → opciones 1 a 5
    user_data = session.get('user_data')
    paquete = user_data.get('tipo de paquete', '').strip().lower()
    reply = ""

    if incoming_msg == '5':
        sessions[phone]['estado'] = 'menu_principal'
        reply = menu_opciones
    elif incoming_msg == '1':
        hotel = user_data.get('hotel alojamiento', '')
        try:
            hotel_data = hoteles_sheet.get_all_records()
            hotel_info = next((h for h in hotel_data if h['Nombre'].strip().lower() == hotel.strip().lower()), None)
            if hotel_info:
                reply = (f"🏨 *{hotel_info['Nombre']}*\n"
                         f"📍 Dirección: {hotel_info['Direccion']}\n"
                         f"🛏️ Comodidades: {hotel_info['Comodidades']}\n"
                         f"💎 Paquete: {hotel_info['Paquete']}\n"
                         f"↩️ Escribe *5* para volver al menú principal.")
            else:
                reply = f"No se encontró información del hotel {hotel}.\n↩️ Escribe *5* para volver al menú principal."
        except Exception as e:
            print(f"❌ Error con hotel: {e}")
            reply = "❌ Error consultando hotel."
    elif incoming_msg == '2':
        reply = (f"🏨 Tu alojamiento es en: {user_data['hotel alojamiento']} "
                 f"(paquete {user_data['tipo de paquete']})\n"
                 f"↩️ Escribe *5* para volver al menú principal.")
    elif incoming_msg == '3':
        reply = (f"✈️ *Viaje de {user_data['lugar salida']} a {user_data['lugar de destino']}*\n"
                 f"📅 Salida: {user_data['fecha salida']} a las {user_data['hora vuelo']}\n"
                 f"📅 Llegada: {user_data['fecha llegada']} a las {user_data['hora de llegada']}\n"
                 f"🔢 Vuelo: {user_data['numero de vuelo']}\n"
                 f"↩️ Escribe *5* para volver al menú principal.")
    elif incoming_msg == '4':
        try:
            tours_data = tours_sheet.get_all_records()
            tours_filtrados = [t for t in tours_data if t['paquete'].strip().lower() == paquete]
            if tours_filtrados:
                reply = f"🧳 Tus tours del paquete *{paquete.title()}*:\n"
                for t in tours_filtrados:
                    reply += f"\n🔹 *{t['nombre']}*\n{t['decripcion']}"
            else:
                reply = "No se encontraron tours para tu paquete."
            reply += "\n↩️ Escribe *5* para volver al menú principal."
        except Exception as e:
            print(f"❌ Error con tours: {e}")
            reply = "❌ Error consultando tours."
    else:
        reply = "❓ Opción inválida. Por favor escribe un número del 1 al 5."

    # Actualizar timestamp de la sesión
    sessions[phone]['last_active'] = now
    print(f"➡️ Bot: {reply}")
    msg.body(clean_text(reply))
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "✅ WhatsApp Bot activo.", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
