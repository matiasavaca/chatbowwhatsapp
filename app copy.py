from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Diccionario para guardar sesiones (por número de teléfono)
sessions = {}

# Opciones del menú
opciones = {
    '1': 'Hotel 🏨',
    '2': 'Alojamiento 🛏️',
    '3': 'Viajes ✈️',
    '4': 'Paquetes 🧳'
}

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip().lower()
    phone_number = request.form.get('From')
    print(f"📥 Mensaje de {phone_number}: '{incoming_msg}'")

    resp = MessagingResponse()
    msg = resp.message()

    estado_actual = sessions.get(phone_number, {}).get("estado", "")

    # Si el estado es esperando una opción y el mensaje es válido
    if estado_actual == "esperando_opcion" and incoming_msg in opciones:
        seleccion = opciones[incoming_msg]
        reply = f"✅ Has seleccionado: {seleccion}"
        sessions[phone_number] = {}  # Reseteamos sesión
    else:
        reply = ("👋 Welcome! Please choose an option:\n"
                 "1. Hotel 🏨\n"
                 "2. Alojamiento 🛏️\n"
                 "3. Viajes ✈️\n"
                 "4. Paquetes 🧳")
        sessions[phone_number] = {"estado": "esperando_opcion"}

    print("✅ Enviando respuesta")
    msg.body(reply)
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "Bot de WhatsApp activo ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
