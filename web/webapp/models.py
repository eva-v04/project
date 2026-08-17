from django.db import models


class Package(models.Model):
    package_name = models.CharField(max_length=100, unique=True)
    package_version = models.CharField(max_length=50, default='latest')


class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    password = models.CharField(max_length=100)


class Analyses(models.Model):
    package_name = models.CharField(max_length=100)
    package_version = models.CharField(max_length=50, default='latest')  # Προσθήκη πεδίου για την έκδοση
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_analyses', null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    analysis_type = models.CharField(max_length=20, choices=[('callgraph', 'Call Graph'), ('gasket', 'Gasket')], default='callgraph')
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed')], default='pending')
    # task_id = models.CharField(max_length=50, blank=True, null=True)  # Προσθήκη πεδίου για το task ID
    progress = models.IntegerField(default=0)  # Προσθήκη πεδίου για την πρόοδο της ανάλυσης (0-100)
    current_step = models.CharField(max_length=255, default="Starting...")  # Περιγραφή σταδίου


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    analysis = models.ForeignKey(Analyses, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=100)
    message = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    #link για να πηγαίνει κατευθείαν στα αποτελέσματα
    link = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
