from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

app = Flask(__name__)

# Conectar a Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/credentials.json", scope)
client = gspread.authorize(creds)

viaje_sheet = client.open("chatbot whatsapp").worksheet("Viaje completo")
hoteles_sheet = client.open("chatbot whatsapp").worksheet("Hoteles")
tours_sheet = client.open("chatbot whatsapp").worksheet("tours")

# Guardar sesiones y tiempos
sesiones = {}
TIEMPO_EXPIRACION = 300  # 5 minutos

def menu_principal():
    return ("📋 Elige una opción:\n"
            "1. Hotel 🏨\n"
            "2. Alojamiento 🛏️\n"
            "3. Viajes ✈️\n"
            "4. Paquetes 🧳")

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip()
    phone = request.form.get('From')
    resp = MessagingResponse()
    msg = resp.message()

    ahora = time.time()
    sesion = sesiones.get(phone, {'estado': 'esperando_username', 'timestamp': ahora})

    # Expirar sesión tras 5 minutos
    if ahora - sesion.get('timestamp', 0) > TIEMPO_EXPIRACION:
        print(f"⏱️ Timeout para {phone}. Reseteando sesión.")
        sesion = {'estado': 'esperando_username', 'timestamp': ahora}

    sesion['timestamp'] = ahora
    estado = sesion['estado']
    print(f"[Mensaje] {phone} escribió: '{incoming_msg}' | Estado: {estado}")

    # Etapa 1: esperando username
    if estado == 'esperando_username':
        username = incoming_msg.lower()
        data = viaje_sheet.get_all_records()
        user_row = next((row for row in data if row['usuario'].strip().lower() == username), None)

        if user_row:
            sesion['estado'] = 'menu_principal'
            sesion['usuario'] = username
            msg.body("✅ Usuario reconocido.\n" + menu_principal())
        else:
            msg.body("⚠️ Usuario no encontrado. Intenta nuevamente.")
        sesiones[phone] = sesion
        return str(resp)

    # Etapa 2: menú principal
    if estado == 'menu_principal':
        if incoming_msg == '1':
            user_data = viaje_sheet.get_all_records()
            row = next((row for row in user_data if row['usuario'].strip().lower() == sesion['usuario']), None)
            if row:
                hotel_nombre = row['hotel alojamiento']
                hotel_data = hoteles_sheet.get_all_records()
                hotel_info = next((h for h in hotel_data if h['Nombre'].strip().lower() == hotel_nombre.strip().lower()), None)
                if hotel_info:
                    reply = (f"🏨 *{hotel_info['Nombre']}*\n"
                             f"📍 Dirección: {hotel_info['Direccion']}\n"
                             f"🛏️ Comodidades: {hotel_info['Comodidades']}\n"
                             f"💎 Paquete: {hotel_info['Paquete']}\n"
                             "↩️ Escribe *5* para volver al menú principal.")
                else:
                    reply = "❌ No se encontró información del hotel.\n↩️ Escribe *5* para volver al menú principal."
                msg.body(reply)
                return str(resp)

        elif incoming_msg == '2':
            user_data = viaje_sheet.get_all_records()
            row = next((row for row in user_data if row['usuario'].strip().lower() == sesion['usuario']), None)
            if row:
                alojamiento = row['hotel alojamiento']
                paquete = row['tipo de paquete']
                reply = (f"🛏️ Tu alojamiento es en: *{alojamiento}*\n"
                         f"💼 Incluido en el paquete *{paquete}*\n"
                         "↩️ Escribe *5* para volver al menú principal.")
                msg.body(reply)
                return str(resp)

        elif incoming_msg == '3':
            user_data = viaje_sheet.get_all_records()
            row = next((row for row in user_data if row['usuario'].strip().lower() == sesion['usuario']), None)
            if row:
                reply = (f"✈️ *Viaje de {row['lugar salida']} a {row['lugar de destino']}*\n"
                         f"📅 Salida: {row['fecha salida']} a las {row['hora vuelo']}\n"
                         f"📅 Llegada: {row['fecha llegada']} a las {row['hora de llegada']}\n"
                         f"🔢 Vuelo: {row['numero de vuelo']}\n"
                         "↩️ Escribe *5* para volver al menú principal.")
                msg.body(reply)
                return str(resp)

        elif incoming_msg == '4':
            user_data = viaje_sheet.get_all_records()
            row = next((row for row in user_data if row['usuario'].strip().lower() == sesion['usuario']), None)
            if row:
                paquete = row['tipo de paquete'].strip().lower()
                tours_data = tours_sheet.get_all_records()
                tours_filtrados = [tour for tour in tours_data if tour.get('paquete', '').strip().lower() == paquete]
                if tours_filtrados:
                    reply = f"🧳 Tus tours del paquete *{paquete.title()}*:"
                    for tour in tours_filtrados:
                        reply += f"\n\n🔹 *{tour['nombre']}*\n{tour['decripcion']}"
                    reply += "\n↩️ Escribe *5* para volver al menú principal."
                else:
                    reply = "❌ No se encontraron tours para tu paquete.\n↩️ Escribe *5* para volver al menú principal."
                msg.body(reply)
                return str(resp)

        elif incoming_msg == '5':
            msg.body(menu_principal())
            return str(resp)

        else:
            msg.body("❓ Opción inválida. Por favor escribe un número del 1 al 5.")
            return str(resp)

    # Fallback si está esperando username pero no lo escribió correctamente
    if estado == 'esperando_username':
        msg.body("👋 Welcome! Sign in with your *username* to get your trip information:")
        sesiones[phone] = {'estado': 'esperando_username', 'timestamp': ahora}
        return str(resp)

    # Fallback general
    msg.body("👋 Welcome! Sign in with your *username* to get your trip information:")
    sesiones[phone] = {'estado': 'esperando_username', 'timestamp': ahora}
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "✅ Bot de WhatsApp activo", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
