# AI Disaster Relief Resource Matcher

A beginner-friendly full-stack project for disaster relief resource coordination.

## Features

- Donors can post available resources.
- Rescue teams can post required resources.
- Resource fields: type, product name, quantity, unit, urgency, and location.
- AI-style explainable matching engine.
- Matching considers:
  1. Resource type
  2. Product name
  3. Quantity availability
  4. Request urgency
  5. Location / coordinates
- Rescue teams can confirm a match.
- Confirming a match reduces available donor stock.
- SQLite database stores resources and requests.
- React + Vite frontend.
- Flask backend.
- Interactive disaster map using Leaflet.
- Match history for confirmed relief matches.

## Requirements

Install:

- Python 3.10+
- Node.js 18+

## Run Backend

Open a terminal in the `backend` folder:

### Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py