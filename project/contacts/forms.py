import logging
from django import forms
from django.core.validators import EmailValidator
import re

from .models import Contact, PersonalDetails, OrganizationDetails, ContactPhone, ContactEmail

# Setup logger for this module
import logging
import sys

# Simple logger that will output to console regardless of Django settings
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Ensure console handler is added
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


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

        logger.info("=" * 50)
        logger.info("ORGANIZATION DETAILS FORM CLEAN - START")
        logger.info("=" * 50)

        # LOG 1: See the data exactly as the browser sent it
        logger.debug(f"Raw cleaned data before processing: {cleaned_data}")
        logger.info(f"Fields received: {list(cleaned_data.keys())}")

        null_if_blank_fields = ['legal_name_ar', 'trade_name_ar']
        logger.debug(f"Fields to check for null conversion: {null_if_blank_fields}")

        for field in null_if_blank_fields:
            value = cleaned_data.get(field)
            logger.debug(f"Checking field '{field}': current value = '{value}' (type: {type(value).__name__})")

            # If the value is a string and is empty/whitespace
            if isinstance(value, str) and not value.strip():
                # LOG 2: See exactly which field is being changed to None
                logger.info(f"Field '{field}' is blank/whitespace. Changing from '{repr(value)}' to None")
                cleaned_data[field] = None
            else:
                # LOG 3: See fields that were skipped because they contain text
                if value:
                    logger.info(f"Field '{field}' has content: '{value}' - keeping as is")
                else:
                    logger.info(f"Field '{field}' is None or not a string - skipping")

        # LOG 4: See the final output dictionary that gets saved
        logger.info("--- FINAL DATA TO SAVE ---")
        logger.info(f"After processing: {cleaned_data}")
        logger.info("=" * 50)
        logger.info("ORGANIZATION DETAILS FORM CLEAN - END")
        logger.info("=" * 50)

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
        logger.debug(f"PhoneForm.clean_phone_number - raw value: '{phone}'")

        if phone:
            # Remove any whitespace
            original_phone = phone
            phone = phone.strip()
            logger.debug(f"Phone after strip: '{phone}'")

            # Check if it only contains digits, +, -, or spaces
            # Remove allowed special characters for validation
            cleaned = re.sub(r'[\s\-\(\)]', '', phone)
            logger.debug(f"Phone after removing special chars: '{cleaned}'")

            # Check if it matches the pattern
            if not re.match(r'^\+?[0-9]{7,15}$', cleaned):
                logger.warning(f"Phone validation failed: '{phone}' does not match pattern")
                raise forms.ValidationError(
                    'Phone number must be between 7-15 digits and can start with +'
                )

            logger.info(f"Phone validation passed: original='{original_phone}', cleaned='{cleaned}'")
            # Update the cleaned data to the cleaned version
            self.cleaned_data['phone_number'] = cleaned
        else:
            logger.debug("Phone number is empty - skipping validation")

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
        logger.debug(f"EmailForm.clean_email_address - raw value: '{email}'")

        if email:
            # Use Django's built-in email validator
            try:
                email_validator = EmailValidator(
                    message='Please enter a valid email address'
                )
                email_validator(email)
                logger.info(f"Email validation passed: '{email}'")
            except forms.ValidationError as e:
                logger.warning(f"Email validation failed: '{email}' - Error: {e.message}")
                raise
        else:
            logger.debug("Email address is empty - skipping validation")

        return email