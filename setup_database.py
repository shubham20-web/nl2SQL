"""
setup_database.py
Creates clinic.db with schema + realistic dummy data.
Run: python setup_database.py
"""

import sqlite3
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

DB_PATH = "clinic.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    date_of_birth   DATE,
    gender          TEXT,
    city            TEXT,
    registered_date DATE
);
CREATE TABLE IF NOT EXISTS doctors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    specialization  TEXT,
    department      TEXT,
    phone           TEXT
);
CREATE TABLE IF NOT EXISTS appointments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       INTEGER REFERENCES patients(id),
    doctor_id        INTEGER REFERENCES doctors(id),
    appointment_date DATETIME,
    status           TEXT,
    notes            TEXT
);
CREATE TABLE IF NOT EXISTS treatments (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id    INTEGER REFERENCES appointments(id),
    treatment_name    TEXT,
    cost              REAL,
    duration_minutes  INTEGER
);
CREATE TABLE IF NOT EXISTS invoices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id   INTEGER REFERENCES patients(id),
    invoice_date DATE,
    total_amount REAL,
    paid_amount  REAL,
    status       TEXT
);
"""

SPECIALIZATIONS = {
    "Dermatology": "Skin & Hair",
    "Cardiology":  "Heart & Vascular",
    "Orthopedics": "Bone & Joint",
    "General":     "General Medicine",
    "Pediatrics":  "Child Health",
}

TREATMENT_MAP = {
    "Dermatology": [("Skin Biopsy",300,30),("Acne Treatment",150,20),("Laser Therapy",500,45)],
    "Cardiology":  [("ECG",100,20),("Echocardiogram",800,60),("Stress Test",600,45)],
    "Orthopedics": [("X-Ray",120,15),("Physiotherapy",300,60),("Joint Injection",450,30)],
    "General":     [("Blood Test",80,15),("General Checkup",100,20),("Vaccination",60,10)],
    "Pediatrics":  [("Child Checkup",90,20),("Growth Assessment",110,25),("Immunization",70,10)],
}

CITIES   = ["Mumbai","Delhi","Bangalore","Hyderabad","Chennai","Pune","Ahmedabad","Kolkata","Jaipur","Indore"]
STATUSES = ["Scheduled","Completed","Cancelled","No-Show"]
INV_ST   = ["Paid","Pending","Overdue"]

def rdate(days_back):
    return (datetime.now()-timedelta(days=random.randint(0,days_back))).strftime("%Y-%m-%d")

def rdatetime(days_back):
    b = datetime.now()-timedelta(days=random.randint(0,days_back))
    b = b.replace(hour=random.randint(8,17), minute=random.choice([0,15,30,45]))
    return b.strftime("%Y-%m-%d %H:%M:%S")

def seed(conn):
    cur = conn.cursor()

    # Doctors (15)
    doctor_ids, doctor_spec = [], {}
    for spec, dept in SPECIALIZATIONS.items():
        for _ in range(3):
            cur.execute("INSERT INTO doctors(name,specialization,department,phone) VALUES(?,?,?,?)",
                        ("Dr. "+fake.name(), spec, dept, fake.phone_number()[:15]))
            did = cur.lastrowid
            doctor_ids.append(did)
            doctor_spec[did] = spec

    # Patients (200)
    patient_ids = []
    for _ in range(200):
        cur.execute("""INSERT INTO patients
            (first_name,last_name,email,phone,date_of_birth,gender,city,registered_date)
            VALUES(?,?,?,?,?,?,?,?)""",
            (fake.first_name(), fake.last_name(),
             fake.email() if random.random()>0.1 else None,
             fake.phone_number()[:15] if random.random()>0.1 else None,
             rdate(365*40), random.choice(["M","F"]),
             random.choice(CITIES), rdate(365)))
        patient_ids.append(cur.lastrowid)

    frequent = random.sample(patient_ids, 20)

    # Appointments (500)
    completed = []
    for _ in range(500):
        pid    = random.choice(frequent) if random.random()<0.35 else random.choice(patient_ids)
        did    = random.choice(doctor_ids)
        status = random.choices(STATUSES, weights=[0.2,0.55,0.15,0.10])[0]
        notes  = fake.sentence() if random.random()>0.4 else None
        cur.execute("INSERT INTO appointments(patient_id,doctor_id,appointment_date,status,notes) VALUES(?,?,?,?,?)",
                    (pid, did, rdatetime(365), status, notes))
        if status == "Completed":
            completed.append((cur.lastrowid, did, pid))

    # Treatments (350)
    for aid, did, _ in random.sample(completed, min(350, len(completed))):
        spec = doctor_spec[did]
        tname, base_cost, base_dur = random.choice(TREATMENT_MAP[spec])
        cur.execute("INSERT INTO treatments(appointment_id,treatment_name,cost,duration_minutes) VALUES(?,?,?,?)",
                    (aid, tname, round(base_cost*random.uniform(0.8,2.5),2), max(10,base_dur+random.randint(-5,20))))

    # Invoices (300)
    for pid in random.choices(patient_ids, k=300):
        total  = round(random.uniform(100,5000),2)
        status = random.choices(INV_ST, weights=[0.55,0.25,0.20])[0]
        paid   = total if status=="Paid" else round(total*random.uniform(0,0.5),2)
        cur.execute("INSERT INTO invoices(patient_id,invoice_date,total_amount,paid_amount,status) VALUES(?,?,?,?,?)",
                    (pid, rdate(365), total, paid, status))

    conn.commit()

    def count(t): return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print("✅ clinic.db created successfully!")
    print(f"   Patients     : {count('patients')}")
    print(f"   Doctors      : {count('doctors')}")
    print(f"   Appointments : {count('appointments')}")
    print(f"   Treatments   : {count('treatments')}")
    print(f"   Invoices     : {count('invoices')}")

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    seed(conn)
    conn.close()

if __name__ == "__main__":
    main()
