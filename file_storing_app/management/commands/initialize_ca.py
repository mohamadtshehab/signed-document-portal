from django.core.management.base import BaseCommand
from file_storing_app.utils import CertificateAuthority

class Command(BaseCommand):
    help = 'Initialize the Certificate Authority and create a self-signed certificate'
    def handle(self, *args, **kwargs):
        ca = CertificateAuthority()
        ca_private_key, ca_certificate = ca.initialize_ca()
        self.stdout.write(self.style.SUCCESS('CA initialized and self-signed certificate created.'))