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

# -----------------------------
# Fake data generation settings
# -----------------------------
CLINIC_COUNT = 3
DOCTORS_PER_CLINIC = 2
PATIENTS_PER_CLINIC = 10
DEVICES_PER_CLINIC = 3
SESSIONS_PER_PATIENT = 5
REPORTS_PER_CLINIC = 5


def create_clinics():
    # Create multiple clinics with random data
    clinics = []
    for _ in range(CLINIC_COUNT):
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
    # Create clinic manager and doctors for a clinic
    short_id = str(clinic.clinic_id).split('-')[0]
    manager_username = f"manager_{short_id}"

    users = []

    # Create clinic manager if not exists
    if not User.objects.filter(username=manager_username).exists():
        manager = User.objects.create_user(
            username=manager_username,
            password="password123",
            role="clinic_manager",
            clinic=clinic,
            email=fake.email()
        )
        users.append(manager)

    # Create doctors for the clinic
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

    print(f"  ✔ Users created for {clinic.name}")
    return users


def create_firmware(device):
    """
    Create a firmware record and attach a fake binary file
    (used for testing secure firmware download)
    """
    version = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 20)}"
    file_content = f"Fake firmware binary for {device.serial_number} v{version}".encode('utf-8')
    checksum = hashlib.sha256(file_content).hexdigest()

    fw = Firmware(
        device=device,
        firmware_version=version,
        release_notes=fake.sentence(),
        checksum=checksum
    )

    # Save fake firmware file to storage
    file_name = f"fw_{device.serial_number}_{version}.bin"
    fw.file_path.save(file_name, ContentFile(file_content))
    fw.save()

    return version


def create_devices(clinic):
    # Create devices, licenses, and firmware for a clinic
    devices = []
    for i in range(DEVICES_PER_CLINIC):
        device = Device.objects.create(
            serial_number=f"RF-{fake.unique.random_int(10000, 99999)}",
            clinic=clinic,
            device_type="RF Microneedling",
            category="Dermatology",
            firmware_version="1.0.0",  # Temporary version, updated later
            status='active',
            api_key=secrets.token_urlsafe(32),
            last_online=timezone.now(),
            installation_date=timezone.now().date() - timedelta(days=random.randint(100, 365)),
            last_service_date=timezone.now().date() - timedelta(days=random.randint(10, 60))
        )

        # Assign an active license to the device
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

    print(f"  ✔ {len(devices)} Devices created")
    return devices


def create_patients(clinic):
    # Create patients with structured personal data
    patients = []
    for _ in range(PATIENTS_PER_CLINIC):
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
            clinic=clinic,
            personal_data=personal_data,
            patient_code=f"P-{fake.unique.random_int(1000, 9999)}",
            consent={"signed": True, "date": str(timezone.now().date())},
            indication={"notes": "Routine checkup and RF treatment"}
        )
        patients.append(patient)

    print(f"  ✔ {len(patients)} Patients created")
    return patients


def create_sessions(clinic, patients, devices):
    # Create treatment sessions for each patient
    count = 0
    for patient in patients:
        for _ in range(SESSIONS_PER_PATIENT):
            device = random.choice(devices)
            days_ago = random.randint(0, 30)
            session_time = timezone.now() - timedelta(days=days_ago, hours=random.randint(1, 5))
            end_time = session_time + timedelta(minutes=random.randint(15, 60))

            Session.objects.create(
                clinic=clinic,
                patient=patient,
                device=device,
                start_time=session_time,
                ended_at=end_time,
                status='completed',
                cost=random.choice([500000, 750000, 1500000, 2500000]),
                summary={
                    "areas_treated": random.choices(["Face", "Neck", "Abdomen", "Thighs"], k=2),
                    "parameters": {"energy": random.randint(10, 50), "shots": random.randint(200, 1500)}
                }
            )
            count += 1
    print(f"  ✔ {count} Sessions created.")


def create_reports(clinic, users, patients):
    """
    Create ready-to-download reports for testing
    report listing and download endpoints
    """
    count = 0
    for _ in range(REPORTS_PER_CLINIC):
        report_type = random.choice(['clinic_summary', 'patient_history', 'device_usage'])
        user = random.choice(users)

        # Assign a random patient only for patient history reports
        target_patient = random.choice(patients) if report_type == 'patient_history' else None

        report = ReportGeneration.objects.create(
            clinic=clinic,
            patient=target_patient,
            generated_by=user,
            report_type=report_type,
            created_at=timezone.now() - timedelta(days=random.randint(0, 5))
        )

        # Create a dummy Excel file so download endpoints work correctly
        dummy_content = f"Dummy Excel Content for Report {report.id}".encode('utf-8')
        file_name = f"{report_type}_{uuid.uuid4().hex[:6]}.xlsx"

        report.file_path.save(file_name, ContentFile(dummy_content))
        report.save()
        count += 1

    print(f"  ✔ {count} Reports generated (Ready to download)")


# -----------------------------
# Script execution
# -----------------------------
print("🚀 Starting Comprehensive Data Generation...")

try:
    clinics_list = create_clinics()

    for clinic in clinics_list:
        users = create_users(clinic)
        devices_list = create_devices(clinic)
        patients_list = create_patients(clinic)

        if devices_list and patients_list:
            create_sessions(clinic, patients_list, devices_list)

        if users:
            create_reports(clinic, users, patients_list)

    print("\n✅ All fake data generated successfully!")

    # Print sample login credentials for quick testing
    if clinics_list:
        short_id = str(clinics_list[0].clinic_id).split('-')[0]
        print("ℹ️  Login Credentials:")
        print(f"   Manager: manager_{short_id}")
        print(f"   Doctor: doc_{short_id}_0")
        print("   Password: password123")

except Exception as e:
    print(f"\n❌ Error: {e}")

# python3 manage.py shell < scripts/fake_data_generator.py
