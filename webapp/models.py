from django.db import models


class Package(models.Model):
    package_name = models.CharField(max_length=100, unique=True)


class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    password = models.CharField(max_length=100)


class Analyses(models.Model):
    package_name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_analyses')
    date = models.DateTimeField(auto_now_add=True)
    analysis_type = models.CharField(max_length=20, choices=[('callgraph', 'Call Graph'), ('gasket', 'Gasket')], default='callgraph')
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed')], default='pending')
    task_id = models.CharField(max_length=50, blank=True, null=True)  # Προσθήκη πεδίου για το task ID
    