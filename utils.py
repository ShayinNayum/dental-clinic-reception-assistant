"""
Utility functions for the Dental Clinic Reception Assistant.

Edit CLINIC_INFO below with your real clinic information.
Do not put your Gemini API key in this file.
"""

import re
from typing import Dict, List

CLINIC_INFO = {
    "name": "Bright Smile Dental Clinic",
    "address": "123 Main Street, Chennai",
    "phone": "+91-90000-00000",
    "email": "reception@brightsmile.example",
    "hours": {
        "Monday": "9:00 AM - 6:00 PM",
        "Tuesday": "9:00 AM - 6:00 PM",
        "Wednesday": "9:00 AM - 6:00 PM",
        "Thursday": "9:00 AM - 6:00 PM",
        "Friday": "9:00 AM - 6:00 PM",
        "Saturday": "9:00 AM - 2:00 PM",
        "Sunday": "Closed",
    },
    "services": {
        "Dental check-up": "Routine examination and oral-health assessment.",
        "Teeth cleaning": "Professional cleaning to remove plaque and tartar.",
        "Dental filling": "Treatment of cavities using a suitable filling material.",
        "Root canal treatment": "Treatment for an infected or inflamed tooth; dentist assessment is required.",
        "Tooth extraction": "Removal of a tooth when clinically necessary.",
        "Teeth whitening": "Cosmetic tooth-whitening consultation and treatment.",
        "Braces consultation": "Initial orthodontic consultation for alignment concerns.",
        "Dental crown": "A protective restoration used for damaged or weakened teeth.",
    },
    "appointment_policy": (
        "Appointments are recommended. The receptionist should collect the "
        "patient's name, phone number, preferred date, preferred time, and reason "
        "for the visit before treating an appointment request as ready."
    ),
    "emergency_policy": (
        "For severe facial swelling, uncontrolled bleeding, difficulty breathing, "
        "or a serious dental injury, advise the patient to seek urgent medical/dental "
        "care. The chatbot must not diagnose or prescribe medication."
    ),
}

def get_clinic_info() -> Dict:
    return CLINIC_INFO

def get_services() -> Dict[str, str]:
    return CLINIC_INFO["services"]

def search_clinic_info(query: str) -> str:
    """Return the most relevant clinic information for the user's question."""
    q = query.lower()
    chunks = []

    if any(k in q for k in ["hour", "open", "close", "timing", "time", "sunday", "saturday"]):
        hours = "\n".join(f"- {day}: {time}" for day, time in CLINIC_INFO["hours"].items())
        chunks.append("Clinic hours:\n" + hours)

    if any(k in q for k in ["address", "location", "where", "located", "phone", "call", "email"]):
        chunks.append(
            f"Clinic: {CLINIC_INFO['name']}\n"
            f"Address: {CLINIC_INFO['address']}\n"
            f"Phone: {CLINIC_INFO['phone']}\n"
            f"Email: {CLINIC_INFO['email']}"
        )

    matched = []
    for service, description in CLINIC_INFO["services"].items():
        terms = re.findall(r"[a-z]+", service.lower())
        if any(term in q for term in terms) or service.lower() in q:
            matched.append(f"- {service}: {description}")

    if matched:
        chunks.append("Relevant services:\n" + "\n".join(matched))

    if any(k in q for k in ["appointment", "book", "schedule", "visit", "available"]):
        chunks.append("Appointment policy:\n" + CLINIC_INFO["appointment_policy"])

    if any(k in q for k in ["emergency", "swelling", "bleeding", "injury", "accident", "severe pain"]):
        chunks.append("Emergency guidance:\n" + CLINIC_INFO["emergency_policy"])

    if not chunks:
        chunks.append(
            f"Clinic: {CLINIC_INFO['name']}\n"
            f"Address: {CLINIC_INFO['address']}\n"
            f"Phone: {CLINIC_INFO['phone']}\n"
            f"Email: {CLINIC_INFO['email']}\n"
            "Services: " + ", ".join(CLINIC_INFO["services"].keys())
        )

    return "\n\n".join(chunks)

def build_system_prompt() -> str:
    services = "\n".join(
        f"- {name}: {description}"
        for name, description in CLINIC_INFO["services"].items()
    )
    hours = "\n".join(
        f"- {day}: {time}" for day, time in CLINIC_INFO["hours"].items()
    )

    return f"""
You are the friendly reception assistant for {CLINIC_INFO['name']}.

Your job:
1. Answer basic reception questions about the clinic, hours, location, contact details,
   services, and appointment requests.
2. Help the patient understand what information is needed to request an appointment.
3. Be concise, polite, and professional.
4. Use only the clinic information supplied in the context. If something is not supplied,
   say that the receptionist must confirm it.
5. Never diagnose a dental condition, prescribe medicine, or give definitive treatment
   instructions.
6. For urgent symptoms, encourage prompt professional/urgent care according to the
   emergency guidance supplied below.
7. Do not claim that an appointment is booked unless a real booking system confirms it.
8. If the patient asks for a specific dentist, price, insurance coverage, or availability
   that is not listed, say the receptionist needs to confirm it.
9. Protect privacy: do not ask for unnecessary sensitive information.
10. When collecting an appointment request, ask for missing basics one at a time:
    patient name, phone number, preferred date, preferred time, and reason for visit.

Clinic details:
Name: {CLINIC_INFO['name']}
Address: {CLINIC_INFO['address']}
Phone: {CLINIC_INFO['phone']}
Email: {CLINIC_INFO['email']}

Hours:
{hours}

Services:
{services}

Appointment policy:
{CLINIC_INFO['appointment_policy']}

Emergency guidance:
{CLINIC_INFO['emergency_policy']}
""".strip()

def clean_user_input(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()
def get_all_appointments():
    import json
    import os

    if not os.path.exists("appointments.json"):
        return []

    with open("appointments.json", "r") as f:
        return json.load(f)