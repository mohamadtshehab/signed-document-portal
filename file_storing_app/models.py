from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from .validators import validate_file_type, validate_birth_date, validate_file_size
from .managers import CustomUserManager
import re, os, uuid
from pathlib import Path

class CustomUser(AbstractUser):
    username = None
    birth_date = models.DateField(verbose_name='Birth Date', 
                                  null=False, 
                                  blank=False,
                                  validators=[validate_birth_date])
    national_id = models.CharField(
        max_length=11, 
        unique=True, 
        blank=False, 
        null=False, 
        validators=[RegexValidator(
            r'^\d{11}$', 'Enter an 11-digit number.'
            )]
    )
    phone_number = models.CharField(
        max_length=10, 
        unique=True, 
        blank=False, 
        null=False, 
        validators=[RegexValidator(
            r'^09\d{8}$', 'Enter a 10-digit number starting with 09.'
            )]
    )

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'birth_date', 'national_id']
    objects = CustomUserManager()

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

class Document(models.Model):
    file = models.FileField(upload_to='documents/',
                            null=False, 
                            blank=False,
                            validators=[validate_file_type, validate_file_size],
                            )
    def save(self, *args, **kwargs):

        def sanitize_filename(filename, max_length=30):

            filename = re.sub(r'[\\/:*?"<>|]', '_', filename)

            name, ext = os.path.splitext(os.path.basename(filename))

            if len(name) > max_length:
                name = name[:max_length]

            unique_suffix = uuid.uuid4().hex[:8]

            sanitized_filename = f"{name}_{unique_suffix}{ext}"

            return sanitized_filename

        if self.file and self.file.name:
            self.file.name = sanitize_filename(self.file.name)

        super().save(*args, **kwargs)
    user = models.ForeignKey(on_delete=models.DO_NOTHING,
                             to=CustomUser,
                             null=False,
                             blank=False)
    
    hash = models.CharField(max_length=64,
                            null=False, 
                            blank=False)
    signature = models.BinaryField(default=bytes(256))
    
    def __str__(self):
        return self.file.name
