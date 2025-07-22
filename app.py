from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import unicodedata
import time

app = Flask(__name__)

# Autenticación con Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/credentials.json", scope)
client = gspread.authorize(creds)

# Acceso a las hojas de cálculo
viaje_sheet = client.open("chatbot whatsapp").worksheet("Viaje completo")
hoteles_sheet = client.open("chatbot whatsapp").worksheet("Hoteles")
tours_sheet = client.open("chatbot whatsapp").worksheet("tours")

# Estado de sesiones
sesiones = {}  # phone_number -> {'estado': ..., 'username': ..., 'last_active': ...}
TIMEOUT = 300  # 5 minutos

# Opciones del menú principal
menu_texto = ("\n\ud83d\udccb Elige una opción:\n"
               "1. Hotel \ud83c\udfe8\n"
               "2. Alojamiento \ud83d\udccf\n"
               "3. Viajes \u2708\ufe0f\n"
               "4. Paquetes \ud83d\ude93")

# Limpieza de texto

def clean_text(text):
    normalized = unicodedata.normalize('NFKD', text)
    cleaned = ''.join(c for c in normalized if c.isprintable() and not unicodedata.category(c).startswith('C'))
    return cleaned.strip()

# Ruta principal del bot
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip()
    phone = request.form.get('From')
    lower_msg = incoming_msg.lower()

    resp = MessagingResponse()
    msg = resp.message()

    now = time.time()
    sesion = sesiones.get(phone, {'estado': 'esperando_username'})

    # Reset por timeout
    if now - sesion.get('last_active', 0) > TIMEOUT:
        print(f"\u23f1\ufe0f Timeout para {phone}. Reseteando sesión.")
        sesion = {'estado': 'esperando_username'}

    sesion['last_active'] = now

    print(f"\ud83d\udcec {phone} escribió: '{incoming_msg}' | Estado: {sesion['estado']}")

    if sesion['estado'] == 'esperando_username':
        try:
            data = viaje_sheet.get_all_records()
            user_row = next((row for row in data if row['usuario'].strip().lower() == lower_msg), None)
            if user_row:
                sesion['estado'] = 'menu_principal'
                sesion['username'] = lower_msg
                sesiones[phone] = sesion
                reply = f"\u2705 Usuario reconocido.{menu_texto}"
            else:
                reply = "\u26a0\ufe0f No encontramos tus datos. Asegurate de haber ingresado correctamente tu *username*."
        except Exception as e:
            print("\u274c Error accediendo a Sheets:", e)
            reply = "\u274c Error consultando tus datos. Intenta más tarde."

    elif sesion['estado'] == 'menu_principal':
        username = sesion.get('username')
        data = viaje_sheet.get_all_records()
        user_row = next((row for row in data if row['usuario'].strip().lower() == username), None)
        if not user_row:
            reply = "\u274c No encontramos tu información. Por favor, reinicia escribiendo tu username."
            sesion['estado'] = 'esperando_username'
        elif lower_msg == '1':
            hotel = user_row['hotel alojamiento']
            hotel_data = hoteles_sheet.get_all_records()
            hotel_info = next((h for h in hotel_data if h['Nombre'].strip().lower() == hotel.strip().lower()), None)
            if hotel_info:
                reply = f"\ud83c\udfe8 *{hotel}*\n\ud83d\udccd Dirección: {hotel_info['Direccion']}\n\ud83d\udccf Comodidades: {hotel_info['Comodidades']}\n\ud83d\udc8e Paquete: {hotel_info['Paquete']}\n\u21a9\ufe0f Escribe *5* para volver al menú principal."
            else:
                reply = f"No se encontró información del hotel {hotel}.\n\u21a9\ufe0f Escribe *5* para volver al menú."
        elif lower_msg == '2':
            reply = f"\ud83c\udfe8 Tu alojamiento es en: *{user_row['hotel alojamiento']}*, incluido en el paquete *{user_row['tipo de paquete']}*\n\u21a9\ufe0f Escribe *5* para volver al menú."
        elif lower_msg == '3':
            reply = (f"\u2708\ufe0f *Viaje de {user_row['lugar salida']} a {user_row['lugar de destino']}*\n"
                     f"\ud83d\uddd3 Salida: {user_row['fecha salida']} a las {user_row['hora vuelo']}\n"
                     f"\ud83d\uddd3 Llegada: {user_row['fecha llegada']} a las {user_row['hora de llegada']}\n"
                     f"\ud83d\udd39 Vuelo: {user_row['numero de vuelo']}\n\u21a9\ufe0f Escribe *5* para volver al menú.")
        elif lower_msg == '4':
            paquete = user_row['tipo de paquete'].strip().lower()
            tours_data = tours_sheet.get_all_records()
            tours_filtrados = [tour for tour in tours_data if tour.get('paquete', '').strip().lower() == paquete]
            if tours_filtrados:
                reply = f"\ud83d\ude93 Tus tours del paquete *{paquete.title()}*:\n"
                for tour in tours_filtrados:
                    reply += f"\n\ud83d\udd39 *{tour['nombre']}*\n{tour['decripcion']}"
                reply += "\n\u21a9\ufe0f Escribe *5* para volver al menú principal."
            else:
                reply = "No se encontraron tours para tu paquete.\n\u21a9\ufe0f Escribe *5* para volver."
        elif lower_msg == '5':
            reply = menu_texto
        else:
            reply = "\u2753 Opción inválida. Por favor escribe un número del 1 al 5."
    else:
        sesion['estado'] = 'esperando_username'
        reply = "\ud83d\udc4b Welcome! Sign in with your *username* to get your trip information:"

    sesiones[phone] = sesion
    msg.body(clean_text(reply))
    print(f"\u27a1\ufe0f Bot: {reply}")
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "Bot de WhatsApp activo ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
