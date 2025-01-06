from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
import datetime
import hashlib
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import subprocess
from django.core.exceptions import ValidationError
import os
import tempfile
from django.shortcuts import render, redirect
from functools import wraps

class CertificateAuthority:
    def generate_ca_key_pair(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        default_storage.save("ca_private_key.pem", ContentFile(key_bytes))
        return private_key

    def create_self_signed_certificate(self, private_key):
        subject = issuer = x509.Name([
            x509.NameAttribute(x509.NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(x509.NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(x509.NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, "My CA"),
            x509.NameAttribute(x509.NameOID.COMMON_NAME, "myca.example.com"),
        ])

        certificate = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365 * 10)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).sign(private_key, hashes.SHA256())

        cert_bytes = certificate.public_bytes(encoding=serialization.Encoding.PEM)
        default_storage.save("ca_cert.pem", ContentFile(cert_bytes))
        return certificate

    def initialize_ca(self):
        private_key = self.generate_ca_key_pair()
        certificate = self.create_self_signed_certificate(private_key)
        return private_key, certificate

    def generate_server_key_pair_and_csr(self):
        server_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
            x509.NameAttribute(x509.NameOID.COMMON_NAME, "myserver.example.com"),
        ])).sign(server_key, hashes.SHA256())

        key_bytes = server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        csr_bytes = csr.public_bytes(encoding=serialization.Encoding.PEM)

        default_storage.save("server_key.pem", ContentFile(key_bytes))
        default_storage.save("server_csr.pem", ContentFile(csr_bytes))

        return csr, server_key

    def sign_the_csr_using_the_ca(self, csr, private_key, certificate):
        server_cert = x509.CertificateBuilder().subject_name(
            csr.subject
        ).issuer_name(
            certificate.subject
        ).public_key(
            csr.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).sign(private_key, hashes.SHA256())

        cert_bytes = server_cert.public_bytes(encoding=serialization.Encoding.PEM)
        default_storage.save("server_cert.pem", ContentFile(cert_bytes))

    def issue_server_certificate(self):
        csr, server_key = self.generate_server_key_pair_and_csr()
        ca_private_key, ca_certificate = self.initialize_ca()
        self.sign_the_csr_using_the_ca(csr, ca_private_key, ca_certificate)

    def verify_certificate(self, certificate, server_cert):
        try:
            public_key = certificate.public_key()
            public_key.verify(
                server_cert.signature,
                server_cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            print("Certificate is valid.")
        except Exception as e:
            print("Certificate verification failed:", e)
            
    def load_ca_private_key(self):
            """Loads the CA private key using default storage."""
            with default_storage.open("ca_private_key.pem", "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,
                )
            return private_key

    def load_ca_certificate(self):
        """Loads the CA certificate using default storage."""
        with default_storage.open("ca_cert.pem", "rb") as cert_file:
            certificate = x509.load_pem_x509_certificate(cert_file.read())
        return certificate

    def sign_document(self, document, private_key):
        hasher = hashlib.sha256()
        for chunk in document.chunks():
            hasher.update(chunk)
        document_hash = hasher.digest()
        signature = private_key.sign(
            document_hash,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return signature

    def verify_document(self, document, signature, certificate):
        hasher = hashlib.sha256()
        for chunk in document.chunks():
            hasher.update(chunk)
        document_hash = hasher.digest()
        public_key = certificate.public_key()
        try:
            public_key.verify(
                signature,
                document_hash,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            return False
        
class MalwareScanner:
    @staticmethod
    def is_safe(file):
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file.read())
            temp_file.close()
            result = subprocess.run(['MpCmdRun.exe', '-Scan', '-ScanType', '3', '-File', temp_file.name], stdout=subprocess.PIPE)
            if b'found no threats' not in result.stdout:
                os.remove(temp_file.name)
                raise ValidationError('File contains a virus and has been deleted.')
            os.remove(temp_file.name)
        return True
    

class Hasher:
    @staticmethod
    def generate_file_hash(file):
        hasher = hashlib.sha256()
        for chunk in file.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()
    

def require_registration_session(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('phone_number') or not request.session.get('user_data'):
            return redirect('registeration')
        return view_func(request, *args, **kwargs)
    return _wrapped_view