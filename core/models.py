from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta


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


class SesionJWT(models.Model):
    sesion_id = models.UUIDField()
    jti = models.CharField(max_length=255, unique=True)
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sesiones_jwt',
    )
    expira_en = models.DateTimeField()
    revocada_en = models.DateTimeField(null=True, blank=True)
    motivo_revocacion = models.CharField(max_length=100, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=('sesion_id',)),
            models.Index(fields=('usuario', 'revocada_en')),
        ]


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
    texto_base = models.TextField(blank=True)
    enunciado = models.TextField()
    retroalimentacion = models.TextField(blank=True)
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
        if self.puntaje <= 0:
            raise ValidationError({
                'puntaje': 'El puntaje debe ser mayor que cero.',
            })

    def validar_opciones(self, opciones):
        if len(opciones) < 2:
            raise ValidationError({
                'opciones': 'Debes registrar al menos 2 opciones.',
            })
        correctas = [opcion for opcion in opciones if opcion.get('es_correcta')]
        if len(correctas) != 1:
            raise ValidationError({
                'opciones': 'Debe haber exactamente una opción correcta.',
            })
        if self.tipo == self.TIPO_VF and len(opciones) != 2:
            raise ValidationError({
                'opciones': (
                    'Para verdadero/falso debe haber exactamente 2 opciones.'
                ),
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
    nota_aprobar = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    permitir_revision = models.BooleanField(default=True)
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
        if self.nota_maxima <= 0:
            raise ValidationError({
                'nota_maxima': 'La calificación máxima debe ser mayor que cero.',
            })
        if self.nota_aprobar < 0 or self.nota_aprobar > self.nota_maxima:
            raise ValidationError({
                'nota_aprobar': (
                    'La nota para aprobar debe estar entre cero y la '
                    'calificación máxima.'
                ),
            })
        if self.duracion_minutos is not None and self.duracion_minutos <= 0:
            raise ValidationError({
                'duracion_minutos': 'El tiempo límite debe ser mayor que cero.',
            })
        if self.max_intentos <= 0:
            raise ValidationError({
                'max_intentos': 'Los intentos permitidos deben ser mayores que cero.',
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
        if not self.cuestionario_preguntas.exists():
            return False, 'El cuestionario no tiene preguntas asignadas.'
        intentos_previos = self.intento_set.filter(usuario=usuario).count()
        if intentos_previos >= self.max_intentos:
            return False, 'Has agotado el número de intentos permitidos.'
        return True, ''

    def validar_preguntas(self):
        errores = []
        relaciones = self.cuestionario_preguntas.select_related('pregunta').prefetch_related(
            'pregunta__opciones',
        )
        if not relaciones:
            errores.append('El cuestionario debe tener preguntas asignadas.')
        for relacion in relaciones:
            pregunta = relacion.pregunta
            if not pregunta.activa:
                errores.append(
                    f'La pregunta {pregunta.id} está inactiva.',
                )
            try:
                pregunta.validar_opciones([
                    {
                        'es_correcta': opcion.es_correcta,
                    }
                    for opcion in pregunta.opciones.all()
                ])
            except ValidationError as error:
                errores.extend(error.messages)
        return errores

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
    ESTADO_EN_CURSO = 'EN_CURSO'
    ESTADO_ENVIADO = 'ENVIADO'
    ESTADO_VENCIDO = 'VENCIDO'
    ESTADO_ANULADO = 'ANULADO'
    ESTADO_CHOICES = (
        (ESTADO_EN_CURSO, 'En curso'),
        (ESTADO_ENVIADO, 'Enviado'),
        (ESTADO_VENCIDO, 'Vencido'),
        (ESTADO_ANULADO, 'Anulado'),
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    cuestionario = models.ForeignKey(Cuestionario, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    puntaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    enviado = models.BooleanField(default=False)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_EN_CURSO,
    )

    class Meta:
        ordering = ('-fecha_inicio',)

    def fecha_limite(self):
        limites = []
        if self.cuestionario.fecha_cierre:
            limites.append(self.cuestionario.fecha_cierre)
        if self.cuestionario.duracion_minutos:
            limites.append(
                self.fecha_inicio + timedelta(
                    minutes=self.cuestionario.duracion_minutos,
                ),
            )
        return min(limites) if limites else None

    def esta_vencido(self):
        limite = self.fecha_limite()
        return limite is not None and timezone.now() > limite

    def calcular_puntaje(self):
        total = Decimal('0')
        obtenido = Decimal('0')
        for respuesta in self.respuestaintento_set.select_related(
            'pregunta',
            'opcion',
        ).prefetch_related('pregunta__opciones'):
            total += respuesta.pregunta.puntaje
            correcta = respuesta.pregunta.opciones.filter(
                es_correcta=True,
            ).first()
            if correcta and respuesta.opcion_id == correcta.id:
                obtenido += respuesta.pregunta.puntaje
        if total == 0:
            return Decimal('0.00')
        nota = (obtenido / total) * self.cuestionario.nota_maxima
        return nota.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class RespuestaIntento(models.Model):
    intento = models.ForeignKey(Intento, on_delete=models.CASCADE)
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE)
    opcion = models.ForeignKey(
        OpcionRespuesta,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('intento', 'pregunta'),
                name='uq_intento_pregunta',
            ),
        ]


class ImportacionPreguntas(models.Model):
    ESTADO_PREVIA = 'PREVIA'
    ESTADO_CONFIRMADA = 'CONFIRMADA'
    ESTADO_ERROR = 'ERROR'
    ESTADO_FALLIDA = 'FALLIDA'
    ESTADO_CHOICES = (
        (ESTADO_PREVIA, 'Vista previa'),
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_ERROR, 'Con errores'),
        (ESTADO_FALLIDA, 'Fallida'),
    )

    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    archivo_nombre = models.CharField(max_length=255)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    total = models.PositiveIntegerField(default=0)
    validas = models.PositiveIntegerField(default=0)
    invalidas = models.PositiveIntegerField(default=0)
    preguntas_creadas = models.PositiveIntegerField(default=0)
    archivo_hash = models.CharField(max_length=64, blank=True)
    error_global = models.TextField(blank=True)
    confirmado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-creado_en',)


class FilaImportacionPregunta(models.Model):
    importacion = models.ForeignKey(
        ImportacionPreguntas,
        on_delete=models.CASCADE,
        related_name='filas',
    )
    numero = models.PositiveIntegerField()
    valida = models.BooleanField(default=False)
    errores = models.JSONField(default=list)
    datos = models.JSONField(default=dict)