import io
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

from openpyxl import Workbook, load_workbook

from .models import Categoria, Competencia, Pregunta


COLUMNAS_ESPERADAS = [
    'categoria',
    'competencia',
    'tipo',
    'texto_base',
    'enunciado',
    'retroalimentacion',
    'explicacion',
    'puntaje',
    'opcion_a',
    'opcion_b',
    'opcion_c',
    'opcion_d',
    'correctas',
]

LETRAS = ('A', 'B', 'C', 'D')
TIPOS_VALIDOS = {Pregunta.TIPO_UNICA, Pregunta.TIPO_MULTIPLE, Pregunta.TIPO_VF}


@dataclass
class FilaValidada:
    numero: int
    errores: list = field(default_factory=list)
    datos: dict = field(default_factory=dict)

    @property
    def valida(self):
        return not self.errores


def construir_plantilla():
    wb = Workbook()
    ws = wb.active
    ws.title = 'Preguntas'
    ws.append(COLUMNAS_ESPERADAS)

    ejemplo = [
        'Matematicas',
        'Razonamiento cuantitativo',
        'UNICA',
        'Contexto de la pregunta',
        'Cuanto es 2 + 2?',
        'La suma de dos y dos es cuatro.',
        'Suma basica de enteros',
        1.0,
        '3',
        '4',
        '5',
        '22',
        'B',
    ]
    ws.append(ejemplo)

    for idx in range(1, len(COLUMNAS_ESPERADAS) + 1):
        letra = ws.cell(row=1, column=idx).column_letter
        ws.column_dimensions[letra].width = 22

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _normalizar(valor):
    if valor is None:
        return ''
    if isinstance(valor, str):
        return valor.strip()
    return valor


def _parsear_correctas(raw, tipo):
    if raw is None or str(raw).strip() == '':
        return []
    if isinstance(raw, str):
        partes = [p.strip().upper() for p in raw.split(',') if p.strip()]
    else:
        partes = [str(raw).strip().upper()]
    if tipo == Pregunta.TIPO_MULTIPLE:
        return partes
    if tipo in (Pregunta.TIPO_UNICA, Pregunta.TIPO_VF):
        return partes[:1]
    return partes


def _leer_filas(file_obj):
    try:
        wb = load_workbook(file_obj, data_only=True)
    except Exception as e:
        raise ValueError(f'No se pudo leer el archivo Excel: {e}')
    ws = wb.active
    filas = list(ws.iter_rows(values_only=True))
    if not filas:
        return []
    encabezados = [_normalizar(c).lower() if isinstance(c, str) else c for c in filas[0]]
    faltantes = [c for c in COLUMNAS_ESPERADAS if c not in encabezados]
    if faltantes:
        raise ValueError(f'Faltan columnas en el Excel: {", ".join(faltantes)}')
    return filas[1:], encabezados


def validar_excel(file_obj):
    try:
        filas, encabezados = _leer_filas(file_obj)
    except ValueError as e:
        return {'error_global': str(e), 'filas': []}

    indice = {col: encabezados.index(col) for col in COLUMNAS_ESPERADAS}
    enunciados_en_archivo = set()
    resultados = []

    categorias = {c.nombre.lower(): c for c in Categoria.objects.all()}
    competencias = {c.nombre.lower(): c for c in Competencia.objects.all()}

    for offset, fila in enumerate(filas, start=2):
        if all(v is None or (isinstance(v, str) and v.strip() == '') for v in fila):
            continue

        def val(col):
            idx = indice[col]
            return _normalizar(fila[idx]) if idx < len(fila) else None

        errores = []

        categoria_nombre = val('categoria')
        competencia_nombre = val('competencia')
        tipo = val('tipo')
        texto_base = val('texto_base') or ''
        enunciado = val('enunciado')
        retroalimentacion = val('retroalimentacion') or ''
        explicacion = val('explicacion') or ''
        puntaje_raw = fila[indice['puntaje']] if indice['puntaje'] < len(fila) else None
        correctas_raw = fila[indice['correctas']] if indice['correctas'] < len(fila) else None
        opciones_raw = {letra: val(f'opcion_{letra.lower()}') for letra in LETRAS}

        if not categoria_nombre:
            errores.append('categoria es obligatoria')
        elif str(categoria_nombre).lower() not in categorias:
            errores.append(f'la categoria "{categoria_nombre}" no existe')

        if not competencia_nombre:
            errores.append('competencia es obligatoria')
        elif str(competencia_nombre).lower() not in competencias:
            errores.append(f'la competencia "{competencia_nombre}" no existe')

        if not enunciado:
            errores.append('enunciado es obligatorio')
        else:
            normalizado = str(enunciado).strip().lower()
            if normalizado in enunciados_en_archivo:
                errores.append('enunciado duplicado dentro del archivo')
            elif Pregunta.objects.filter(enunciado__iexact=normalizado).exists():
                errores.append('ya existe una pregunta con este enunciado en el banco')
            enunciados_en_archivo.add(normalizado)

        if not tipo:
            errores.append('tipo es obligatorio')
        elif tipo not in TIPOS_VALIDOS:
            errores.append(f'tipo invalido: debe ser {", ".join(sorted(TIPOS_VALIDOS))}')

        try:
            puntaje = (
                Decimal(str(puntaje_raw))
                if puntaje_raw not in (None, '')
                else Decimal('1')
            )
            if puntaje <= 0:
                errores.append('puntaje debe ser mayor que cero')
        except (TypeError, ValueError, InvalidOperation):
            puntaje = Decimal('1')
            errores.append('puntaje debe ser numerico')

        correctas = _parsear_correctas(correctas_raw, tipo) if tipo else []
        opciones_validas = {k: v for k, v in opciones_raw.items() if v}
        if len(opciones_validas) < 2:
            errores.append('debe registrar al menos 2 opciones')
        if not correctas:
            errores.append('debe indicar al menos una opcion correcta en "correctas"')
        for letra in correctas:
            if letra not in LETRAS:
                errores.append(f'opcion correcta invalida: {letra}')
            elif letra not in opciones_validas:
                errores.append(f'la opcion {letra} esta marcada como correcta pero no tiene texto')

        if tipo in (Pregunta.TIPO_UNICA, Pregunta.TIPO_MULTIPLE) and len(correctas) != 1:
            errores.append('para UNICA debe haber exactamente 1 correcta')
        if tipo == Pregunta.TIPO_VF:
            if len(opciones_validas) != 2:
                errores.append('para VF debe haber exactamente 2 opciones')
            if len(correctas) != 1:
                errores.append('para VF debe haber exactamente 1 correcta')

        datos = {
            'categoria': categoria_nombre,
            'competencia': competencia_nombre,
            'tipo': tipo,
            'texto_base': texto_base,
            'enunciado': enunciado,
            'retroalimentacion': retroalimentacion,
            'explicacion': explicacion,
            'puntaje': puntaje,
            'opciones': [
                {'letra': letra, 'texto': opciones_raw[letra]}
                for letra in LETRAS if opciones_raw[letra]
            ],
            'correctas': correctas,
        }
        resultados.append(FilaValidada(numero=offset, errores=errores, datos=datos))

    return {'error_global': None, 'filas': resultados}


def guardar_filas(filas_validadas):
    creadas = 0
    for fila in filas_validadas:
        if not fila.valida:
            raise ValueError(f'Fila {fila.numero} invalida')
        datos = fila.datos
        categoria = Categoria.objects.get(nombre__iexact=datos['categoria'])
        competencia = Competencia.objects.get(nombre__iexact=datos['competencia'])
        pregunta = Pregunta(
            categoria=categoria,
            competencia=competencia,
            texto_base=datos['texto_base'],
            enunciado=datos['enunciado'],
            retroalimentacion=datos['retroalimentacion'],
            explicacion=datos['explicacion'],
            tipo=datos['tipo'],
            puntaje=Decimal(str(datos['puntaje'])),
            activa=True,
        )
        pregunta.full_clean(exclude=['opciones'])
        pregunta.save()
        for opcion in datos['opciones']:
            from .models import OpcionRespuesta
            OpcionRespuesta.objects.create(
                pregunta=pregunta,
                texto=opcion['texto'],
                es_correcta=opcion['letra'] in datos['correctas'],
                orden=LETRAS.index(opcion['letra']) + 1,
            )
        creadas += 1
    return creadas  