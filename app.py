from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Conectar a Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/credentials.json", scope)
client = gspread.authorize(creds)

viaje_sheet = client.open("chatbot whatsapp").worksheet("Viaje completo")
hoteles_sheet = client.open("chatbot whatsapp").worksheet("Hoteles")
tours_sheet = client.open("chatbot whatsapp").worksheet("tours")

# Guardar usuarios ya saludados
usuarios_saludados = {}

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip().lower()
    from_number = request.form.get('From')
    resp = MessagingResponse()
    msg = resp.message()

    username = from_number.split(":")[-1].lower()

    print(f"📩 Mensaje de {username}: {incoming_msg}")

    # Mostrar siempre el menú si no es número del 1 al 4
    if incoming_msg not in ['1', '2', '3', '4']:
        reply = ("👋 Welcome! Please choose an option:\n"
                 "1. Hotel 🏨\n"
                 "2. Alojamiento 🛏️\n"
                 "3. Viajes ✈️\n"
                 "4. Paquetes 🧳")
        msg.body(reply)
        return str(resp)

    # Buscar datos del usuario en el sheet
    try:
        data = viaje_sheet.get_all_records()
        user_row = next((row for row in data if row['usuario'].strip().lower() == username), None)

        if not user_row:
            msg.body("⚠️ No encontramos tus datos. Por favor asegurate de haber ingresado correctamente tu nombre de usuario.")
            return str(resp)

        paquete = user_row['tipo de paquete'].strip().lower()

        if incoming_msg == '1':
            hotel = user_row['hotel alojamiento']
            hotel_data = hoteles_sheet.get_all_records()
            hotel_info = next((h for h in hotel_data if h['Nombre'].strip().lower() == hotel.strip().lower()), None)
            if hotel_info:
                reply = f"🏨 *{hotel}*\n📍 Dirección: {hotel_info['Direccion']}\n🛏️ Comodidades: {hotel_info['Comodidades']}\n💎 Paquete: {hotel_info['Paquete']}"
            else:
                reply = f"No se encontró información del hotel {hotel}."
        elif incoming_msg == '2':
            reply = f"🏨 Tu alojamiento es en: {user_row['hotel alojamiento']}, incluido en el paquete {user_row['tipo de paquete']}"
        elif incoming_msg == '3':
            reply = (f"✈️ *Viaje de {user_row['lugar salida']} a {user_row['lugar de destino']}*\n"
                     f"📅 Salida: {user_row['fecha salida']} a las {user_row['hora vuelo']}\n"
                     f"📅 Llegada: {user_row['fecha llegada']} a las {user_row['hora de llegada']}\n"
                     f"🔢 Vuelo: {user_row['numero de vuelo']}")
        elif incoming_msg == '4':
            tours_data = tours_sheet.get_all_records()
            paquete = user_row['tipo de paquete'].strip().lower()
            tours_filtrados = [tour for tour in tours_data if tour['paquete'].strip().lower() == paquete]
            if tours_filtrados:
                reply = f"🧳 Estos son tus tours incluidos en el paquete *{paquete.title()}*:\n"
                for tour in tours_filtrados:
                    reply += f"\n🔹 *{tour['nombre']}*\n{tour['decripcion']}\n"
            else:
                reply = "No se encontraron tours para tu paquete."

    except Exception as e:
        print(f"❌ Error: {e}")
        reply = "Ocurrió un error consultando tu información. Intenta más tarde."

    msg.body(reply)
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "Bot de WhatsApp activo ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
