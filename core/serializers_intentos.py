from rest_framework import serializers

from .models import Intento, OpcionRespuesta, Pregunta, RespuestaIntento


class OpcionIntentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionRespuesta
        fields = ('id', 'texto', 'orden')


class PreguntaIntentoSerializer(serializers.ModelSerializer):
    opciones = OpcionIntentoSerializer(many=True, read_only=True)

    class Meta:
        model = Pregunta
        fields = ('id', 'texto_base', 'enunciado', 'tipo', 'puntaje', 'opciones')


class RespuestaIntentoSerializer(serializers.ModelSerializer):
    opcion_texto = serializers.CharField(source='opcion.texto', read_only=True)

    class Meta:
        model = RespuestaIntento
        fields = ('pregunta', 'opcion', 'opcion_texto', 'marcada_revision')


class IntentoSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.SerializerMethodField()
    estudiante_usuario = serializers.CharField(
        source='usuario.username',
        read_only=True,
    )
    cuestionario_nombre = serializers.CharField(
        source='cuestionario.nombre',
        read_only=True,
    )
    respuestas = RespuestaIntentoSerializer(
        source='respuestaintento_set',
        many=True,
        read_only=True,
    )
    preguntas = serializers.SerializerMethodField()
    nota_maxima = serializers.DecimalField(
        source='cuestionario.nota_maxima',
        max_digits=5,
        decimal_places=2,
        read_only=True,
    )
    nota_aprobar = serializers.DecimalField(
        source='cuestionario.nota_aprobar',
        max_digits=5,
        decimal_places=2,
        read_only=True,
    )
    aprobado = serializers.SerializerMethodField()
    calificacion_final = serializers.DecimalField(
        source='puntaje',
        max_digits=5,
        decimal_places=2,
        read_only=True,
    )
    preguntas_sin_responder = serializers.SerializerMethodField()
    duracion_minutos = serializers.IntegerField(
        source='cuestionario.duracion_minutos',
        read_only=True,
        allow_null=True,
    )
    revision_habilitada = serializers.BooleanField(
        source='cuestionario.permitir_revision',
        read_only=True,
    )
    fecha_limite = serializers.SerializerMethodField()
    resultado_publicado = serializers.SerializerMethodField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if (request and instance.usuario_id == request.user.id
                and not instance.cuestionario.publicar_resultado):
            data['puntaje'] = None
            data['calificacion_final'] = None
            data['aprobado'] = None
        return data

    class Meta:
        model = Intento
        fields = (
            'id',
            'cuestionario',
            'cuestionario_nombre',
            'estudiante_nombre',
            'estudiante_usuario',
            'fecha_inicio',
            'fecha_envio',
            'enviado',
            'estado',
            'puntaje',
            'calificacion_final',
            'nota_maxima',
            'nota_aprobar',
            'aprobado',
            'resultado_publicado',
            'preguntas_sin_responder',
            'duracion_minutos',
            'revision_habilitada',
            'fecha_limite',
            'preguntas',
            'respuestas',
        )

    def get_estudiante_nombre(self, obj) -> str:
        nombre = f'{obj.usuario.first_name} {obj.usuario.last_name}'.strip()
        return nombre or obj.usuario.username

    def get_preguntas(self, obj) -> list[dict]:
        preguntas = Pregunta.objects.filter(
            cuestionario_preguntas__cuestionario=obj.cuestionario,
        ).prefetch_related('opciones')
        return PreguntaIntentoSerializer(preguntas, many=True).data

    def get_aprobado(self, obj) -> bool:
        return obj.enviado and obj.puntaje >= obj.cuestionario.nota_aprobar

    def get_resultado_publicado(self, obj) -> bool:
        request = self.context.get('request')
        return bool(obj.cuestionario.publicar_resultado or (request and (request.user.is_staff or request.user.is_superuser)))

    def get_preguntas_sin_responder(self, obj) -> int:
        return obj.respuestaintento_set.filter(opcion__isnull=True).count()

    def get_fecha_limite(self, obj) -> str | None:
        limite = obj.fecha_limite()
        return limite.isoformat() if limite else None


class RevisionRespuestaSerializer(serializers.ModelSerializer):
    pregunta_enunciado = serializers.CharField(
        source='pregunta.enunciado',
        read_only=True,
    )
    opcion_texto = serializers.CharField(source='opcion.texto', read_only=True)
    opcion_correcta = serializers.SerializerMethodField()
    retroalimentacion = serializers.CharField(
        source='pregunta.retroalimentacion',
        read_only=True,
    )

    class Meta:
        model = RespuestaIntento
        fields = (
            'pregunta',
            'pregunta_enunciado',
            'opcion',
            'opcion_texto',
            'opcion_correcta',
            'retroalimentacion',
        )

    def get_opcion_correcta(self, obj) -> int | None:
        correcta = obj.pregunta.opciones.filter(es_correcta=True).first()
        return correcta.id if correcta else None


class IniciarIntentoInputSerializer(serializers.Serializer):
    cuestionario = serializers.IntegerField(
        min_value=1,
        help_text='ID del simulacro o cuestionario a iniciar.',
    )
    contrasena = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        help_text='Contraseña de acceso si el simulacro la requiere.',
    )


class IniciarIntentoCuestionarioInputSerializer(serializers.Serializer):
    contrasena = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        help_text='Contraseña de acceso si el simulacro la requiere.',
    )


class IniciarIntentoOutputSerializer(serializers.Serializer):
    detail = serializers.CharField()
    intento_id = serializers.IntegerField()
    cuestionario_id = serializers.IntegerField()
    duracion_minutos = serializers.IntegerField(allow_null=True)
    nota_maxima = serializers.CharField()


class GuardarRespuestaInputSerializer(serializers.Serializer):
    pregunta = serializers.IntegerField(min_value=1)
    opcion = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    marcada_revision = serializers.BooleanField(required=False)


class GuardarRespuestaOutputSerializer(serializers.Serializer):
    detail = serializers.CharField()
    pregunta = serializers.IntegerField()
    opcion = serializers.IntegerField(allow_null=True)


class ResultadoPermitidoSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.SerializerMethodField()
    estudiante_usuario = serializers.CharField(source='usuario.username', read_only=True)
    cuestionario_nombre = serializers.CharField(source='cuestionario.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True, allow_null=True)
    periodo_nombre = serializers.CharField(source='periodo.nombre', read_only=True, allow_null=True)
    calificacion_final = serializers.DecimalField(
        source='puntaje',
        max_digits=5,
        decimal_places=2,
        read_only=True,
    )
    nota_maxima = serializers.DecimalField(
        source='cuestionario.nota_maxima',
        max_digits=5,
        decimal_places=2,
        read_only=True,
    )
    nota_aprobar = serializers.DecimalField(
        source='cuestionario.nota_aprobar',
        max_digits=5,
        decimal_places=2,
        read_only=True,
    )
    aprobado = serializers.SerializerMethodField()
    resultado_publicado = serializers.SerializerMethodField()

    class Meta:
        model = Intento
        fields = (
            'id',
            'cuestionario',
            'cuestionario_nombre',
            'curso_nombre',
            'periodo_nombre',
            'estudiante_nombre',
            'estudiante_usuario',
            'fecha_inicio',
            'fecha_envio',
            'enviado',
            'estado',
            'puntaje',
            'calificacion_final',
            'nota_maxima',
            'nota_aprobar',
            'aprobado',
            'resultado_publicado',
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if (
            request
            and instance.usuario_id == request.user.id
            and not instance.cuestionario.publicar_resultado
        ):
            data['puntaje'] = None
            data['calificacion_final'] = None
            data['aprobado'] = None
        return data

    def get_estudiante_nombre(self, obj) -> str:
        nombre = f'{obj.usuario.first_name} {obj.usuario.last_name}'.strip()
        return nombre or obj.usuario.username

    def get_aprobado(self, obj) -> bool:
        return obj.enviado and obj.puntaje >= obj.cuestionario.nota_aprobar

    def get_resultado_publicado(self, obj) -> bool:
        request = self.context.get('request')
        return bool(
            obj.cuestionario.publicar_resultado
            or (request and (request.user.is_staff or request.user.is_superuser))
        )

