from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from .models import Contact, PersonalDetails, OrganizationDetails, ContactPhone, ContactEmail
from .forms import (
    ContactForm, PersonalDetailsForm, OrganizationDetailsForm,
    PhoneForm, EmailForm
)


def contact_list(request):
    """View all contacts with filtering options"""
    contact_type = request.GET.get('type', 'all')

    # Base queryset
    contacts = Contact.objects.all().order_by('-created_at')

    # Apply filter only if it is personal or organization
    if contact_type in ['personal', 'organization']:
        contacts = contacts.filter(contact_type=contact_type)
    # preparing the context for the template
    context = {
        'contacts': contacts,
        'current_filter': contact_type,
        'filter_options': [
            ('all', 'All Contacts'),
            ('personal', 'Personal'),
            ('organization', 'Organizations'),
        ]
    }
    # rendering the template with the context

    return render(request, 'contact_list.html', context)


def add_contact(request):
    """Add a new contact with multiple phones and emails"""

    if request.method == 'POST':
        contact_form = ContactForm(request.POST)
        contact_type = request.POST.get('contact_type')

        # Initialize forms based on contact type
        if contact_type == 'personal':
            details_form = PersonalDetailsForm(request.POST)
        else:
            details_form = OrganizationDetailsForm(request.POST)

        # Get phone and email data from POST
        phone_numbers = request.POST.getlist('phone_number')
        phone_types = request.POST.getlist('phone_type')
        emails = request.POST.getlist('email_address')
        email_types = request.POST.getlist('email_type')

        # Validate all forms
        forms_valid = contact_form.is_valid()
        if details_form:
            forms_valid = forms_valid and details_form.is_valid()

        # Check if at least one phone is provided
        has_phone = any(phone.strip() for phone in phone_numbers)
        if not has_phone:
            forms_valid = False
            messages.error(request, 'At least one phone number is required.')

        # Validate phone and email sub-forms
        phone_forms = []
        email_forms = []
        phone_errors = []
        email_errors = []

        # IMPORTANT: Create phone forms with the submitted data
        for i, phone in enumerate(phone_numbers):
            if phone.strip():
                phone_form = PhoneForm({
                    'phone_number': phone,
                    'type': phone_types[i] if i < len(phone_types) else 'other'
                })
                phone_forms.append(phone_form)
                if not phone_form.is_valid():
                    forms_valid = False
                    for field, errors in phone_form.errors.items():
                        for error in errors:
                            phone_errors.append(f"Phone {i + 1}: {error}")
            else:
                # Always add empty phone forms if they were submitted
                if i == 0 and not any(p.strip() for p in phone_numbers):
                    # First phone is empty, keep it
                    phone_forms.append(PhoneForm())
                elif i > 0:
                    # Additional empty phone fields - don't add them
                    pass

        # IMPORTANT: Create email forms with the submitted data
        for i, email in enumerate(emails):
            if email.strip():
                email_form = EmailForm({
                    'email_address': email,
                    'type': email_types[i] if i < len(email_types) else 'other'
                })
                email_forms.append(email_form)
                if not email_form.is_valid():
                    forms_valid = False
                    for field, errors in email_form.errors.items():
                        for error in errors:
                            email_errors.append(f"Email {i + 1}: {error}")
            else:
                if i == 0 and not any(e.strip() for e in emails):
                    email_forms.append(EmailForm())

        # IMPORTANT: If validation fails, re-render with the submitted data
        if not forms_valid:
            # Display all errors
            if not contact_form.is_valid():
                for field, errors in contact_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

            if details_form and not details_form.is_valid():
                for field, errors in details_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

            for error in phone_errors:
                messages.error(request, error)
            for error in email_errors:
                messages.error(request, error)

            # Prepare context with the submitted data
            context = {
                'contact_form': contact_form,
                'details_form': details_form,
                'phone_forms': phone_forms if phone_forms else [PhoneForm()],
                'email_forms': email_forms if email_forms else [EmailForm()],
                'initial_type': contact_type or 'personal',
                'is_edit': False,
            }
            return render(request, 'add_contact.html', context)

        # If validation passes, save to database
        if forms_valid:
            try:
                with transaction.atomic():
                    contact = contact_form.save()
                    details = details_form.save(commit=False)
                    details.contact = contact
                    details.save()

                    for phone_form in phone_forms:
                        phone = phone_form.save(commit=False)
                        phone.contact = contact
                        phone.save()

                    for email_form in email_forms:
                        email = email_form.save(commit=False)
                        email.contact = contact
                        email.save()

                    messages.success(request, f'Contact created successfully!')
                    return redirect('contacts:contact_list')

            except Exception as e:
                messages.error(request, f'Error saving contact: {str(e)}')

    else:
        # GET request - initialize empty forms
        contact_form = ContactForm()
        details_form = None
        phone_forms = [PhoneForm()]
        email_forms = [EmailForm()]

    # Get initial contact type for form display
    initial_type = request.GET.get('type', 'personal')

    context = {
        'contact_form': contact_form,
        'details_form': details_form,
        'phone_forms': phone_forms if 'phone_forms' in locals() else [PhoneForm()],
        'email_forms': email_forms if 'email_forms' in locals() else [EmailForm()],
        'initial_type': initial_type,
        'is_edit': False,
    }

    return render(request, 'add_contact.html', context)


def edit_contact(request, contact_id):
    """Edit an existing contact"""
    contact = get_object_or_404(Contact, id=contact_id)

    # Get related objects
    if contact.contact_type == 'personal':
        details = get_object_or_404(PersonalDetails, contact=contact)
    else:
        details = get_object_or_404(OrganizationDetails, contact=contact)

    phones = ContactPhone.objects.filter(contact=contact)
    emails = ContactEmail.objects.filter(contact=contact)

    if request.method == 'POST':
        # Use existing contact type, not from POST
        contact_type = contact.contact_type
        contact_form = ContactForm(request.POST, instance=contact)

        # Initialize forms based on contact type
        if contact_type == 'personal':
            details_form = PersonalDetailsForm(request.POST, instance=details)
        else:
            details_form = OrganizationDetailsForm(request.POST, instance=details)

        # Get phone and email data from POST
        phone_numbers = request.POST.getlist('phone_number')
        phone_types = request.POST.getlist('phone_type')
        emails_post = request.POST.getlist('email_address')
        email_types = request.POST.getlist('email_type')

        # Validate all forms
        forms_valid = contact_form.is_valid()
        if details_form:
            forms_valid = forms_valid and details_form.is_valid()

        # Check if at least one phone is provided
        has_phone = any(phone.strip() for phone in phone_numbers)
        if not has_phone:
            forms_valid = False
            messages.error(request, 'At least one phone number is required.')

        # IMPORTANT: Create phone forms with the submitted data
        phone_forms = []
        phone_errors = []

        for i, phone in enumerate(phone_numbers):
            if phone.strip():
                phone_form = PhoneForm({
                    'phone_number': phone,
                    'type': phone_types[i] if i < len(phone_types) else 'other'
                })
                phone_forms.append(phone_form)
                if not phone_form.is_valid():
                    forms_valid = False
                    for field, errors in phone_form.errors.items():
                        for error in errors:
                            phone_errors.append(f"Phone {i + 1}: {error}")
            else:
                if i == 0 and not any(p.strip() for p in phone_numbers):
                    phone_forms.append(PhoneForm())

        # IMPORTANT: Create email forms with the submitted data
        email_forms = []
        email_errors = []

        for i, email in enumerate(emails_post):
            if email.strip():
                email_form = EmailForm({
                    'email_address': email,
                    'type': email_types[i] if i < len(email_types) else 'other'
                })
                email_forms.append(email_form)
                if not email_form.is_valid():
                    forms_valid = False
                    for field, errors in email_form.errors.items():
                        for error in errors:
                            email_errors.append(f"Email {i + 1}: {error}")
            else:
                if i == 0 and not any(e.strip() for e in emails_post):
                    email_forms.append(EmailForm())

        if forms_valid:
            try:
                with transaction.atomic():
                    contact = contact_form.save()
                    details = details_form.save(commit=False)
                    details.contact = contact
                    details.save()

                    # Delete existing phones and emails
                    ContactPhone.objects.filter(contact=contact).delete()
                    ContactEmail.objects.filter(contact=contact).delete()

                    # Save phones
                    for phone_form in phone_forms:
                        phone = phone_form.save(commit=False)
                        phone.contact = contact
                        phone.save()

                    # Save emails
                    for email_form in email_forms:
                        email = email_form.save(commit=False)
                        email.contact = contact
                        email.save()

                    messages.success(request, f'Contact updated successfully!')
                    return redirect('contacts:contact_list')

            except Exception as e:
                messages.error(request, f'Error updating contact: {str(e)}')
        else:
            # Display errors
            if not contact_form.is_valid():
                for field, errors in contact_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

            if details_form and not details_form.is_valid():
                for field, errors in details_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

            for error in phone_errors:
                messages.error(request, error)
            for error in email_errors:
                messages.error(request, error)

            # IMPORTANT: Re-render with the submitted data
            context = {
                'contact_form': contact_form,
                'details_form': details_form,
                'phone_forms': phone_forms if phone_forms else [PhoneForm()],
                'email_forms': email_forms if email_forms else [EmailForm()],
                'initial_type': contact.contact_type,
                'is_edit': True,
                'contact_id': contact.id,
            }
            return render(request, 'add_contact.html', context)

    else:
        # GET request - populate forms with existing data
        contact_form = ContactForm(instance=contact)

        if contact.contact_type == 'personal':
            details_form = PersonalDetailsForm(instance=details)
        else:
            details_form = OrganizationDetailsForm(instance=details)

        # Create phone forms with existing data
        phone_forms = []
        if phones.exists():
            for phone in phones:
                phone_form = PhoneForm(initial={
                    'phone_number': phone.phone_number,
                    'type': phone.type
                })
                phone_forms.append(phone_form)
        else:
            phone_forms = [PhoneForm()]

        # Create email forms with existing data
        email_forms = []
        if emails.exists():
            for email in emails:
                email_form = EmailForm(initial={
                    'email_address': email.email_address,
                    'type': email.type
                })
                email_forms.append(email_form)
        else:
            email_forms = [EmailForm()]

    context = {
        'contact_form': contact_form,
        'details_form': details_form,
        'phone_forms': phone_forms,
        'email_forms': email_forms,
        'initial_type': contact.contact_type,
        'is_edit': True,
        'contact_id': contact.id,
    }

    return render(request, 'add_contact.html', context)


def delete_contact(request, contact_id):
    """Delete a contact"""
    contact = get_object_or_404(Contact, id=contact_id)

    try:
        # Get name for success message before deleting
        contact_name = contact.get_name()
        contact.delete()
        messages.success(request, f'Contact "{contact_name}" deleted successfully!')
    except Exception as e:
        messages.error(request, f'Error deleting contact: {str(e)}')

    return redirect('contacts:contact_list')

