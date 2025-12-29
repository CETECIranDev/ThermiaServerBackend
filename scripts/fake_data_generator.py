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

fake = Faker()
User = get_user_model()

# -----------------------------
# Fake data generation settings
# -----------------------------
CLINIC_COUNT = 3
DOCTORS_PER_CLINIC = 2
PATIENTS_PER_CLINIC = 6
DEVICES_PER_CLINIC = 3
SESSIONS_PER_PATIENT = 4


def create_clinics():
    clinics = []
    for _ in range(CLINIC_COUNT):
        # Create clinic with random UUID
        clinic = Clinic.objects.create(
            clinic_id=uuid.uuid4(),
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
    username = f"manager_{short_id}"

    if not User.objects.filter(username=username).exists():
        User.objects.create_user(
            username=username,
            password="password123",
            role="clinic_manager",
            clinic=clinic,
            email=fake.email()
        )

    # Doctors
    doctors = []
    for i in range(DOCTORS_PER_CLINIC):
        doc_username = f"doc_{short_id}_{i}"
        if not User.objects.filter(username=doc_username).exists():
            doc = User.objects.create_user(
                username=doc_username,
                password="password123",
                role="doctor",
                clinic=clinic,
                first_name=fake.first_name(),
                last_name=fake.last_name()
            )
            doctors.append(doc)

    print(f"  ✔ Users created for {clinic.name}")
    return doctors


def create_firmware(device):
    """Create a firmware record and a physical firmware file for a device"""
    version = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 20)}"
    file_content = f"Fake firmware binary for {device.serial_number} v{version}".encode('utf-8')
    checksum = hashlib.sha256(file_content).hexdigest()

    fw = Firmware(
        device=device,
        firmware_version=version,
        release_notes=fake.sentence(),
        checksum=checksum
    )

    # Save fake firmware file
    file_name = f"fw_{device.serial_number}_{version}.bin"
    fw.file_path.save(file_name, ContentFile(file_content))
    fw.save()

    return version


def create_devices(clinic):
    devices = []
    for i in range(DEVICES_PER_CLINIC):
        device = Device.objects.create(
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

        # Create license
        License.objects.create(
            device=device,
            license_type='full',
            status='active',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365)
        )

        # Create firmware and update device version
        latest_version = create_firmware(device)
        device.firmware_version = latest_version
        device.save()

        devices.append(device)

    print(f"  ✔ {len(devices)} Devices (with Firmware) created")
    return devices


def create_patients(clinic):
    patients = []
    for _ in range(PATIENTS_PER_CLINIC):
        # Use numerify to avoid integer overflow
        national_id = fake.numerify(text='##########')

        personal_data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "phone": fake.phone_number(),
            "national_id": national_id,
            "gender": random.choice(["Male", "Female"]),
            "age": random.randint(18, 60)
        }

        patient = Patient.objects.create(
            clinic=clinic,
            personal_data=personal_data,
            patient_code=f"P-{fake.unique.random_int(1000, 9999)}",
            consent={"signed": True},
            indication={"notes": "Checkup"}
        )
        patients.append(patient)

    print(f"  ✔ {len(patients)} Patients created")
    return patients


def create_sessions(clinic, patients, devices):
    count = 0
    for patient in patients:
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
            count += 1
    print(f"  ✔ {count} Sessions created.")


# -----------------------------
# Script execution
# -----------------------------
print("🚀 Starting Complete Data Generation...")

try:
    clinics_list = create_clinics()

    for clinic in clinics_list:
        create_users(clinic)
        devices_list = create_devices(clinic)
        patients_list = create_patients(clinic)

        if devices_list and patients_list:
            create_sessions(clinic, patients_list, devices_list)

    print("\n✅ All fake data generated successfully!")

    # Print login info using clinic_id
    if clinics_list:
        short_id = str(clinics_list[0].clinic_id).split('-')[0]
        print("ℹ️  You can log in with:")
        print(f"   Username: manager_{short_id}")
        print("   Password: password123")

except Exception as e:
    print(f"\n❌ Error: {e}")

# python3 manage.py shell < scripts/fake_data_generator.py
