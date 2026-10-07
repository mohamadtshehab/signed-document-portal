from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import Document, CustomUser


    
class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ('file',)

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label='Repeat Password')
    birth_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'birth_date', 'national_id', 'phone_number', 'password')

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        if password and password != cleaned_data.get('confirm_password'):
            self.add_error('confirm_password', 'Passwords do not match.')
        if password:
            validate_password(password)
        return cleaned_data


class LoginForm(forms.Form):
    phone_number = forms.CharField(max_length=10)
    password = forms.CharField(widget=forms.PasswordInput)
