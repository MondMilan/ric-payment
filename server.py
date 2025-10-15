# server.py - semplice server Flask per creare Checkout + generare QR e ricevere webhook
import os, csv, io
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file, abort, redirect, url_for
import stripe
import qrcode
from dotenv import load_dotenv

load_dotenv()  # legge .env

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
DOMAIN = os.getenv("DOMAIN", "http://localhost:4242")
CLIENTS_CSV = r"C:\ric-display\clients.csv"


if not STRIPE_SECRET_KEY:
    raise RuntimeError("Devi impostare STRIPE_SECRET_KEY nella .env")

stripe.api_key = STRIPE_SECRET_KEY

app = Flask(__name__)

# utilità CSV (uid;numero_cliente;porta;scadenza)
def read_clients():
    d = {}
    if not os.path.isfile(CLIENTS_CSV):
        return d
    with open(CLIENTS_CSV, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            parts = [p.strip() for p in line.split(";")]
            uid = parts[0]
            d[uid] = {
                "numero_cliente": parts[1] if len(parts)>1 else "-",
                "porta": parts[2] if len(parts)>2 else "-",
                "scadenza": parts[3] if len(parts)>3 else "-"
            }
    return d

def write_clients(d):
    with open(CLIENTS_CSV, "w", encoding="utf-8") as f:
        for uid, info in d.items():
            f.write(f"{uid};{info.get('numero_cliente','-')};{info.get('porta','-')};{info.get('scadenza','-')}\n")

def set_expiry_for_uid(uid, months):
    """aggiorna clients.csv, aggiungendo months alla scadenza attuale (se presente) o da oggi"""
    clients = read_clients()
    today = datetime.now().date()
    current = clients.get(uid, {}).get("scadenza","")
    try:
        if current and current != "-" :
            cur_date = datetime.strptime(current, "%d/%m/%Y").date()
            base = cur_date if cur_date > today else today
        else:
            base = today
    except Exception:
        base = today
    # aggiungi mesi in modo semplice (approssimazione: 30 giorni * months) oppure usa relativedelta
    new_date = base + timedelta(days=30*int(months))
    new_str = new_date.strftime("%d/%m/%Y")
    if uid not in clients:
        clients[uid] = {"numero_cliente":"-","porta":"-","scadenza":new_str}
    else:
        clients[uid]["scadenza"] = new_str
    write_clients(clients)
    return new_str

# Endpoint per creare una Checkout session e restituire il QR image
@app.route("/create_checkout", methods=["GET"])
def create_checkout():
    uid = request.args.get("uid")
    months = request.args.get("months", "1")
    price_cents = int(request.args.get("price_cents", "1000"))  # es: 1000 = €10.00
    currency = request.args.get("currency", "eur")

    if not uid:
        return jsonify({"error":"missing uid"}), 400

    # crea sessione checkout con metadata (salviamo uid/months per il webhook)
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "product_data": {"name": f"Rinnovo abbonamento {months} mese/i"},
                    "unit_amount": price_cents,
                },
                "quantity": 1
            }],
            mode="payment",
            success_url=DOMAIN + "/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=DOMAIN + "/cancel",
            metadata={"uid": uid, "months": months}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Genera QR per session.url
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(session.url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)

    # opzionale: salva l'url/sessionid in file di log locale
    with open("last_checkout.log", "w", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} uid={uid} months={months} session={session.id} url={session.url}\n")

    # ritorna immagine PNG del QR
    return send_file(bio, mimetype="image/png")

# success/cancel pages minimal (puoi personalizzare)
@app.route("/success")
def success():
    return "<h2>Pagamento ricevuto! Grazie.</h2>"

@app.route("/cancel")
def cancel():
    return "<h2>Pagamento annullato.</h2>"

# Webhook Stripe: riceve gli eventi e aggiorna clients.csv
@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # invalid payload
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400

    # gestisci eventi
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        uid = metadata.get("uid")
        months = metadata.get("months", "1")
        # aggiorna scadenza
        if uid:
            newdate = set_expiry_for_uid(uid, months)
            # puoi loggare o inviare notifica
            with open("payments.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} PAID uid={uid} months={months} new_expiry={newdate}\n")
    return "", 200

if __name__ == "__main__":
    # Attenzione: in produzione esegui con gunicorn/uwsgi e HTTPS
    app.run(host="0.0.0.0", port=4242, debug=True)

