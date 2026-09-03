from django import forms
from django.core.validators import EmailValidator
import re

from .models import Contact, PersonalDetails, OrganizationDetails, ContactPhone, ContactEmail

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['contact_type']
        widgets = {
            'contact_type': forms.RadioSelect(choices=Contact.ContactType)
        }

class PersonalDetailsForm(forms.ModelForm):
    class Meta:
        model = PersonalDetails
        fields = ['first_name', 'second_name', 'middle_name', 'last_name',
                  'first_name_ar', 'second_name_ar', 'middle_name_ar', 'last_name_ar']
        widgets = {
            'second_name': forms.TextInput(attrs={'required': False}),
            'middle_name': forms.TextInput(attrs={'required': False}),
            'second_name_ar': forms.TextInput(attrs={'required': False}),
            'middle_name_ar': forms.TextInput(attrs={'required': False}),
        }




class OrganizationDetailsForm(forms.ModelForm):
    class Meta:
        model = OrganizationDetails
        fields = ['legal_name', 'trade_name', 'legal_name_ar', 'trade_name_ar']

    def clean(self):
        cleaned_data = super().clean()

        # LOG 1: See the data exactly as the browser sent it
        print("\n--- [Form Clean Start] Raw Cleaned Data ---")
        print(f"Before processing: {cleaned_data}")

        null_if_blank_fields = ['legal_name_ar', 'trade_name_ar']

        for field in null_if_blank_fields:
            value = cleaned_data.get(field)

            # If the value is a string and is empty/whitespace
            if isinstance(value, str) and not value.strip():
                # LOG 2: See exactly which field is being changed to None
                print(f"Target field '{field}' is blank. Changing '{repr(value)}' to None.")
                cleaned_data[field] = None
            else:
                #LOG 3: See fields that were skipped because they contain text
                print(f"Skipping field '{field}'. Current value is: '{value}'")

        #LOG 4: See the final output dictionary that gets saved
        print("--- [Form Clean End] Final Data to Save ---")
        print(f"After processing: {cleaned_data}\n")

        return cleaned_data

class PhoneForm(forms.ModelForm):
    class Meta:
        model = ContactPhone
        fields = ['phone_number', 'type']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'placeholder': 'e.g., +1234567890',
                'pattern': r'^\+?[0-9]{7,15}$',
                'title': 'Phone number must be 7-15 digits, can start with +'
            })
        }

    def clean_phone_number(self):
        """Custom validation for phone number"""
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Remove any whitespace
            phone = phone.strip()

            # Check if it only contains digits, +, -, or spaces
            # Remove allowed special characters for validation
            cleaned = re.sub(r'[\s\-\(\)]', '', phone)

            # Check if it matches the pattern
            if not re.match(r'^\+?[0-9]{7,15}$', cleaned):
                raise forms.ValidationError(
                    'Phone number must be between 7-15 digits and can start with +'
                )

            # Update the cleaned data to the cleaned version
            self.cleaned_data['phone_number'] = cleaned
        return phone




class EmailForm(forms.ModelForm):
    class Meta:
        model = ContactEmail
        fields = ['email_address', 'type']
        widgets = {
            'email_address': forms.EmailInput(attrs={
                'placeholder': 'e.g., email@example.com',
                'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                'title': 'Please enter a valid email address (e.g., user@example.com)'
            })
        }

    def clean_email_address(self):
        """Custom validation for email"""
        email = self.cleaned_data.get('email_address')
        if email:
            # Use Django's built-in email validator
            email_validator = EmailValidator(
                message='Please enter a valid email address'
            )
            email_validator(email)
        return email