from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Competencia(models.Model):
    nombre = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ('nombre',)

    def __str__(self):
        return self.nombre


class Rol(models.Model):
    grupo = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name='rol',
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ('grupo__name',)

    def __str__(self):
        return self.grupo.name


class Pregunta(models.Model):
    TIPO_UNICA = 'UNICA'
    TIPO_MULTIPLE = 'MULTIPLE'
    TIPO_VF = 'VF'
    TIPO_CHOICES = [
        (TIPO_UNICA, 'Opción única'),
        (TIPO_MULTIPLE, 'Opción múltiple'),
        (TIPO_VF, 'Verdadero/Falso'),
    ]

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='preguntas',
    )
    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.PROTECT,
        related_name='preguntas',
        null=True,
        blank=True,
    )
    enunciado = models.TextField()
    explicacion = models.TextField(blank=True)
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default=TIPO_UNICA,
    )
    puntaje = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ('id',)

    def clean(self):
        super().clean()
        if not self.enunciado or not self.enunciado.strip():
            raise ValidationError({'enunciado': 'El enunciado es obligatorio.'})
        normalizado = self.enunciado.strip().lower()
        qs = Pregunta.objects.filter(enunciado__iexact=normalizado)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({
                'enunciado': 'Ya existe una pregunta con este enunciado.',
            })

    def __str__(self):
        return self.enunciado[:50]


class OpcionRespuesta(models.Model):
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE,
        related_name='opciones',
    )
    texto = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('orden', 'id')

    def __str__(self):
        return self.texto


class CuestionarioQuerySet(models.QuerySet):
    def disponibles(self):
        ahora = timezone.now()
        return self.filter(
            activo=True,
            fecha_apertura__lte=ahora,
            fecha_cierre__gte=ahora,
        )


class Cuestionario(models.Model):
    nombre = models.CharField(max_length=100)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_apertura = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    duracion_minutos = models.PositiveIntegerField(null=True, blank=True)
    max_intentos = models.PositiveIntegerField(default=1)
    nota_maxima = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    activo = models.BooleanField(default=True)

    objects = CuestionarioQuerySet.as_manager()

    class Meta:
        ordering = ('-fecha_apertura',)
        permissions = [
            ('manage_users', 'Puede administrar usuarios'),
            ('manage_roles', 'Puede administrar roles y permisos'),
            ('manage_question_bank', 'Puede administrar el banco de preguntas'),
            ('configure_quizzes', 'Puede configurar cuestionarios'),
            ('view_results', 'Puede consultar resultados'),
        ]

    def clean(self):
        super().clean()
        if self.fecha_apertura and self.fecha_cierre:
            if self.fecha_cierre <= self.fecha_apertura:
                raise ValidationError({
                    'fecha_cierre': 'La fecha de cierre debe ser posterior a la de apertura.',
                })

    def puede_iniciar(self, usuario):
        """Devuelve (bool, motivo). Si puede, (True, '')."""
        if not self.activo:
            return False, 'El cuestionario está inactivo.'
        if self.fecha_apertura is None or self.fecha_cierre is None:
            return False, 'El cuestionario aún no tiene fechas configuradas.'
        ahora = timezone.now()
        if ahora < self.fecha_apertura:
            return False, 'El cuestionario aún no está disponible.'
        if ahora > self.fecha_cierre:
            return False, 'El cuestionario ya cerró.'
        intentos_previos = self.intento_set.filter(usuario=usuario).count()
        if intentos_previos >= self.max_intentos:
            return False, 'Has agotado el número de intentos permitidos.'
        return True, ''

    def __str__(self):
        return self.nombre


class CuestionarioPregunta(models.Model):
    cuestionario = models.ForeignKey(
        Cuestionario,
        on_delete=models.CASCADE,
        related_name='cuestionario_preguntas',
    )
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.PROTECT,
        related_name='cuestionario_preguntas',
    )
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('orden', 'id')
        constraints = [
            models.UniqueConstraint(
                fields=['cuestionario', 'pregunta'],
                name='uq_cuestionario_pregunta',
            ),
        ]

    def __str__(self):
        return f'{self.cuestionario} - {self.pregunta}'


class Intento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    cuestionario = models.ForeignKey(Cuestionario, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    puntaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)


class RespuestaIntento(models.Model):
    intento = models.ForeignKey(Intento, on_delete=models.CASCADE)
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE)
    opcion = models.ForeignKey(OpcionRespuesta, on_delete=models.CASCADE)