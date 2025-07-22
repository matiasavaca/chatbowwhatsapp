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

# Cargar hojas
viaje_sheet = client.open("chatbot whatsapp").worksheet("Viaje completo")
hoteles_sheet = client.open("chatbot whatsapp").worksheet("Hoteles")
tours_sheet = client.open("chatbot whatsapp").worksheet("tours")

# Guardar sesiones activas (timestamp)
sesiones = {}
TIMEOUT = 300  # 5 minutos en segundos

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    resp = MessagingResponse()
    msg = resp.message()

    try:
        incoming_msg = request.form.get('Body', '').strip().lower()
        from_number = request.form.get('From')
        username = from_number.split(":")[-1].lower()
        print(f"\n📩 Mensaje de {username}: '{incoming_msg}'")

        # Resetear sesión si pasaron más de 5 minutos
        now = time.time()
        if from_number in sesiones and now - sesiones[from_number] > TIMEOUT:
            print("🕒 Sesión expirada, reiniciando...")
            del sesiones[from_number]

        sesiones[from_number] = now  # Actualiza o crea timestamp de sesión

        if incoming_msg not in ['1', '2', '3', '4']:
            reply = ("👋 Welcome! Please choose an option:\n"
                     "1. Hotel \U0001F3E8\n"
                     "2. Alojamiento \U0001F6CF\uFE0F\n"
                     "3. Viajes \u2708\uFE0F\n"
                     "4. Paquetes \U0001F9F3")
            msg.body(reply)
            return str(resp)

        # Buscar al usuario en la hoja
        data = viaje_sheet.get_all_records()
        user_row = next((row for row in data if row['usuario'].strip().lower() == username), None)

        if not user_row:
            msg.body("⚠️ No encontramos tus datos. Asegurate de haber ingresado correctamente tu usuario.")
            return str(resp)

        paquete = user_row['tipo de paquete'].strip().lower()

        if incoming_msg == '1':
            hotel = user_row['hotel alojamiento']
            hotel_data = hoteles_sheet.get_all_records()
            hotel_info = next((h for h in hotel_data if h['Nombre'].strip().lower() == hotel.strip().lower()), None)
            if hotel_info:
                reply = (
                    f"\U0001F3E8 *{hotel}*\n"
                    f"\U0001F4CD Dirección: {hotel_info['Direccion']}\n"
                    f"\U0001F6CF\uFE0F Comodidades: {hotel_info['Comodidades']}\n"
                    f"\U0001F48E Paquete: {hotel_info['Paquete']}"
                )
            else:
                reply = f"⚠️ No se encontró información del hotel *{hotel}*."

        elif incoming_msg == '2':
            reply = f"\U0001F6CF\uFE0F Tu alojamiento es en *{user_row['hotel alojamiento']}*, incluido en el paquete *{user_row['tipo de paquete']}*."

        elif incoming_msg == '3':
            reply = (
                f"\u2708\uFE0F *Tu viaje desde {user_row['lugar salida']} a {user_row['lugar de destino']}*\n"
                f"\U0001F4C5 Salida: {user_row['fecha salida']} a las {user_row['hora vuelo']}\n"
                f"\U0001F4C5 Llegada: {user_row['fecha llegada']} a las {user_row['hora de llegada']}\n"
                f"\U0001F522 Número de vuelo: {user_row['numero de vuelo']}"
            )

        elif incoming_msg == '4':
            tours_data = tours_sheet.get_all_records()
            tours_filtrados = [tour for tour in tours_data if tour['paquete'].strip().lower() == paquete]
            if tours_filtrados:
                reply = f"\U0001F9F3 Estos son tus tours incluidos en el paquete *{paquete.title()}*:\n"
                for tour in tours_filtrados:
                    reply += f"\n\u2728 *{tour['nombre']}*\n{tour['decripcion']}\n"
            else:
                reply = "⚠️ No se encontraron tours para tu paquete."

        print(f"\u2709\uFE0F Respuesta enviada a {username}:\n{reply}\n")
        msg.body(reply)

    except Exception as e:
        print(f"❌ Error: {e}")
        msg.body("⚠️ Ocurrió un error procesando tu solicitud. Intenta más tarde.")

    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "Bot de WhatsApp activo ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
