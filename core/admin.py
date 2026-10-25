from django.contrib import admin

from .models import (
    Categoria,
    Competencia,
    Cuestionario,
    CuestionarioPregunta,
    Intento,
    OpcionRespuesta,
    Pregunta,
    RespuestaIntento,
    Rol,
    SesionJWT,
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


class OpcionRespuestaInline(admin.TabularInline):
    model = OpcionRespuesta
    extra = 1
    fields = ('texto', 'es_correcta', 'orden')


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('id', 'enunciado_corto', 'categoria', 'competencia', 'tipo', 'puntaje', 'activa')
    list_filter = ('activa', 'tipo', 'categoria', 'competencia')
    search_fields = ('enunciado',)
    inlines = [OpcionRespuestaInline]

    @admin.display(description='Enunciado')
    def enunciado_corto(self, obj):
        return obj.enunciado[:60]


class CuestionarioPreguntaInline(admin.TabularInline):
    model = CuestionarioPregunta
    extra = 1
    fields = ('pregunta', 'orden')
    autocomplete_fields = ('pregunta',)


@admin.register(Cuestionario)
class CuestionarioAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'nombre', 'activo', 'fecha_apertura', 'fecha_cierre',
        'duracion_minutos', 'max_intentos', 'nota_maxima', 'nota_aprobar',
        'permitir_revision',
    )
    list_filter = ('activo',)
    search_fields = ('nombre',)
    inlines = [CuestionarioPreguntaInline]


@admin.register(OpcionRespuesta)
class OpcionRespuestaAdmin(admin.ModelAdmin):
    list_display = ('id', 'pregunta', 'texto', 'es_correcta', 'orden')
    list_filter = ('es_correcta',)
    search_fields = ('texto',)


admin.site.register(Intento)
admin.site.register(RespuestaIntento)
admin.site.register(Rol)
admin.site.register(SesionJWT)