from django.contrib import admin
from .models import DatabaseBackup, CBTBackup, SalesReport

@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(admin.ModelAdmin):
    list_display = ['backup_type', 'file_size_mb', 'created_by', 'created_at']
    list_filter = ['backup_type', 'created_at']
    readonly_fields = ['file_size', 'created_at']
    
    def file_size_mb(self, obj):
        return f"{obj.file_size / (1024*1024):.2f} MB"
    file_size_mb.short_description = 'File Size'

@admin.register(CBTBackup)
class CBTBackupAdmin(admin.ModelAdmin):
    list_display = ['exam_name', 'student', 'exam_date', 'score', 'total_questions']
    list_filter = ['exam_date', 'exam_name']
    search_fields = ['exam_name', 'student__first_name', 'student__surname']

@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    list_display = ['period', 'start_date', 'end_date', 'total_sales', 'total_orders', 'generated_at']
    list_filter = ['period', 'generated_at']
    readonly_fields = ['generated_at']