"""
generate_data.py
Creates a sample clinic_visits.csv file with realistic random data.
Run once:  python generate_data.py
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)  # same "random" data every time you run it

COURSES = ["BSIT", "BSCS", "BSN", "BSEd", "BSBA", "BSCrim", "BSHM"]

# complaint: weight (higher = more common)
COMPLAINTS = {
    "Fever": 18,
    "Headache": 20,
    "Cough and Colds": 16,
    "Stomachache": 12,
    "Dysmenorrhea": 9,
    "Dizziness": 7,
    "Toothache": 5,
    "Allergy": 5,
    "Wound/Injury": 5,
    "Asthma": 3,
}

NUM_STUDENTS = 300
NUM_VISITS = 450
START = date(2026, 1, 5)
END = date(2026, 11, 13)

# 1. Make a list of students (each student keeps the same age, gender, course)
students = []
for i in range(1, NUM_STUDENTS + 1):
    year_enrolled = random.choice([2022, 2023, 2024, 2025])
    students.append({
        "student_id": f"S{year_enrolled}{i:03d}",
        "age": random.choices(range(17, 27), weights=[8, 18, 18, 17, 14, 10, 6, 4, 3, 2])[0],
        "gender": random.choice(["Male", "Female"]),
        "course": random.choice(COURSES),
    })

# 2. Make the visits
visits = []
total_days = (END - START).days
for _ in range(NUM_VISITS):
    s = random.choice(students)
    complaint = random.choices(list(COMPLAINTS), weights=COMPLAINTS.values())[0]
    if complaint == "Dysmenorrhea":          # only female students
        s = random.choice([x for x in students if x["gender"] == "Female"])
    d = START + timedelta(days=random.randint(0, total_days))
    while d.weekday() >= 5:                 # skip Saturday/Sunday
        d += timedelta(days=1)
    visits.append({**s, "complaint": complaint, "date": d.isoformat()})

visits.sort(key=lambda v: v["date"])

# 3. Save to CSV
with open("clinic_visits.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["visit_id", "student_id", "age", "gender", "course", "complaint", "date"])
    for n, v in enumerate(visits, start=1):
        writer.writerow([f"CL{n:03d}", v["student_id"], v["age"], v["gender"],
                         v["course"], v["complaint"], v["date"]])

print(f"Created clinic_visits.csv with {len(visits)} visits.")
