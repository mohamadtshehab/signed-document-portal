from django.core.management.base import BaseCommand
from ...utils import CertificateClient

class Command(BaseCommand):
    help = 'Request a CSR from the CA server over API.'

    def add_arguments(self, parser):
        parser.add_argument('server_name', type=str, help='Name of the server requesting the CSR.')
        parser.add_argument('organization_name', type=str, help='Name of the organization requesting the CSR.')
        
    def handle(self, *args, **options):
        # Initialize the CertificateClient
        client = CertificateClient()

        # Retrieve the server name from arguments
        server_name = options['server_name']
        organization_name = options['organization_name']
        # Generate CSR and private key using the client
        csr, private_key = client.generate_csr(server_name, organization_name)

        # Send the CSR and server name to the CA server using the client
        response = client.request_csr_from_ca(csr, server_name)

        # Handle the response
        if response.status_code == 201:
            self.stdout.write(self.style.SUCCESS('CSR successfully submitted to CA server.'))
            self.stdout.write(response.json())
        else:
            self.stdout.write(self.style.ERROR(f'Failed to submit CSR. Status code: {response.status_code}'))
            self.stdout.write(response.text)

        # Save the private key using the client
        client.save_private_key(private_key, 'private_key.pem')
        self.stdout.write(self.style.SUCCESS('Private key saved as private_key.pem.'))