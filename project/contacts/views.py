from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from .models import Contact, PersonalDetails, OrganizationDetails, ContactPhone, ContactEmail
from .forms import (
    ContactForm, PersonalDetailsForm, OrganizationDetailsForm,
    PhoneForm, EmailForm
)
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

    logger.info(f"add_contact called with method: {request.method}")

    if request.method == 'POST':
        logger.info("Processing POST request for add_contact")

        contact_form = ContactForm(request.POST)
        contact_type = request.POST.get('contact_type')
        logger.info(f"Contact type received: {contact_type}")

        # Initialize forms based on contact type
        if contact_type == 'personal':
            details_form = PersonalDetailsForm(request.POST)
            logger.info("Using PersonalDetailsForm")
        else:
            details_form = OrganizationDetailsForm(request.POST)
            logger.info("Using OrganizationDetailsForm")

        # Get phone and email data from POST
        phone_numbers = request.POST.getlist('phone_number')
        phone_types = request.POST.getlist('phone_type')
        emails = request.POST.getlist('email_address')
        email_types = request.POST.getlist('email_type')

        logger.info(f"Phone numbers received: {phone_numbers}")
        logger.info(f"Phone types received: {phone_types}")
        logger.info(f"Emails received: {emails}")
        logger.info(f"Email types received: {email_types}")

        # Validate all forms
        forms_valid = contact_form.is_valid()
        logger.info(f"Contact form valid: {forms_valid}")

        if details_form:
            details_valid = details_form.is_valid()
            forms_valid = forms_valid and details_valid
            logger.info(f"Details form valid: {details_valid}")

        # Check if at least one phone is provided
        has_phone = any(phone.strip() for phone in phone_numbers)
        logger.info(f"Has at least one phone number: {has_phone}")

        if not has_phone:
            forms_valid = False
            logger.warning("At least one phone number is required - validation failed")
            messages.error(request, 'At least one phone number is required.')

        # Validate phone and email sub-forms
        phone_forms = []
        email_forms = []
        phone_errors = []
        email_errors = []

        # Create phone forms with the submitted data
        logger.info(f"Processing {len(phone_numbers)} phone entries")
        for i, phone in enumerate(phone_numbers):
            if phone.strip():
                phone_form = PhoneForm({
                    'phone_number': phone,
                    'type': phone_types[i] if i < len(phone_types) else 'other'
                })
                phone_forms.append(phone_form)
                is_valid = phone_form.is_valid()
                logger.debug(
                    f"Phone {i + 1} - Number: '{phone}', Type: '{phone_types[i] if i < len(phone_types) else 'other'}', Valid: {is_valid}")

                if not is_valid:
                    forms_valid = False
                    logger.warning(f"Phone {i + 1} validation failed. Errors: {phone_form.errors}")
                    for field, errors in phone_form.errors.items():
                        for error in errors:
                            phone_errors.append(f"Phone {i + 1}: {error}")
            else:
                logger.debug(f"Phone {i + 1} is empty - skipping")
                # Always add empty phone forms if they were submitted
                if i == 0 and not any(p.strip() for p in phone_numbers):
                    logger.info("First phone is empty, keeping it")
                    phone_forms.append(PhoneForm())
                elif i > 0:
                    logger.debug("Additional empty phone field - not adding")
                    pass

        # Create email forms with the submitted data
        logger.info(f"Processing {len(emails)} email entries")
        for i, email in enumerate(emails):
            if email.strip():
                email_form = EmailForm({
                    'email_address': email,
                    'type': email_types[i] if i < len(email_types) else 'other'
                })
                email_forms.append(email_form)
                is_valid = email_form.is_valid()
                logger.debug(
                    f"Email {i + 1} - Address: '{email}', Type: '{email_types[i] if i < len(email_types) else 'other'}', Valid: {is_valid}")

                if not is_valid:
                    forms_valid = False
                    logger.warning(f"Email {i + 1} validation failed. Errors: {email_form.errors}")
                    for field, errors in email_form.errors.items():
                        for error in errors:
                            email_errors.append(f"Email {i + 1}: {error}")
            else:
                logger.debug(f"Email {i + 1} is empty - skipping")
                if i == 0 and not any(e.strip() for e in emails):
                    logger.info("First email is empty, keeping it")
                    email_forms.append(EmailForm())

        # Log final validation status
        logger.info(f"Final validation status: {forms_valid}")
        logger.info(f"Phone errors count: {len(phone_errors)}")
        logger.info(f"Email errors count: {len(email_errors)}")

        # If validation fails, re-render with the submitted data
        if not forms_valid:
            logger.warning("Validation failed - re-rendering form with errors")

            # Display all errors
            if not contact_form.is_valid():
                logger.warning(f"Contact form errors: {contact_form.errors}")
                for field, errors in contact_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

            if details_form and not details_form.is_valid():
                logger.warning(f"Details form errors: {details_form.errors}")
                for field, errors in details_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

            for error in phone_errors:
                logger.warning(f"Phone error: {error}")
                messages.error(request, error)

            for error in email_errors:
                logger.warning(f"Email error: {error}")
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

            logger.info("Returning to add_contact.html with error context")
            return render(request, 'add_contact.html', context)

        # If validation passes, save to database
        if forms_valid:
            logger.info("All forms valid - proceeding to save contact")

            try:
                with transaction.atomic():
                    logger.info("Starting database transaction")

                    contact = contact_form.save()
                    logger.info(f"Contact saved with ID: {contact.id}")

                    details = details_form.save(commit=False)
                    details.contact = contact
                    details.save()
                    logger.info(f"Details saved for contact ID: {contact.id}")

                    logger.info(f"Saving {len(phone_forms)} phone numbers")
                    for i, phone_form in enumerate(phone_forms):
                        phone = phone_form.save(commit=False)
                        phone.contact = contact
                        phone.save()
                        logger.debug(f"Phone {i + 1} saved: {phone}")

                    logger.info(f"Saving {len(email_forms)} email addresses")
                    for i, email_form in enumerate(email_forms):
                        email = email_form.save(commit=False)
                        email.contact = contact
                        email.save()
                        logger.debug(f"Email {i + 1} saved: {email}")

                    messages.success(request, f'Contact created successfully!')
                    logger.info(f"Contact {contact.id} created successfully. Redirecting to contact list.")
                    return redirect('contacts:contact_list')

            except Exception as e:
                logger.error(f"Error saving contact: {str(e)}", exc_info=True)
                messages.error(request, f'Error saving contact: {str(e)}')

    else:
        # GET request - initialize empty forms
        logger.info("Processing GET request - initializing empty forms")
        contact_form = ContactForm()
        details_form = None
        phone_forms = [PhoneForm()]
        email_forms = [EmailForm()]
        logger.debug("Created empty forms for GET request")

    # Get initial contact type for form display
    initial_type = request.GET.get('type', 'personal')
    logger.info(f"Initial contact type for form display: {initial_type}")

    # Ensure variables exist in context
    if 'phone_forms' not in locals():
        logger.debug("phone_forms not in locals - creating default")
        phone_forms = [PhoneForm()]

    if 'email_forms' not in locals():
        logger.debug("email_forms not in locals - creating default")
        email_forms = [EmailForm()]

    if 'contact_form' not in locals():
        logger.debug("contact_form not in locals - creating default")
        contact_form = ContactForm()

    if 'details_form' not in locals():
        logger.debug("details_form not in locals - setting to None")
        details_form = None

    context = {
        'contact_form': contact_form,
        'details_form': details_form,
        'phone_forms': phone_forms,
        'email_forms': email_forms,
        'initial_type': initial_type,
        'is_edit': False,
    }

    logger.info("Rendering add_contact.html with initial context")
    return render(request, 'add_contact.html', context)


def edit_contact(request, contact_id):
    """Edit an existing contact"""
    logger.info(f"edit_contact called with contact_id: {contact_id}, method: {request.method}")

    contact = get_object_or_404(Contact, id=contact_id)
    logger.info(f"Contact found: ID={contact.id}, Type={contact.contact_type}")

    # Get related objects
    if contact.contact_type == 'personal':
        details = get_object_or_404(PersonalDetails, contact=contact)
        logger.info("Retrieved PersonalDetails for contact")
    else:
        details = get_object_or_404(OrganizationDetails, contact=contact)
        logger.info("Retrieved OrganizationDetails for contact")

    phones = ContactPhone.objects.filter(contact=contact)
    emails = ContactEmail.objects.filter(contact=contact)
    logger.info(f"Found {phones.count()} phones and {emails.count()} emails for contact")

    if request.method == 'POST':
        logger.info("Processing POST request for edit_contact")

        # Use existing contact type, not from POST
        contact_type = contact.contact_type
        contact_form = ContactForm(request.POST, instance=contact)
        logger.debug(f"Contact type from existing contact: {contact_type}")

        # Initialize forms based on contact type
        if contact_type == 'personal':
            details_form = PersonalDetailsForm(request.POST, instance=details)
            logger.debug("Using PersonalDetailsForm with instance")
        else:
            details_form = OrganizationDetailsForm(request.POST, instance=details)
            logger.debug("Using OrganizationDetailsForm with instance")

        # Get phone and email data from POST
        phone_numbers = request.POST.getlist('phone_number')
        phone_types = request.POST.getlist('phone_type')
        emails_post = request.POST.getlist('email_address')
        email_types = request.POST.getlist('email_type')

        logger.info(f"Phone numbers received: {phone_numbers}")
        logger.info(f"Phone types received: {phone_types}")
        logger.info(f"Emails received: {emails_post}")
        logger.info(f"Email types received: {email_types}")

        # Validate all forms
        forms_valid = contact_form.is_valid()
        logger.info(f"Contact form valid: {forms_valid}")

        if details_form:
            details_valid = details_form.is_valid()
            forms_valid = forms_valid and details_valid
            logger.info(f"Details form valid: {details_valid}")

        # Check if at least one phone is provided
        has_phone = any(phone.strip() for phone in phone_numbers)
        logger.info(f"Has at least one phone number: {has_phone}")

        if not has_phone:
            forms_valid = False
            logger.warning("At least one phone number is required - validation failed")
            messages.error(request, 'At least one phone number is required.')

        # Create phone forms with the submitted data
        phone_forms = []
        phone_errors = []
        logger.info(f"Processing {len(phone_numbers)} phone entries")

        for i, phone in enumerate(phone_numbers):
            if phone.strip():
                phone_form = PhoneForm({
                    'phone_number': phone,
                    'type': phone_types[i] if i < len(phone_types) else 'other'
                })
                phone_forms.append(phone_form)
                is_valid = phone_form.is_valid()
                logger.debug(
                    f"Phone {i + 1} - Number: '{phone}', Type: '{phone_types[i] if i < len(phone_types) else 'other'}', Valid: {is_valid}")

                if not is_valid:
                    forms_valid = False
                    logger.warning(f"Phone {i + 1} validation failed. Errors: {phone_form.errors}")
                    for field, errors in phone_form.errors.items():
                        for error in errors:
                            phone_errors.append(f"Phone {i + 1}: {error}")
            else:
                logger.debug(f"Phone {i + 1} is empty - skipping")
                if i == 0 and not any(p.strip() for p in phone_numbers):
                    logger.info("First phone is empty, keeping it")
                    phone_forms.append(PhoneForm())

        # Create email forms with the submitted data
        email_forms = []
        email_errors = []
        logger.info(f"Processing {len(emails_post)} email entries")

        for i, email in enumerate(emails_post):
            if email.strip():
                email_form = EmailForm({
                    'email_address': email,
                    'type': email_types[i] if i < len(email_types) else 'other'
                })
                email_forms.append(email_form)
                is_valid = email_form.is_valid()
                logger.debug(
                    f"Email {i + 1} - Address: '{email}', Type: '{email_types[i] if i < len(email_types) else 'other'}', Valid: {is_valid}")

                if not is_valid:
                    forms_valid = False
                    logger.warning(f"Email {i + 1} validation failed. Errors: {email_form.errors}")
                    for field, errors in email_form.errors.items():
                        for error in errors:
                            email_errors.append(f"Email {i + 1}: {error}")
            else:
                logger.debug(f"Email {i + 1} is empty - skipping")
                if i == 0 and not any(e.strip() for e in emails_post):
                    logger.info("First email is empty, keeping it")
                    email_forms.append(EmailForm())

        # Log final validation status
        logger.info(f"Final validation status: {forms_valid}")
        logger.info(f"Phone errors count: {len(phone_errors)}")
        logger.info(f"Email errors count: {len(email_errors)}")

        if forms_valid:
            logger.info("All forms valid - proceeding to update contact")

            try:
                with transaction.atomic():
                    logger.info("Starting database transaction for update")

                    contact = contact_form.save()
                    logger.info(f"Contact updated with ID: {contact.id}")

                    details = details_form.save(commit=False)
                    details.contact = contact
                    details.save()
                    logger.info(f"Details updated for contact ID: {contact.id}")

                    # Delete existing phones and emails
                    deleted_phones = ContactPhone.objects.filter(contact=contact).delete()
                    deleted_emails = ContactEmail.objects.filter(contact=contact).delete()
                    logger.info(f"Deleted {deleted_phones[0]} existing phones and {deleted_emails[0]} existing emails")

                    # Save phones
                    logger.info(f"Saving {len(phone_forms)} phone numbers")
                    for i, phone_form in enumerate(phone_forms):
                        phone = phone_form.save(commit=False)
                        phone.contact = contact
                        phone.save()
                        logger.debug(f"Phone {i + 1} saved: {phone}")

                    # Save emails
                    logger.info(f"Saving {len(email_forms)} email addresses")
                    for i, email_form in enumerate(email_forms):
                        email = email_form.save(commit=False)
                        email.contact = contact
                        email.save()
                        logger.debug(f"Email {i + 1} saved: {email}")

                    messages.success(request, f'Contact updated successfully!')
                    logger.info(f"Contact {contact.id} updated successfully. Redirecting to contact list.")
                    return redirect('contacts:contact_list')

            except Exception as e:
                logger.error(f"Error updating contact: {str(e)}", exc_info=True)
                messages.error(request, f'Error updating contact: {str(e)}')
        else:
            logger.warning("Validation failed - re-rendering form with errors")

            # Display errors
            if not contact_form.is_valid():
                logger.warning(f"Contact form errors: {contact_form.errors}")
                for field, errors in contact_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

            if details_form and not details_form.is_valid():
                logger.warning(f"Details form errors: {details_form.errors}")
                for field, errors in details_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

            for error in phone_errors:
                logger.warning(f"Phone error: {error}")
                messages.error(request, error)

            for error in email_errors:
                logger.warning(f"Email error: {error}")
                messages.error(request, error)

            # Re-render with the submitted data
            context = {
                'contact_form': contact_form,
                'details_form': details_form,
                'phone_forms': phone_forms if phone_forms else [PhoneForm()],
                'email_forms': email_forms if email_forms else [EmailForm()],
                'initial_type': contact.contact_type,
                'is_edit': True,
                'contact_id': contact.id,
            }

            logger.info(f"Returning to add_contact.html with error context for contact ID: {contact.id}")
            return render(request, 'add_contact.html', context)

    else:
        # GET request - populate forms with existing data
        logger.info("Processing GET request - populating forms with existing data")

        contact_form = ContactForm(instance=contact)
        logger.debug("ContactForm populated with instance")

        if contact.contact_type == 'personal':
            details_form = PersonalDetailsForm(instance=details)
            logger.debug("PersonalDetailsForm populated with instance")
        else:
            details_form = OrganizationDetailsForm(instance=details)
            logger.debug("OrganizationDetailsForm populated with instance")

        # Create phone forms with existing data
        phone_forms = []
        if phones.exists():
            logger.info(f"Creating phone forms for {phones.count()} existing phones")
            for i, phone in enumerate(phones):
                phone_form = PhoneForm(initial={
                    'phone_number': phone.phone_number,
                    'type': phone.type
                })
                phone_forms.append(phone_form)
                logger.debug(f"Phone {i + 1} loaded: {phone.phone_number} ({phone.type})")
        else:
            logger.info("No existing phones found - creating empty phone form")
            phone_forms = [PhoneForm()]

        # Create email forms with existing data
        email_forms = []
        if emails.exists():
            logger.info(f"Creating email forms for {emails.count()} existing emails")
            for i, email in enumerate(emails):
                email_form = EmailForm(initial={
                    'email_address': email.email_address,
                    'type': email.type
                })
                email_forms.append(email_form)
                logger.debug(f"Email {i + 1} loaded: {email.email_address} ({email.type})")
        else:
            logger.info("No existing emails found - creating empty email form")
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

    logger.info(f"Rendering add_contact.html with edit context for contact ID: {contact.id}")
    return render(request, 'add_contact.html', context)


def delete_contact(request, contact_id):
    """Delete a contact"""
    logger.info(f"delete_contact called with contact_id: {contact_id}")

    contact = get_object_or_404(Contact, id=contact_id)
    logger.info(f"Contact found: ID={contact.id}")

    try:
        # Get name for success message before deleting
        contact_name = contact.get_name()
        logger.info(f"Deleting contact: {contact_name} (ID: {contact.id})")

        contact.delete()
        logger.info(f"Contact {contact_name} (ID: {contact_id}) deleted successfully")
        messages.success(request, f'Contact "{contact_name}" deleted successfully!')

    except Exception as e:
        logger.error(f"Error deleting contact {contact_id}: {str(e)}", exc_info=True)
        messages.error(request, f'Error deleting contact: {str(e)}')

    logger.info("Redirecting to contact list after delete attempt")
    return redirect('contacts:contact_list')