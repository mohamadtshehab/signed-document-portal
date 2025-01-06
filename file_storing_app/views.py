from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse, Http404
from django.core.exceptions import ValidationError
from django.conf import settings
from django_ratelimit.decorators import ratelimit
from datetime import date
from urllib.parse import quote
from twilio.rest import Client
from .forms import *
from .models import Document
from .utils import CertificateAuthority, MalwareScanner, Hasher, require_registration_session

def success(request):
    return render(request, 'success.html')

@ratelimit(key='ip', rate='5/m', method='GET', block=True)
def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('documents')
        else:
            return redirect('uploads')
    return render(request, 'home.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def uploads(request):
    if request.user.is_staff:
        return HttpResponseForbidden("You're not authorized to upload documents.")

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            if not MalwareScanner.is_safe(request.FILES['file']):
                raise ValidationError("Malware detected. File removed")
            
            document.user = request.user
            document.hash = Hasher.generate_file_hash(request.FILES['file'])
            
            ca = CertificateAuthority()
            ca_private_key = ca.load_ca_private_key()
            ca_certificate = ca.load_ca_certificate()
            
            document_signature = ca.sign_document(request.FILES['file'], ca_private_key)
            document.signature = document_signature
            
            document.save()
            return redirect('success')
    else:
        form = DocumentForm()
    return render(request, 'upload.html', {'form': form})


@login_required
def documents(request):
    if request.user.is_staff:
        national_id = request.GET.get('national_id', '')
        if national_id:
            files = Document.objects.filter(user__national_id=national_id)
        else:
            files = Document.objects.all()
    else:
        files = Document.objects.filter(user=request.user)

    context = {
        'files': files,
        'is_staff': request.user.is_staff,
    }
    return render(request, 'documents.html', context)

@login_required
def download(request, file_id):
    try:
        document = Document.objects.get(id=file_id)
    except Document.DoesNotExist:
        raise Http404("File does not exist")

    if not request.user.is_staff and document.user != request.user:
        return HttpResponseForbidden("You're not authorized to download this document.")

    current_hash = Hasher.generate_file_hash(document.file)
    if current_hash != document.hash:
        return HttpResponseForbidden("The file may be corrupted.")

    ca = CertificateAuthority()
    ca_certificate = ca.load_ca_certificate()
    
    if not ca.verify_document(document.file, document.signature, ca_certificate):
        return HttpResponseForbidden("Document signature verification failed.")

    response = HttpResponse(document.file, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename={quote(document.file.name)}'
    return response

User = get_user_model()

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data.get('phone_number')
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            try:
                to = '+963' + str(phone_number[1:])
                verification = client.verify.services(settings.TWILIO_SERVICE_SID).verifications.create(to=to, channel='sms')
                
                user_data = form.cleaned_data
                for key, value in user_data.items():
                    if isinstance(value, date):
                        user_data[key] = value.isoformat()
                
                request.session['phone_number'] = phone_number
                request.session['user_data'] = user_data
                return redirect('verify')
            except Exception as e:
                form.add_error(None, f'Error sending OTP: {e}')
        else:
            form.add_error(None, 'Form is not valid.')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

@require_registration_session
def verify(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        phone_number = request.session.get('phone_number')
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        to = '+963' + str(phone_number[1:])
        verification_check = client.verify.services(settings.TWILIO_SERVICE_SID).verification_checks.create(to=to, code=code)
        
        if verification_check.status == 'approved':
            user_data = request.session.get('user_data')
            user_data.pop('confirm_password', None)
            user = User.objects.create_user(**user_data)
            user.save()
            auth_login(request, user, backend='file_storing_app.backends.PhoneNumberBackend')
            return redirect('home')
        else:
            return render(request, 'verify.html', {'error': 'Invalid OTP. Please try again.'})
    
    return render(request, 'verify.html')

def login(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('documents')
        else:
            return redirect('uploads')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data.get('phone_number')
            password = form.cleaned_data.get('password')
            user = authenticate(request, phone_number=phone_number, password=password)
            if user is not None:
                auth_login(request, user)
                if user.is_staff:
                    return redirect('documents')
                else:
                    return redirect('uploads')
            else:
                form.add_error(None, 'Invalid phone number or password.')
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})
