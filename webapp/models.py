from django.db import models


class Package(models.Model):
    name = models.CharField(max_length=100, unique=True)


class User(models.Model):
    username = models.CharField(max_length=100)
    email = models.EmailField()
    password = models.CharField(max_length=100)


class Analyses(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='all_analyses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_analyses')
    date = models.DateTimeField(auto_now_add=True)