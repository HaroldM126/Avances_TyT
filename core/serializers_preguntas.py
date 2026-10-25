from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    Categoria,
    Competencia,
    OpcionRespuesta,
    Pregunta,
)


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ('id', 'nombre')

    def validate_nombre(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('El nombre es obligatorio.')
        qs = Categoria.objects.filter(nombre__iexact=value.strip())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe una categoría con este nombre.')
        return value.strip()


class CompetenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competencia
        fields = ('id', 'nombre')

    def validate_nombre(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('El nombre es obligatorio.')
        qs = Competencia.objects.filter(nombre__iexact=value.strip())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe una competencia con este nombre.')
        return value.strip()


class OpcionRespuestaSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionRespuesta
        fields = ('id', 'texto', 'es_correcta', 'orden')

    def validate_texto(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('El texto de la opción es obligatorio.')
        return value.strip()


class PreguntaSerializer(serializers.ModelSerializer):
    opciones = OpcionRespuestaSerializer(many=True)
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    competencia_nombre = serializers.CharField(source='competencia.nombre', read_only=True)

    class Meta:
        model = Pregunta
        fields = (
            'id',
            'categoria',
            'categoria_nombre',
            'competencia',
            'competencia_nombre',
            'enunciado',
            'explicacion',
            'tipo',
            'puntaje',
            'activa',
            'opciones',
        )

    def validate(self, data):
        tipo = data.get('tipo', getattr(self.instance, 'tipo', None))
        opciones = data.get('opciones', None)

        if opciones is not None:
            if len(opciones) < 2:
                raise serializers.ValidationError(
                    {'opciones': 'Debes registrar al menos 2 opciones.'}
                )
            correctas = [o for o in opciones if o.get('es_correcta')]
            if tipo == Pregunta.TIPO_UNICA and len(correctas) != 1:
                raise serializers.ValidationError(
                    {'opciones': 'Para opción única debe haber exactamente una opción correcta.'}
                )
            if tipo == Pregunta.TIPO_MULTIPLE and len(correctas) < 1:
                raise serializers.ValidationError(
                    {'opciones': 'Para opción múltiple debe haber al menos una opción correcta.'}
                )
            if tipo == Pregunta.TIPO_VF:
                if len(opciones) != 2:
                    raise serializers.ValidationError(
                        {'opciones': 'Para verdadero/falso debe haber exactamente 2 opciones.'}
                    )
                if len(correctas) != 1:
                    raise serializers.ValidationError(
                        {'opciones': 'Para verdadero/falso debe haber exactamente una opción correcta.'}
                    )

        return data

    def create(self, validated_data):
        opciones_data = validated_data.pop('opciones', [])
        try:
            pregunta = Pregunta(**validated_data)
            pregunta.full_clean(exclude=['opciones'])
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        pregunta.save()
        for opcion in opciones_data:
            OpcionRespuesta.objects.create(pregunta=pregunta, **opcion)
        return pregunta

    def update(self, instance, validated_data):
        opciones_data = validated_data.pop('opciones', None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        try:
            instance.full_clean(exclude=['opciones'])
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        instance.save()
        if opciones_data is not None:
            instance.opciones.all().delete()
            for opcion in opciones_data:
                OpcionRespuesta.objects.create(pregunta=instance, **opcion)
        return instance


class PreguntaListSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    competencia_nombre = serializers.CharField(source='competencia.nombre', read_only=True)

    class Meta:
        model = Pregunta
        fields = (
            'id',
            'categoria',
            'categoria_nombre',
            'competencia',
            'competencia_nombre',
            'enunciado',
            'tipo',
            'puntaje',
            'activa',
        )