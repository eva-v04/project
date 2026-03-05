from django.db import models
from django import forms as modelForms
#from django import datefields

class analysis(models.Model):
    package_name = models.CharField(max_length=100)
#    date = models.DateField()

class package(models.Model):
    package_name = models.OneToOneField(analysis, on_delete=models.CASCADE)
    bridges = models.IntegerField(default=0)