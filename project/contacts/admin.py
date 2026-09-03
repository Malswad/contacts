from django.contrib import admin

from .models import Contact, PersonalDetails, OrganizationDetails, ContactPhone, ContactEmail

# Register your models here.
admin.site.register(Contact)
admin.site.register(PersonalDetails)
admin.site.register(OrganizationDetails)
admin.site.register(ContactPhone)
admin.site.register(ContactEmail)
