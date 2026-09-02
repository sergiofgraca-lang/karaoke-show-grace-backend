from django.db import models

class Musica(models.Model):
    titulo = models.CharField(max_length=200)
    videoId = models.CharField(max_length=50)
    cantor = models.CharField(max_length=100)
    audio = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.titulo} - {self.cantor}"