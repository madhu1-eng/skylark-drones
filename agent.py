import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
client = gspread.authorize(creds)

sheet = client.open("missions")

pilot_ws = sheet.worksheet("pilot_roster")
drone_ws = sheet.worksheet("drone_fleet")
mission_ws = sheet.worksheet("missions")

pilots = pilot_ws.get_all_records()
drones = drone_ws.get_all_records()
missions = mission_ws.get_all_records()

print("AI AGENT READY\n")

# ---------------- HELPERS ----------------
def mission_days(m):
    start = datetime.fromisoformat(m["start_date"])
    end = datetime.fromisoformat(m["end_date"])
    return (end - start).days + 1

def find_pilot(m):
    for p in pilots:
        if p["status"] != "Available":
            continue
        if m["required_skills"] not in p["skills"]:
            continue
        if m["required_certs"] not in p["certifications"]:
            print("⚠ Certification mismatch:", p["name"])
            continue
        return p
    return None

def find_drone(m):
    for d in drones:
        if d["status"] != "Available":
            continue
        if m["weather_forecast"] == "Rainy" and "Rain" not in d["weather_resistance"]:
            print("⚠ Weather risk:", d["drone_id"])
            continue
        return d
    return None

def update_sheet_status(pilot, drone, mission):
    # update pilot status
    cells = pilot_ws.findall(pilot["name"])
    if cells:
        row = cells[0].row
        pilot_ws.update_cell(row, 6, "Assigned")  # status col
        pilot_ws.update_cell(row, 7, mission["project_id"])

    # update drone status
    cells = drone_ws.findall(drone["drone_id"])
    if cells:
        row = cells[0].row
        drone_ws.update_cell(row, 4, "Assigned")
        drone_ws.update_cell(row, 7, mission["project_id"])

# ---------------- URGENT REASSIGNMENT ----------------
def handle_urgent(m):
    if m["priority"] != "Urgent":
        return None

    print("🚨 Urgent mission → trying reassignment")

    for p in pilots:
        if p["status"] == "Assigned":
            print("Reassigning pilot:", p["name"])
            return p
    return None

# ---------------- MAIN LOOP ----------------
for m in missions:
    print(f"\nChecking mission {m['project_id']}")

    pilot = find_pilot(m)

    if not pilot:
        pilot = handle_urgent(m)

    drone = find_drone(m)

    if not pilot:
        print("❌ No pilot available")
        continue

    if not drone:
        print("❌ No drone available")
        continue

    # budget check
    cost = mission_days(m) * pilot["daily_rate_inr"]
    if cost > m["mission_budget_inr"]:
        print("⚠ Budget exceeded")
        continue

    # location mismatch
    if pilot["location"] != m["location"]:
        print("⚠ Location mismatch:", pilot["name"])

    print("✅ Assigning pilot:", pilot["name"])
    print("✅ Assigning drone:", drone["drone_id"])

    update_sheet_status(pilot, drone, m)

print("\nAgent finished")

