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
        fields = ('pregunta', 'opcion', 'opcion_texto')


class IntentoSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = Intento
        fields = (
            'id',
            'cuestionario',
            'cuestionario_nombre',
            'fecha_inicio',
            'fecha_envio',
            'enviado',
            'estado',
            'puntaje',
            'calificacion_final',
            'nota_maxima',
            'nota_aprobar',
            'aprobado',
            'preguntas_sin_responder',
            'preguntas',
            'respuestas',
        )

    def get_preguntas(self, obj):
        preguntas = Pregunta.objects.filter(
            cuestionario_preguntas__cuestionario=obj.cuestionario,
        ).prefetch_related('opciones')
        return PreguntaIntentoSerializer(preguntas, many=True).data

    def get_aprobado(self, obj):
        return obj.enviado and obj.puntaje >= obj.cuestionario.nota_aprobar

    def get_preguntas_sin_responder(self, obj):
        return obj.respuestaintento_set.filter(opcion__isnull=True).count()


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

    def get_opcion_correcta(self, obj):
        correcta = obj.pregunta.opciones.filter(es_correcta=True).first()
        return correcta.id if correcta else None
