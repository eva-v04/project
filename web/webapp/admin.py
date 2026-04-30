from django.contrib import admin
from .models import User, Package, Analyses

admin.site.register(User)
admin.site.register(Package)
admin.site.register(Analyses)