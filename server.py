# -*- coding: utf-8 -*-
"""
AG GYM - Rinnovi online soci ASD

Questo server crea pagamenti Stripe SOLO per rinnovi di soci già registrati.
Nuove iscrizioni, tesseramento iniziale e ingresso giornaliero restano SOLO in presenza.

URL esempio:
https://TUO-SITO.onrender.com/rinnovo?badge=54000422DDAF&name=PROVA%20PAGAMENTO
"""

import os
import re
from datetime import datetime
from flask import Flask, request, redirect, render_template_string, abort
from markupsafe import escape
import stripe

app = Flask(__name__)

# ---------------- CONFIG ----------------

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
BASE_URL = os.environ.get("BASE_URL", "").strip().rstrip("/")

if not STRIPE_SECRET_KEY:
    print("ATTENZIONE: manca STRIPE_SECRET_KEY nelle variabili ambiente.")

if not BASE_URL:
    print("ATTENZIONE: manca BASE_URL nelle variabili ambiente.")

stripe.api_key = STRIPE_SECRET_KEY

GYM_NAME = "AG GYM"
PHONE_1 = "340 705 4473"
PHONE_2 = "379 147 9280"

# SOLO RINNOVI
PLANS = {
    "1m": {
        "title": "Rinnovo 1 mese",
        "months": 1,
        "amount_cents": 4500,
        "price_text": "45€",
        "description": "Rinnovo abbonamento sala pesi per 1 mese",
    },
    "3m": {
        "title": "Rinnovo 3 mesi",
        "months": 3,
        "amount_cents": 12000,
        "price_text": "120€",
        "description": "Rinnovo abbonamento sala pesi per 3 mesi",
    },
    "6m": {
        "title": "Rinnovo 6 mesi",
        "months": 6,
        "amount_cents": 21000,
        "price_text": "210€",
        "description": "Rinnovo abbonamento sala pesi per 6 mesi",
    },
    "12m": {
        "title": "Rinnovo 12 mesi",
        "months": 12,
        "amount_cents": 36000,
        "price_text": "360€",
        "description": "Rinnovo abbonamento sala pesi per 12 mesi",
    },
}


def clean_badge(value: str) -> str:
    value = (value or "").strip().upper()
    value = re.sub(r"[^A-Z0-9]", "", value)
    return value


def valid_badge(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{6,40}", value or ""))


def safe_name(value: str) -> str:
    value = (value or "").strip()
    value = value[:80]
    return value


# ---------------- PAGINA RINNOVO ----------------

@app.route("/")
def home():
    return redirect("/info")


@app.route("/info")
def info():
    return render_template_string("""
<!doctype html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AG GYM - Rinnovi online</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #0b1117;
            color: #f4f7fb;
            padding: 30px;
        }
        .box {
            max-width: 760px;
            margin: 0 auto;
            background: #16212b;
            border-radius: 22px;
            padding: 28px;
            box-shadow: 0 10px 35px rgba(0,0,0,.35);
        }
        h1 {
            margin-top: 0;
            color: #ffd166;
            font-size: 34px;
        }
        p {
            font-size: 18px;
            line-height: 1.45;
            color: #d7e0e8;
        }
        .warn {
            background: #1c2a36;
            border-left: 6px solid #ffd166;
            padding: 14px 16px;
            border-radius: 12px;
            margin-top: 20px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>AG GYM - Rinnovi online</h1>
        <p>Questa pagina è riservata ai soci già registrati.</p>
        <p>Per rinnovare, passa il badge al lettore della palestra e scansiona il QR code mostrato sul display.</p>
        <div class="warn">
            Nuove iscrizioni, tesseramento iniziale e assistenza vengono gestiti solo in presenza dalla Presidenza.
        </div>
    </div>
</body>
</html>
""")


@app.route("/rinnovo")
def rinnovo():
    badge = clean_badge(request.args.get("badge", ""))
    name = safe_name(request.args.get("name", ""))

    if not valid_badge(badge):
        return render_template_string("""
<!doctype html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Badge non valido</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #0b1117;
            color: #f4f7fb;
            padding: 30px;
        }
        .box {
            max-width: 720px;
            margin: 0 auto;
            background: #16212b;
            border-radius: 22px;
            padding: 28px;
        }
        h1 { color: #ff9090; }
        p { font-size: 18px; color: #d7e0e8; }
    </style>
</head>
<body>
    <div class="box">
        <h1>Badge non valido</h1>
        <p>Il link non contiene un badge valido.</p>
        <p>Rivolgiti alla Presidenza AG GYM.</p>
    </div>
</body>
</html>
"""), 400

    badge_html = escape(badge)
    name_html = escape(name) if name else "Socio AG GYM"

    plan_cards = ""
    for plan_id, plan in PLANS.items():
        plan_cards += f"""
        <form method="post" action="/checkout" class="card">
            <input type="hidden" name="badge" value="{badge_html}">
            <input type="hidden" name="name" value="{name_html}">
            <input type="hidden" name="plan_id" value="{plan_id}">
            <div class="months">{plan["title"]}</div>
            <div class="desc">{plan["description"]}</div>
            <button type="submit">{plan["price_text"]}</button>
        </form>
        """

    return render_template_string(f"""
<!doctype html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Rinnovo AG GYM</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #0b1117;
            color: #f4f7fb;
            padding: 22px;
        }}
        .wrap {{
            max-width: 920px;
            margin: 0 auto;
        }}
        .header {{
            background: #16212b;
            border-radius: 24px;
            padding: 24px;
            margin-bottom: 18px;
            box-shadow: 0 10px 35px rgba(0,0,0,.35);
        }}
        .brand {{
            color: #ffd166;
            font-size: 18px;
            font-weight: 900;
            letter-spacing: .08em;
            text-transform: uppercase;
        }}
        h1 {{
            margin: 8px 0 10px 0;
            font-size: 38px;
            line-height: 1.05;
        }}
        .subtitle {{
            color: #d7e0e8;
            font-size: 18px;
            line-height: 1.35;
        }}
        .userbox {{
            margin-top: 18px;
            background: #101922;
            border-radius: 16px;
            padding: 16px;
        }}
        .label {{
            color: #aebbc8;
            font-size: 13px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .08em;
        }}
        .value {{
            font-size: 22px;
            font-weight: 900;
            margin-top: 4px;
        }}
        .plans {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
        }}
        .card {{
            background: #16212b;
            border: 2px solid #26313a;
            border-radius: 22px;
            padding: 20px;
            box-shadow: 0 8px 28px rgba(0,0,0,.28);
        }}
        .months {{
            color: #ffd166;
            font-size: 28px;
            font-weight: 900;
            margin-bottom: 8px;
        }}
        .desc {{
            color: #d7e0e8;
            font-size: 16px;
            min-height: 45px;
            line-height: 1.35;
        }}
        button {{
            width: 100%;
            margin-top: 18px;
            border: 0;
            border-radius: 16px;
            padding: 16px;
            background: #ffd166;
            color: #111111;
            font-size: 28px;
            font-weight: 900;
            cursor: pointer;
        }}
        button:active {{
            transform: scale(.98);
        }}
        .note {{
            margin-top: 18px;
            background: #1c2a36;
            border-left: 6px solid #ffd166;
            border-radius: 14px;
            padding: 16px;
            color: #d7e0e8;
            font-size: 16px;
            line-height: 1.45;
        }}
        .small {{
            color: #aebbc8;
            font-size: 14px;
            margin-top: 14px;
            line-height: 1.4;
        }}
        @media (max-width: 720px) {{
            body {{
                padding: 14px;
            }}
            h1 {{
                font-size: 32px;
            }}
            .plans {{
                grid-template-columns: 1fr;
            }}
            .months {{
                font-size: 25px;
            }}
        }}
    </style>
</head>
<body>
    <div class="wrap">
        <div class="header">
            <div class="brand">ASD AG GYM</div>
            <h1>Rinnovo abbonamento</h1>
            <div class="subtitle">
                Scegli il piano, paga online e poi attendi qualche secondo prima di ripassare il badge.
            </div>

            <div class="userbox">
                <div class="label">Socio</div>
                <div class="value">{name_html}</div>
                <br>
                <div class="label">Badge</div>
                <div class="value">{badge_html}</div>
            </div>
        </div>

        <div class="plans">
            {plan_cards}
        </div>

        <div class="note">
            <strong>Importante:</strong> questa pagina è riservata esclusivamente ai rinnovi di soci già iscritti.
            Nuove iscrizioni, tesseramento iniziale e assistenza vengono gestiti solo in presenza dalla Presidenza.
        </div>

        <div class="small">
            In caso di problemi contattare: {PHONE_1} • {PHONE_2}
        </div>
    </div>
</body>
</html>
""")


@app.route("/checkout", methods=["POST"])
def checkout():
    badge = clean_badge(request.form.get("badge", ""))
    name = safe_name(request.form.get("name", ""))
    plan_id = (request.form.get("plan_id", "") or "").strip()

    if not valid_badge(badge):
        abort(400, "Badge non valido")

    if plan_id not in PLANS:
        abort(400, "Piano non valido")

    if not STRIPE_SECRET_KEY:
        abort(500, "STRIPE_SECRET_KEY mancante")

    if not BASE_URL:
        abort(500, "BASE_URL mancante")

    plan = PLANS[plan_id]

    metadata = {
        "source": "ag_gym_renewal",
        "badge": badge,
        "name": name or "",
        "plan_id": plan_id,
        "months": str(plan["months"]),
        "amount_cents": str(plan["amount_cents"]),
        "created_by": "ag_gym_render_server",
    }

    session = stripe.checkout.Session.create(
        mode="payment",
        client_reference_id=badge,
        metadata=metadata,
        payment_intent_data={
            "metadata": metadata
        },
        line_items=[
            {
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": f"{plan['title']} - AG GYM",
                        "description": "Rinnovo online riservato ai soci già iscritti",
                        "metadata": metadata,
                    },
                    "unit_amount": plan["amount_cents"],
                },
                "quantity": 1,
            }
        ],
        success_url=f"{BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{BASE_URL}/cancel?badge={badge}",
    )

    return redirect(session.url, code=303)


@app.route("/success")
def success():
    session_id = request.args.get("session_id", "")

    return render_template_string(f"""
<!doctype html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pagamento ricevuto</title>
    <style>
        body {{
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #0b1117;
            color: #f4f7fb;
            padding: 24px;
        }}
        .box {{
            max-width: 760px;
            margin: 0 auto;
            background: #16212b;
            border-radius: 24px;
            padding: 28px;
            text-align: center;
            box-shadow: 0 10px 35px rgba(0,0,0,.35);
        }}
        .ok {{
            font-size: 70px;
            color: #00a651;
            font-weight: 900;
        }}
        h1 {{
            color: #ffd166;
            font-size: 36px;
        }}
        p {{
            color: #d7e0e8;
            font-size: 19px;
            line-height: 1.45;
        }}
        .small {{
            margin-top: 18px;
            color: #aebbc8;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="box">
        <div class="ok">✓</div>
        <h1>Pagamento ricevuto</h1>
        <p>
            Il rinnovo è stato registrato.<br>
            Attendi qualche secondo e poi ripassa il badge al lettore.
        </p>
        <p>
            In caso di problemi contatta la Presidenza:<br>
            <strong>{PHONE_1} • {PHONE_2}</strong>
        </p>
        <div class="small">Sessione Stripe: {escape(session_id)}</div>
    </div>
</body>
</html>
""")


@app.route("/cancel")
def cancel():
    badge = clean_badge(request.args.get("badge", ""))

    retry_url = f"/rinnovo?badge={badge}" if valid_badge(badge) else "/info"

    return render_template_string(f"""
<!doctype html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pagamento annullato</title>
    <style>
        body {{
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #0b1117;
            color: #f4f7fb;
            padding: 24px;
        }}
        .box {{
            max-width: 760px;
            margin: 0 auto;
            background: #16212b;
            border-radius: 24px;
            padding: 28px;
            text-align: center;
        }}
        h1 {{
            color: #ff9090;
        }}
        p {{
            color: #d7e0e8;
            font-size: 18px;
        }}
        a {{
            display: inline-block;
            margin-top: 18px;
            background: #ffd166;
            color: #111;
            padding: 14px 20px;
            border-radius: 14px;
            text-decoration: none;
            font-weight: 900;
        }}
    </style>
</head>
<body>
    <div class="box">
        <h1>Pagamento annullato</h1>
        <p>Non è stato effettuato nessun rinnovo.</p>
        <a href="{retry_url}">Torna al rinnovo</a>
    </div>
</body>
</html>
""")


@app.route("/health")
def health():
    return {
        "ok": True,
        "service": "ag_gym_renewals",
        "time": datetime.now().isoformat(),
        "plans": {
            plan_id: {
                "months": plan["months"],
                "amount_cents": plan["amount_cents"],
                "title": plan["title"],
            }
            for plan_id, plan in PLANS.items()
        }
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
