from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from file_storing_app.utils import CertificateAuthority

class Command(BaseCommand):
    help = 'Initialize the Certificate Authority and create a self-signed certificate'
    def handle(self, *args, **kwargs):
        if default_storage.exists('ca_private_key.pem') or default_storage.exists('ca_cert.pem'):
            raise CommandError('CA files already exist; refusing to replace them.')
        ca = CertificateAuthority()
        ca.initialize_ca()
        self.stdout.write(self.style.SUCCESS('CA initialized and self-signed certificate created.'))
