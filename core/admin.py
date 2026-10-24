from django.contrib import admin


from .models import (
    Categoria,
    Pregunta,
    OpcionRespuesta,
    Cuestionario,
    CuestionarioPregunta,
    Intento,
    RespuestaIntento
)

admin.site.register(Categoria)
admin.site.register(Pregunta)
admin.site.register(OpcionRespuesta)
admin.site.register(Cuestionario)
admin.site.register(CuestionarioPregunta)
admin.site.register(Intento)
admin.site.register(RespuestaIntento)
