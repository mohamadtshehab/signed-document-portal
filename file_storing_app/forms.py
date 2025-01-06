from django import forms
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


class LoginForm(forms.Form):
    phone_number = forms.CharField(max_length=10)
    password = forms.CharField(widget=forms.PasswordInput)