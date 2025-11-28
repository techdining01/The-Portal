from celery import shared_task
from django.core.management import call_command
from django.core.mail import send_mail
from django.conf import settings
import subprocess
import os

@shared_task
def create_automated_backup(backup_type='full'):
    """
    Create automated database backup
    """
    try:
        # Call management command
        call_command('create_backup', type=backup_type)
        
        # Send success notification
        send_mail(
            f"Backup Completed - {backup_type}",
            f"The {backup_type} backup has been completed successfully.",
            settings.DEFAULT_FROM_EMAIL,
            ['admin@brillspay.edu'],
            fail_silently=False,
        )
        
        return f"Backup {backup_type} completed successfully"
    except Exception as e:
        # Send error notification
        send_mail(
            f"Backup Failed - {backup_type}",
            f"The {backup_type} backup failed with error: {str(e)}",
            settings.DEFAULT_FROM_EMAIL,
            ['admin@brillspay.edu'],
            fail_silently=False,
        )
        raise e

@shared_task
def backup_database_to_cloud():
    """
    Backup database to cloud storage (example with AWS S3)
    """
    try:
        # This would integrate with cloud storage
        # For now, we'll just create a local backup
        call_command('create_backup', type='full')
        
        # Example: Upload to S3 (you'd need boto3)
        # import boto3
        # s3 = boto3.client('s3')
        # s3.upload_file('backup_file_path', 'bucket_name', 'backup_file_name')
        
        return "Cloud backup initiated"
    except Exception as e:
        print(f"Cloud backup failed: {str(e)}")
        raise e