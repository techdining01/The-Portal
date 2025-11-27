
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from .models import BackupRecord, BackupSchedule, RestorePoint, AuditLog
from .backup_service import BackupService
import json
import os

def staff_required(view_func):
    """Decorator to ensure user is staff member"""
    actual_decorator = user_passes_test(
        lambda u: u.is_staff,
        login_url='/admin/login/'
    )
    return actual_decorator(view_func)

@login_required
@staff_required
def backup_management(request):
    """Main backup management dashboard"""
    backup_records = BackupRecord.objects.all().order_by('-created_at')[:50]
    backup_schedules = BackupSchedule.objects.filter(is_active=True)
    restore_points = RestorePoint.objects.all().order_by('-created_at')[:20]
    
    # Get backup statistics
    total_backups = BackupRecord.objects.count()
    completed_backups = BackupRecord.objects.filter(status='completed').count()
    total_size = sum(backup.file_size for backup in BackupRecord.objects.filter(status='completed'))
    
    context = {
        'backup_records': backup_records,
        'backup_schedules': backup_schedules,
        'restore_points': restore_points,
        'stats': {
            'total_backups': total_backups,
            'completed_backups': completed_backups,
            'total_size': total_size,
        }
    }
    return render(request, 'admin/backup_management.html', context)

@login_required
@staff_required
@require_POST
def create_backup(request):
    """Create a new backup manually"""
    backup_type = request.POST.get('backup_type', 'database')
    description = request.POST.get('description', '')
    
    backup_service = BackupService()
    
    try:
        if backup_type == 'database':
            backup_record = backup_service.create_database_backup(
                description=description,
                is_automated=False,
                created_by=request.user
            )
        elif backup_type == 'transactions':
            backup_record = backup_service.create_transactions_backup(
                description=description,
                is_automated=False,
                created_by=request.user
            )
        elif backup_type == 'payments':
            backup_record = backup_service.create_payments_backup(
                description=description,
                is_automated=False,
                created_by=request.user
            )
        elif backup_type == 'audit_logs':
            backup_record = backup_service.create_audit_logs_backup(
                description=description,
                is_automated=False,
                created_by=request.user
            )
        else:
            backup_record = backup_service.create_full_backup(
                description=description,
                is_automated=False,
                created_by=request.user
            )
        
        if backup_record:
            messages.success(request, f"Backup '{backup_record.backup_name}' created successfully!")
        else:
            messages.error(request, "Failed to create backup.")
    
    except Exception as e:
        messages.error(request, f"Error creating backup: {str(e)}")
    
    return redirect('admin_backup_management')

@login_required
@staff_required
def view_backup(request, backup_id):
    """View backup details"""
    backup_record = get_object_or_404(BackupRecord, id=backup_id)
    
    # Check if backup file exists
    file_exists = os.path.exists(backup_record.file_path) if backup_record.file_path else False
    
    context = {
        'backup': backup_record,
        'file_exists': file_exists,
    }
    return render(request, 'admin/view_backup.html', context)

@login_required
@staff_required
@require_POST
def delete_backup(request, backup_id):
    """Delete a backup record and file"""
    backup_record = get_object_or_404(BackupRecord, id=backup_id)
    
    try:
        # Delete physical file
        if backup_record.file_path and os.path.exists(backup_record.file_path):
            os.remove(backup_record.file_path)
        
        backup_name = backup_record.backup_name
        backup_record.delete()
        
        messages.success(request, f"Backup '{backup_name}' deleted successfully!")
    
    except Exception as e:
        messages.error(request, f"Error deleting backup: {str(e)}")
    
    return redirect('admin_backup_management')

@login_required
@staff_required
def verify_backup(request, backup_id):
    """Verify backup integrity"""
    backup_record = get_object_or_404(BackupRecord, id=backup_id)
    
    try:
        is_valid = backup_record.verify_integrity()
        
        if is_valid:
            messages.success(request, f"Backup '{backup_record.backup_name}' verified successfully!")
        else:
            messages.error(request, f"Backup verification failed for '{backup_record.backup_name}'!")
    
    except Exception as e:
        messages.error(request, f"Error verifying backup: {str(e)}")
    
    return redirect('admin_backup_management')

@login_required
@staff_required
def download_backup(request, backup_id):
    """Download backup file"""
    backup_record = get_object_or_404(BackupRecord, id=backup_id)
    
    if not backup_record.file_path or not os.path.exists(backup_record.file_path):
        messages.error(request, "Backup file not found.")
        return redirect('admin_backup_management')
    
    try:
        with open(backup_record.file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{backup_record.filename}"'
            return response
    
    except Exception as e:
        messages.error(request, f"Error downloading backup: {str(e)}")
        return redirect('admin_backup_management')

@login_required
@staff_required
def manual_backup(request):
    """Manual backup creation page"""
    if request.method == 'POST':
        return create_backup(request)
    
    return render(request, 'admin/manual_backup.html')

@login_required
@staff_required
def audit_logs(request):
    """View audit logs"""
    logs = AuditLog.objects.all().order_by('-created_at')[:100]
    
    # Filter options
    action_types = AuditLog.ACTION_TYPES
    table_names = AuditLog.objects.values_list('table_name', flat=True).distinct()
    
    # Apply filters
    action_filter = request.GET.get('action_type')
    table_filter = request.GET.get('table_name')
    user_filter = request.GET.get('user')
    
    if action_filter:
        logs = logs.filter(action_type=action_filter)
    if table_filter:
        logs = logs.filter(table_name=table_filter)
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    
    context = {
        'logs': logs,
        'action_types': action_types,
        'table_names': table_names,
        'filters': {
            'action_type': action_filter,
            'table_name': table_filter,
            'user': user_filter,
        }
    }
    return render(request, 'admin/audit_logs.html', context)

# API endpoints for AJAX
@login_required
@staff_required
def api_backup_status(request):
    """Get backup status for dashboard"""
    try:
        total = BackupRecord.objects.count()
        completed = BackupRecord.objects.filter(status='completed').count()
        failed = BackupRecord.objects.filter(status='failed').count()
        in_progress = BackupRecord.objects.filter(status='in_progress').count()
        
        recent_backups = BackupRecord.objects.filter(
            status='completed'
        ).order_by('-created_at')[:5]
        
        data = {
            'total': total,
            'completed': completed,
            'failed': failed,
            'in_progress': in_progress,
            'recent_backups': [
                {
                    'name': backup.backup_name,
                    'type': backup.backup_type,
                    'size': backup.file_size_display,
                    'date': backup.created_at.strftime('%Y-%m-%d %H:%M'),
                }
                for backup in recent_backups
            ]
        }
        
        return JsonResponse({'success': True, 'data': data})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@staff_required
@require_POST
def api_cleanup_backups(request):
    """Clean up old backups"""
    try:
        data = json.loads(request.body)
        days_to_keep = data.get('days_to_keep', 30)
        
        backup_service = BackupService()
        deleted_files, deleted_records = backup_service.cleanup_old_backups(days_to_keep)
        
        return JsonResponse({
            'success': True,
            'deleted_files': deleted_files,
            'deleted_records': deleted_records,
            'message': f'Cleaned up {deleted_files} files and {deleted_records} records'
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})