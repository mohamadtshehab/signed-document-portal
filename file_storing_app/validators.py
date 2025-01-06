import os
from django.core.exceptions import ValidationError
from datetime import date
def validate_file_type(value):
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
    ext = os.path.splitext(value.name)[1]
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')
    
def validate_birth_date(value):
    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 18:
        raise ValidationError('User must be at least 18 years old.')
    
def validate_file_size(file, max_file_size = 10 * 1024 * 1024):
    if file.size > max_file_size:
        raise ValueError("File size exceeds the limit")