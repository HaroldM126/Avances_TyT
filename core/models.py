from django.db import models
from django.contrib.auth.models import User


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Pregunta(models.Model):
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE
    )

    enunciado = models.TextField()
    explicacion = models.TextField(blank=True)

    def __str__(self):
        return self.enunciado[:50]


class OpcionRespuesta(models.Model):
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE
    )

    texto = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)

    def __str__(self):
        return self.texto


class Cuestionario(models.Model):
    nombre = models.CharField(max_length=100)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class CuestionarioPregunta(models.Model):
    cuestionario = models.ForeignKey(
        Cuestionario,
        on_delete=models.CASCADE
    )

    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE
    )


class Intento(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    cuestionario = models.ForeignKey(
        Cuestionario,
        on_delete=models.CASCADE
    )

    fecha_inicio = models.DateTimeField(auto_now_add=True)
    puntaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )


class RespuestaIntento(models.Model):
    intento = models.ForeignKey(
        Intento,
        on_delete=models.CASCADE
    )

    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE
    )

    opcion = models.ForeignKey(
        OpcionRespuesta,
        on_delete=models.CASCADE
    )