from django.db import models


class Contact(models.Model):
    """main contact table"""

    ContactType = [
        ('organization', 'organization'),
        ('personal', 'personal')
    ]

    contact_type = models.CharField(max_length=12, choices=ContactType)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.contact_type} ({self.id})"

    def get_name(self):
        """Fetches whatever name matches the profile type."""
        if self.contact_type == 'personal':
            p = self.personaldetails # Django template reverse lookup syntax
            if p:
                if p.first_name_ar and p.last_name_ar:
                    return f"{p.first_name} {p.last_name} | {p.first_name_ar} {p.last_name_ar}"
                else:
                    return f"{p.first_name} {p.last_name}"
        if self.contact_type == 'organization':
            o = self.organizationdetails
            if o:
                if o.legal_name_ar:
                    return f"{o.legal_name} | {o.legal_name_ar}"
                else:
                    return f"{o.legal_name}"
        return "No Name Added"

    def get_phones(self):
        """Fetches all stored phone numbers into a single clean string."""
        phone_list = self.contactphone_set.all()
        return ", ".join([f"{p.phone_number} ({p.type})" for p in phone_list]) if phone_list else "No phone"

class PersonalDetails(models.Model):
    """Specific details for person contacts."""
    contact = models.OneToOneField(Contact, on_delete=models.CASCADE)

    # English Version
    first_name = models.CharField(max_length=50)
    second_name = models.CharField(max_length=50, blank=True, null=True)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)

    # Arabic Version
    first_name_ar = models.CharField(max_length=50, blank=True, null=True)
    second_name_ar = models.CharField(max_length=50, blank=True, null=True)
    middle_name_ar = models.CharField(max_length=50, blank=True, null=True)
    last_name_ar = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} | {self.first_name_ar} {self.last_name_ar}"


class OrganizationDetails(models.Model):
    """Specific details for businesses contacts."""
    contact = models.OneToOneField(Contact, on_delete=models.CASCADE)

    # English Version
    legal_name = models.CharField(max_length=255)  # Official registered name
    trade_name = models.CharField(max_length=255)  # Doing Business As (DBA)

    # Arabic Version
    legal_name_ar = models.CharField(max_length=255, blank=True, null=True)
    trade_name_ar = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.legal_name} | {self.legal_name_ar}"


class ContactPhone(models.Model):
    """Contact phone number table to use as many to one with the main contact table"""
    PhoneType = [
        ('work', 'work'),
        ('personal', 'personal'),
        ('other', 'other')
    ]

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20)
    type = models.CharField(max_length=10, choices=PhoneType, default='other')

    def __str__(self):
        return f"{self.phone_number} ({self.type})"


class ContactEmail(models.Model):
    """Contact email table to use as many to one with the main contact table"""
    EmailType = [
        ('work', 'work'),
        ('personal', 'personal'),
        ('other', 'other')
    ]

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    email_address = models.EmailField()
    type = models.CharField(max_length=10, choices=EmailType, default='other')

    def __str__(self):
        return f"{self.email_address} ({self.type})"
