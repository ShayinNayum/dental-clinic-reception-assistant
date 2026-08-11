import os
import json
import re
from datetime import datetime

import panel as pn
from google import genai
from google.genai import types
import utils

pn.extension()

# Gemini configuration
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Add it in Replit Secrets."
    )

client = genai.Client(api_key=API_KEY)
MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = utils.build_system_prompt()

# ---------------- Appointment storage ----------------

APPOINTMENTS_FILE = "appointments.json"


def load_appointments():
    if not os.path.exists(APPOINTMENTS_FILE):
        with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as file:
            json.dump([], file, indent=4)

    with open(APPOINTMENTS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_appointment(name, phone, date, time, reason):
    appointments = load_appointments()

    appointment = {
        "name": name,
        "phone": phone,
        "date": date,
        "time": time,
        "reason": reason,
        "booked_at": datetime.now().isoformat(timespec="seconds"),
    }

    appointments.append(appointment)

    with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as file:
        json.dump(appointments, file, indent=4)

    return appointment


def get_all_appointments():
    return load_appointments()


def show_appointments():
    appointments = get_all_appointments()

    if not appointments:
        return "No appointments found."

    message = "## 🦷 Appointment List\n\n"

    for i, appt in enumerate(appointments, start=1):
        message += (
            f"**{i}. Appointment**\n"
            f"- Name: {appt.get('name')}\n"
            f"- Phone: {appt.get('phone')}\n"
            f"- Date: {appt.get('date')}\n"
            f"- Time: {appt.get('time')}\n"
            f"- Reason: {appt.get('reason')}\n\n"
            f"---\n\n"
        )

    return message


def cancel_appointment(phone):
    appointments = get_all_appointments()

    if not appointments:
        return "No appointments found."

    found = False
    remaining = []

    for appt in appointments:
        if str(appt.get("phone", "")) == str(phone):
            found = True
        else:
            remaining.append(appt)

    if not found:
        return f"No appointment found for phone number {phone}."

    with open(APPOINTMENTS_FILE, "w", encoding="utf-8") as file:
        json.dump(remaining, file, indent=4)

    return f"Appointment for phone number {phone} has been cancelled successfully."


def find_appointment(phone):
    appointments = get_all_appointments()

    if not appointments:
        return "No appointments found."

    for appt in appointments:
        if str(appt.get("phone", "")) == str(phone):
            return (
                "## 🦷 Appointment Found\n\n"
                f"- Name: {appt.get('name')}\n"
                f"- Phone: {appt.get('phone')}\n"
                f"- Date: {appt.get('date')}\n"
                f"- Time: {appt.get('time')}\n"
                f"- Reason: {appt.get('reason')}"
            )

    return f"No appointment found for phone number {phone}."


# ---------------- Gemini helpers ----------------

def get_completion_from_messages(
    messages, model=MODEL, temperature=0.3, max_tokens=500
):
    contents = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")

        if role == "system":
            continue

        gemini_role = "model" if role == "assistant" else "user"
        contents.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part.from_text(text=str(content))],
            )
        )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )

    return response.text.strip()


def book_appointment_from_message(user_message):
    response = client.models.generate_content(
        model=MODEL,
        contents=f"""
You are a dental clinic reception assistant.

Extract appointment details from this patient message:

"{user_message}"

Return ONLY these 5 lines:

Name: ...
Phone: ...
Date: ...
Time: ...
Reason: ...

If a detail is missing, write:
Missing
""",
    )

    details = response.text.strip()
    data = {}

    for line in details.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()

    required = ["Name", "Phone", "Date", "Time", "Reason"]

    if any(data.get(key) in [None, "", "Missing"] for key in required):
        return "Please provide all appointment details."

    save_appointment(
        name=data["Name"],
        phone=data["Phone"],
        date=data["Date"],
        time=data["Time"],
        reason=data["Reason"],
    )

    return (
        "## ✅ Appointment booked successfully!\n\n"
        f"- **Name:** {data['Name']}\n"
        f"- **Phone:** {data['Phone']}\n"
        f"- **Date:** {data['Date']}\n"
        f"- **Time:** {data['Time']}\n"
        f"- **Reason:** {data['Reason']}"
    )


# ---------------- Booking conversation state ----------------

booking_state = {
    "active": False,
    "step": None,
    "name": None,
    "phone": None,
    "date": None,
    "time": None,
    "reason": None,
}


def reset_booking():
    booking_state.update({
        "active": False,
        "step": None,
        "name": None,
        "phone": None,
        "date": None,
        "time": None,
        "reason": None,
    })


def start_booking():
    reset_booking()
    booking_state["active"] = True
    booking_state["step"] = "name"
    return "Sure! 😊 Let's book your dental appointment. What is your **name**?"


def continue_booking(user_input):
    value = user_input.strip()
    step = booking_state["step"]

    if not value:
        return "Please enter a value."

    if step == "name":
        booking_state["name"] = value
        booking_state["step"] = "phone"
        return "Thank you! 📞 What is your **10-digit phone number**?"

    if step == "phone":
        phone_match = re.search(r"\b\d{10}\b", value)
        if not phone_match:
            return "Please enter a valid **10-digit phone number**."
        booking_state["phone"] = phone_match.group()
        booking_state["step"] = "date"
        return "Great! 📅 What **date** would you like for the appointment?"

    if step == "date":
        booking_state["date"] = value
        booking_state["step"] = "time"
        return "What **time** would you prefer?"

    if step == "time":
        booking_state["time"] = value
        booking_state["step"] = "reason"
        return "What is the **reason for the visit**? (For example: cleaning, tooth pain, check-up)"

    if step == "reason":
        booking_state["reason"] = value

        appointment = save_appointment(
            name=booking_state["name"],
            phone=booking_state["phone"],
            date=booking_state["date"],
            time=booking_state["time"],
            reason=booking_state["reason"],
        )

        response = (
            "## ✅ Appointment booked successfully!\n\n"
            f"- **Name:** {appointment['name']}\n"
            f"- **Phone:** {appointment['phone']}\n"
            f"- **Date:** {appointment['date']}\n"
            f"- **Time:** {appointment['time']}\n"
            f"- **Reason:** {appointment['reason']}\n\n"
            "Thank you! 🦷 We look forward to seeing you."
        )
        reset_booking()
        return response

    reset_booking()
    return start_booking()


# ---------------- Chat UI ----------------

context = [{"role": "system", "content": SYSTEM_PROMPT}]

# Medium-level professional styling
pn.config.raw_css.append("""
:root {
    --clinic-blue: #176b87;
    --clinic-blue-dark: #0e4f66;
    --clinic-bg: #f4f8fa;
    --clinic-card: #ffffff;
    --clinic-text: #18323d;
    --clinic-muted: #6b7f88;
}

body {
    background: #f4f8fa;
}

.clinic-header {
    background: linear-gradient(135deg, #176b87, #2b8eaa);
    color: white;
    border-radius: 16px;
    padding: 24px 28px;
    box-shadow: 0 8px 24px rgba(23, 107, 135, 0.18);
}

.clinic-header h1 {
    margin: 0;
    font-size: 28px;
}

.clinic-header p {
    margin: 7px 0 0;
    opacity: 0.92;
    font-size: 14px;
}

.clinic-card {
    background: white;
    border: 1px solid #dce8ed;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 5px 18px rgba(24, 50, 61, 0.07);
}

.clinic-card h3 {
    color: #176b87;
    margin-top: 0;
}

.chat-card {
    background: white;
    border: 1px solid #dce8ed;
    border-radius: 14px;
    padding: 10px;
    box-shadow: 0 5px 18px rgba(24, 50, 61, 0.07);
}

.chat-title {
    color: #176b87;
    font-weight: 700;
    font-size: 18px;
    padding: 8px 8px 12px;
    border-bottom: 1px solid #e4edf0;
}
""")

chat_box = pn.Column(
    height=500,
    scroll=True,
    sizing_mode="stretch_width",
)

inp = pn.widgets.TextInput(
    placeholder="Type your message… e.g. I want to book an appointment",
    sizing_mode="stretch_width",
)

send_button = pn.widgets.Button(
    name="Send  ➤",
    button_type="primary",
    width=105,
    height=38,
)


def send_message(event):
    global context

    user_input = inp.value.strip()

    if not user_input:
        return

    chat_box.append(
        pn.pane.Markdown(
            f"**You**  \n{user_input}",
            margin=(8, 12, 8, 12),
        )
    )
    inp.value = ""

    try:
        lower = user_input.lower()

        if booking_state["active"]:
            response = continue_booking(user_input)

        elif (
            ("appointment" in lower or "book" in lower)
            and not ("show" in lower or "find" in lower or "search" in lower or "cancel" in lower)
        ):
            response = start_booking()

        elif "show" in lower and "appointment" in lower:
            response = show_appointments()

        elif "find" in lower or "search" in lower:
            phone_match = re.search(r"\b\d{10}\b", user_input)

            if phone_match:
                response = find_appointment(phone_match.group())
            else:
                response = "Please provide your 10-digit phone number."

        elif "cancel" in lower:
            phone_match = re.search(r"\b\d{10}\b", user_input)

            if phone_match:
                response = cancel_appointment(phone_match.group())
            else:
                response = "Please provide your 10-digit phone number."

        else:
            response = client.models.generate_content(
                model=MODEL,
                contents=f"""
You are a friendly dental clinic reception assistant
for Bright Smile Dental Clinic.

Answer the patient's question clearly and politely.

Patient question:
{user_input}
""",
            ).text

        chat_box.append(
            pn.pane.Markdown(
                f"**🦷 Dental Reception Assistant**  \n{response}",
                margin=(8, 12, 14, 12),
            )
        )

    except Exception as e:
        chat_box.append(
            pn.pane.Markdown(
                f"**⚠️ Error**  \n{str(e)}",
                margin=(8, 12, 8, 12),
            )
        )


send_button.on_click(send_message)

header = pn.pane.HTML("""
<div class="clinic-header">
    <h1>🦷 Bright Smile Dental Clinic</h1>
    <p>AI-Powered Dental Reception Assistant · Appointments, enquiries & patient support</p>
</div>
""", sizing_mode="stretch_width")

clinic_info = pn.pane.HTML("""
<div class="clinic-card">
    <h3>🏥 Clinic Information</h3>
    <b>Bright Smile Dental Clinic</b><br><br>
    📍 Comfortable & friendly dental care<br>
    📞 Reception available for appointments<br>
    🕒 Mon–Sat · 9:00 AM – 6:00 PM<br><br>

    <h3>🦷 Services</h3>
    • Dental check-up<br>
    • Teeth cleaning<br>
    • Tooth pain consultation<br>
    • Dental fillings<br>
    • General dental care
</div>
""", sizing_mode="stretch_width")

quick_help = pn.pane.HTML("""
<div class="clinic-card">
    <h3>💡 Quick Help</h3>
    <b>Book:</b> “I want to book an appointment”<br><br>
    <b>Find:</b> “Find my appointment 9876543210”<br><br>
    <b>Cancel:</b> “Cancel my appointment 9876543210”<br><br>
    <b>View:</b> “Show appointments”
</div>
""", sizing_mode="stretch_width")

chat_panel = pn.Column(
    pn.pane.HTML('<div class="chat-title">💬 Chat with Reception</div>'),
    chat_box,
    pn.Row(inp, send_button, sizing_mode="stretch_width"),
    css_classes=["chat-card"],
    sizing_mode="stretch_width",
)

dashboard = pn.Column(
    header,
    pn.Row(
        pn.Column(clinic_info, quick_help, width=285),
        chat_panel,
        sizing_mode="stretch_width",
    ),
    sizing_mode="stretch_width",
    margin=(18, 24),
)

dashboard.servable()
