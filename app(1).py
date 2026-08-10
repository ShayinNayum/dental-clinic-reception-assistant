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


# ---------------- Chat UI ----------------

context = [{"role": "system", "content": SYSTEM_PROMPT}]

chat_box = pn.Column(
    height=450,
    scroll=True,
    sizing_mode="stretch_width",
)

inp = pn.widgets.TextInput(
    placeholder="Type your question here...",
    sizing_mode="stretch_width",
)

send_button = pn.widgets.Button(
    name="Send",
    button_type="primary",
)


def send_message(event):
    global context

    user_input = inp.value.strip()

    if not user_input:
        return

    chat_box.append(pn.pane.Markdown(f"**You:** {user_input}"))
    inp.value = ""

    try:
        lower = user_input.lower()

        if "show" in lower and "appointment" in lower:
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

        elif "appointment" in lower or "book" in lower:
            response = book_appointment_from_message(user_input)

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
                f"**🦷 Dental Reception Assistant:**\n\n{response}"
            )
        )

    except Exception as e:
        chat_box.append(pn.pane.Markdown(f"**Error:** {str(e)}"))


send_button.on_click(send_message)

dashboard = pn.Column(
    pn.pane.Markdown("# 🦷 Dental Clinic Reception Assistant"),
    chat_box,
    pn.Row(inp, send_button),
    sizing_mode="stretch_width",
)

dashboard.servable()
