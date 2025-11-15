import os
import subprocess
import datetime
import boto3
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from cryptography.fernet import Fernet
from cores.models import BackupLog


def encrypt_file(filepath):
    """Encrypt file before uploading to S3."""
    fernet = Fernet(settings.FERNET_KEY)
    with open(filepath, "rb") as f:
        data = f.read()
    encrypted = fernet.encrypt(data)
    with open(filepath, "wb") as f:
        f.write(encrypted)


def backup_and_cleanup(auto=True):
    """Performs local + S3 backup and cleanup."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(settings.BACKUP_DIR, exist_ok=True)
    filename = f"cbt_backup_{timestamp}.json"
    filepath = os.path.join(settings.BACKUP_DIR, filename)

    # Local backup
    subprocess.call([
        "python", "manage.py", "dumpdata",
        "--natural-primary", "--natural-foreign",
        "--indent", "2", "-o", filepath
    ])

    # Encrypt
    encrypt_file(filepath)

    # Upload to S3
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    try:
        s3.upload_file(filepath, settings.AWS_STORAGE_BUCKET_NAME, f"backups/{filename}")
        status = "Uploaded to S3"
    except Exception as e:
        status = f"Cloud upload failed: {e}"

    # Save backup log
    BackupLog.objects.create(filename=filename, status=status, is_auto=auto)


def start_scheduler():
    """Start job scheduler without DB jobstore."""
    scheduler = BackgroundScheduler()

    # Run every minute
    scheduler.add_job(
        backup_and_cleanup,
        trigger="interval",
        minutes=1,
        id="backup_job",
        replace_existing=True
    )

    scheduler.start()
    print("⏱ APScheduler running (every 1 minute).")
