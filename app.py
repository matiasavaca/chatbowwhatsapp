from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ['hi', 'hello', 'hola', 'start', 'menu']:
        reply = ("👋 Welcome! Please choose an option:\n"
                 "1. Hotel 🏨\n"
                 "2. Alojamiento 🛏️\n"
                 "3. Viajes ✈️\n"
                 "4. Paquetes 🧳")
    elif incoming_msg == '1':
        reply = "You selected Hotel 🏨. Please tell us your destination."
    elif incoming_msg == '2':
        reply = "You selected Alojamiento 🛏️. Let us know your preferred location."
    elif incoming_msg == '3':
        reply = "You selected Viajes ✈️. What type of trip are you planning?"
    elif incoming_msg == '4':
        reply = "You selected Paquetes 🧳. Do you want domestic or international?"
    else:
        reply = "Sorry, I didn't understand. Please type 'menu' to see the options."

    msg.body(reply)
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
