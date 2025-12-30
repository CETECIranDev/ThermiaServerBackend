import uuid
import random
import secrets
import hashlib
from faker import Faker
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from accounts.models import Clinic
from patients.models import Patient
from devices.models import Device, License, Firmware
from patient_sessions.models import Session
from reports.models import ReportGeneration

fake = Faker()
User = get_user_model()

CLINIC_COUNT = 3
DOCTORS_PER_CLINIC = 2
PATIENTS_PER_CLINIC = 6
DEVICES_PER_CLINIC = 3
SESSIONS_PER_PATIENT = 4
REPORTS_PER_CLINIC = 2


def create_clinics():
    clinics = []
    for _ in range(CLINIC_COUNT):
        c_id = str(uuid.uuid4())
        clinic = Clinic.objects.create(
            clinic_id=c_id,
            name=f"{fake.last_name()} Clinic",
            address=fake.address(),
            phone=fake.phone_number()
        )
        clinics.append(clinic)
    print(f"✔ {len(clinics)} Clinics created.")
    return clinics


def create_users(clinic):
    # Clinic Manager
    short_id = str(clinic.clinic_id).split('-')[0]
    manager_username = f"manager_{short_id}"
    users = []

    if not User.objects.filter(username=manager_username).exists():
        manager = User.objects.create_user(
            username=manager_username,
            password="password123",
            role="clinic_manager",
            clinic=clinic,
            email=fake.email()
        )
        users.append(manager)

    # Doctors
    for i in range(DOCTORS_PER_CLINIC):
        doc_username = f"doc_{short_id}_{i}"
        if not User.objects.filter(username=doc_username).exists():
            doc = User.objects.create_user(
                username=doc_username,
                password="password123",
                role="doctor",
                clinic=clinic,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email()
            )
            users.append(doc)
    return users


def create_firmware(device):
    version = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 20)}"
    file_content = f"Fake firmware binary for {device.serial_number}".encode('utf-8')
    checksum = hashlib.sha256(file_content).hexdigest()

    fw = Firmware(
        device=device,
        firmware_version=version,
        release_notes=fake.sentence(),
        checksum=checksum
    )
    file_name = f"fw_{device.serial_number}_{version}.bin"
    fw.file_path.save(file_name, ContentFile(file_content))
    fw.save()
    return version


def create_devices(clinic):
    devices = []
    for i in range(DEVICES_PER_CLINIC):
        d_id = str(uuid.uuid4())
        device = Device.objects.create(
            device_id=d_id,
            serial_number=f"RF-{fake.unique.random_int(10000, 99999)}",
            clinic=clinic,
            device_type="RF Microneedling",
            category="Dermatology",
            firmware_version="1.0.0",
            status='active',
            api_key=secrets.token_urlsafe(32),
            last_online=timezone.now(),
            installation_date=timezone.now().date() - timedelta(days=random.randint(100, 365))
        )

        License.objects.create(
            device=device,
            license_type='full',
            status='active',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365)
        )
        create_firmware(device)
        devices.append(device)

    print(f"  ✔ {len(devices)} Devices created")
    return devices


def create_patients(clinic):
    patients = []
    for _ in range(PATIENTS_PER_CLINIC):
        p_id = str(uuid.uuid4())

        personal_data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "gender": random.choice(["Male", "Female"]),
            "birth_date": str(fake.date_of_birth(minimum_age=18, maximum_age=80)),
            "national_id": fake.numerify(text='##########'),
            "phone": fake.phone_number(),
            "email": fake.email(),
            "address": fake.address().replace('\n', ', ')
        }

        patient = Patient.objects.create(
            patient_id=p_id,
            clinic=clinic,
            personal_data=personal_data,
            patient_code=f"P-{fake.unique.random_int(1000, 9999)}",
            last_visit=timezone.now().date() - timedelta(days=random.randint(100, 365)),
            consent={"signed": True},
            indication={"notes": "Checkup"}
        )
        patients.append(patient)

    print(f"  ✔ {len(patients)} Patients created")
    return patients


def create_sessions(clinic, patients, devices):
    count = 0
    for patient in patients:
        latest_session_date = None

        for _ in range(SESSIONS_PER_PATIENT):
            device = random.choice(devices)
            days_ago = random.randint(0, 30)
            session_time = timezone.now() - timedelta(days=days_ago, hours=random.randint(1, 5))
            end_time = session_time + timedelta(minutes=random.randint(15, 45))

            Session.objects.create(
                clinic=clinic,
                patient=patient,
                device=device,
                start_time=session_time,
                ended_at=end_time,
                status='completed',
                cost=random.choice([500000, 750000, 1200000, 2000000]),
                summary={
                    "areas_treated": random.choices(["Face", "Neck", "Body", "Arms"], k=2),
                    "parameters": {"energy": random.randint(10, 50), "shots": random.randint(200, 1000)}
                }
            )

            if latest_session_date is None or session_time > latest_session_date:
                latest_session_date = session_time

            count += 1

        if latest_session_date:
            patient.last_visit = latest_session_date
            patient.save()

    print(f"  ✔ {count} Sessions created (and patient visits updated).")


def create_reports(clinic, users, patients):
    count = 0
    for _ in range(REPORTS_PER_CLINIC):
        user = random.choice(users)
        report = ReportGeneration.objects.create(
            clinic=clinic,
            patient=random.choice(patients),
            generated_by=user,
            report_type='clinic_summary',
            created_at=timezone.now()
        )
        count += 1
    print(f"  ✔ {count} Reports created")


print("🚀 Starting Data Generation...")
try:
    clinics_list = create_clinics()
    for clinic in clinics_list:
        users = create_users(clinic)
        devices = create_devices(clinic)
        patients = create_patients(clinic)
        if devices and patients:
            create_sessions(clinic, patients, devices)
        if users:
            create_reports(clinic, users, patients)

    print("\n✅ DONE! No Overflow Errors.")
    if clinics_list:
        short_id = str(clinics_list[0].clinic_id).split('-')[0]
        print(f"Login: manager_{short_id} / password123")

except Exception as e:
    print(f"\n❌ Error: {e}")

# python3 manage.py shell < scripts/fake_data_generator.py
