from decimal import Decimal

from rest_framework import serializers

from .models import Cuestionario, CuestionarioPregunta, OpcionRespuesta, Pregunta


class CuestionarioPreguntaSerializer(serializers.ModelSerializer):
    pregunta_enunciado = serializers.CharField(source='pregunta.enunciado', read_only=True)
    pregunta_activa = serializers.BooleanField(source='pregunta.activa', read_only=True)

    class Meta:
        model = CuestionarioPregunta
        fields = ('id', 'pregunta', 'pregunta_enunciado', 'pregunta_activa', 'orden')

    def validate_pregunta(self, value):
        if not value.activa:
            raise serializers.ValidationError('La pregunta está inactiva y no puede asignarse.')
        return value


class CuestionarioSerializer(serializers.ModelSerializer):
    preguntas = CuestionarioPreguntaSerializer(
        source='cuestionario_preguntas',
        many=True,
        required=False,
    )
    total_preguntas = serializers.SerializerMethodField(read_only=True)
    requiere_contrasena = serializers.BooleanField(read_only=True)
    contrasena = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)

    class Meta:
        model = Cuestionario
        fields = (
            'id',
            'nombre',
            'descripcion',
            'tematica',
            'estado',
            'requiere_contrasena',
            'contrasena',
            'publicar_resultado',
            'curso',
            'fecha_creacion',
            'fecha_apertura',
            'fecha_cierre',
            'duracion_minutos',
            'max_intentos',
            'nota_maxima',
            'nota_aprobar',
            'permitir_revision',
            'activo',
            'preguntas',
            'total_preguntas',
        )

    def get_total_preguntas(self, obj):
        return obj.cuestionario_preguntas.count()

    def validate(self, data):
        fecha_apertura = data.get('fecha_apertura', getattr(self.instance, 'fecha_apertura', None))
        fecha_cierre = data.get('fecha_cierre', getattr(self.instance, 'fecha_cierre', None))
        duracion = data.get('duracion_minutos', getattr(self.instance, 'duracion_minutos', None))
        max_intentos = data.get('max_intentos', getattr(self.instance, 'max_intentos', None))
        nota_maxima = data.get(
            'nota_maxima',
            getattr(self.instance, 'nota_maxima', Decimal('5')),
        )
        nota_aprobar = data.get(
            'nota_aprobar',
            getattr(self.instance, 'nota_aprobar', Decimal('0')),
        )

        if fecha_apertura and fecha_cierre and fecha_cierre <= fecha_apertura:
            raise serializers.ValidationError(
                {'fecha_cierre': 'Debe ser posterior a la fecha de apertura.'}
            )
        if duracion is not None and duracion <= 0:
            raise serializers.ValidationError(
                {'duracion_minutos': 'Debe ser mayor que cero.'}
            )
        if max_intentos is not None and max_intentos < 1:
            raise serializers.ValidationError(
                {'max_intentos': 'Debe ser al menos 1.'}
            )
        if nota_maxima is not None and (
            nota_maxima <= 0 or nota_maxima > Decimal('5.00')
        ):
            raise serializers.ValidationError(
                {'nota_maxima': 'Debe estar entre cero y 5.00.'}
            )
        if nota_aprobar is not None and (
            nota_aprobar < 0 or nota_aprobar > nota_maxima
        ):
            raise serializers.ValidationError(
                {'nota_aprobar': 'Debe estar entre cero y la calificación máxima.'}
            )

        preguntas = data.get('cuestionario_preguntas', None)
        if preguntas is not None:
            ids = [p['pregunta'].id for p in preguntas]
            if len(ids) != len(set(ids)):
                raise serializers.ValidationError(
                    {'preguntas': 'No puedes repetir la misma pregunta en el cuestionario.'}
                )

        return data

    def create(self, validated_data):
        preguntas_data = validated_data.pop('cuestionario_preguntas', [])
        raw_password = validated_data.pop('contrasena', '')
        validated_data['estado'] = Cuestionario.ESTADO_BORRADOR
        validated_data['activo'] = False
        validated_data['creador'] = self.context['request'].user
        cuestionario = Cuestionario.objects.create(**validated_data)
        if raw_password:
            cuestionario.establecer_contrasena(raw_password)
            cuestionario.save(update_fields=['contrasena_hash'])
        for item in preguntas_data:
            CuestionarioPregunta.objects.create(cuestionario=cuestionario, **item)
        return cuestionario

    def update(self, instance, validated_data):
        preguntas_data = validated_data.pop('cuestionario_preguntas', None)
        raw_password = validated_data.pop('contrasena', None)
        validated_data.pop('estado', None)
        validated_data.pop('activo', None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()
        if raw_password is not None:
            instance.establecer_contrasena(raw_password)
            instance.save(update_fields=['contrasena_hash'])
        if preguntas_data is not None:
            instance.cuestionario_preguntas.all().delete()
            for item in preguntas_data:
                CuestionarioPregunta.objects.create(cuestionario=instance, **item)
        return instance


class CuestionarioListSerializer(serializers.ModelSerializer):
    total_preguntas = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Cuestionario
        fields = (
            'id',
            'nombre',
            'descripcion',
            'tematica',
            'estado',
            'curso',
            'fecha_apertura',
            'fecha_cierre',
            'duracion_minutos',
            'max_intentos',
            'nota_maxima',
            'nota_aprobar',
            'permitir_revision',
            'activo',
            'total_preguntas',
        )

    def get_total_preguntas(self, obj):
        return obj.cuestionario_preguntas.count()


class CuestionarioEstudianteSerializer(serializers.ModelSerializer):
    requiere_contrasena = serializers.BooleanField(read_only=True)
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True, allow_null=True)
    total_preguntas = serializers.SerializerMethodField(read_only=True)
    intentos_realizados = serializers.SerializerMethodField()
    intentos_restantes = serializers.SerializerMethodField()
    puede_iniciar = serializers.SerializerMethodField()
    motivo_bloqueo = serializers.SerializerMethodField()

    class Meta:
        model = Cuestionario
        fields = (
            'id',
            'nombre',
            'descripcion',
            'tematica',
            'curso',
            'curso_nombre',
            'fecha_apertura',
            'fecha_cierre',
            'duracion_minutos',
            'max_intentos',
            'nota_maxima',
            'nota_aprobar',
            'permitir_revision',
            'publicar_resultado',
            'requiere_contrasena',
            'total_preguntas',
            'intentos_realizados',
            'intentos_restantes',
            'puede_iniciar',
            'motivo_bloqueo',
        )

    def get_total_preguntas(self, obj):
        return obj.cuestionario_preguntas.count()

    def get_intentos_realizados(self, obj):
        user = self.context['request'].user
        return obj.intento_set.filter(usuario=user).count()

    def get_puede_iniciar(self, obj):
        return obj.puede_iniciar(self.context['request'].user)[0]

    def get_motivo_bloqueo(self, obj):
        return obj.puede_iniciar(self.context['request'].user)[1]

    def get_intentos_restantes(self, obj):
        return max(
            0,
            obj.max_intentos - self.get_intentos_realizados(obj),
        )
