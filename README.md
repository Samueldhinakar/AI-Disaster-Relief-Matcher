# AI Disaster Relief Resource Matcher

A beginner-friendly full-stack project for VS Code.

## Features

- Donors can post available resources.
- Rescue teams can post required resources.
- Resource fields: type, product name, quantity, unit, urgency and location.
- AI-style explainable matching engine.
- Matching considers:
  1. Resource type
  2. Product name
  3. Quantity availability
  4. Request urgency
  5. Location / coordinates
- Rescue team can confirm a match.
- Confirming a match reduces available donor stock.
- SQLite database stores resources and requests.
- React + Vite frontend.
- Flask backend.

## Requirements

Install:
- Python 3.10+
- Node.js 18+

## Run backend

Open a terminal in the `backend` folder:

Windows:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Backend runs at:
http://127.0.0.1:5000

## Run frontend

Open a second terminal in the `frontend` folder:

```bash
npm install
npm run dev
```

Open the URL shown by Vite, normally:
http://localhost:5173

## Demo flow

1. Open Donor Resources.
2. Add:
   - Type: Food
   - Name: Rice
   - Quantity: 500
   - Unit: kg
   - Location: Coimbatore
   - Urgency: High
   - Donor: ABC NGO
3. Open Rescue Requests.
4. Add:
   - Type: Food
   - Name: Rice
   - Quantity: 300
   - Unit: kg
   - Location: Coimbatore
   - Urgency: Critical
   - Team: Rescue Team 1
5. Open AI Matches.
6. Click Run AI Matching.
7. Confirm the match.
8. The donor's remaining quantity becomes 200 kg.

## Important

This project uses an explainable rule-based scoring engine called the "AI matching engine" for the prototype. For a final-year/hackathon version, you can later replace it with a machine-learning model or optimization algorithm using historical disaster data.
