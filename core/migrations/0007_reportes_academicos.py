import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_importacionpreguntas_archivo_hash_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PeriodoAcademico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anio', models.PositiveSmallIntegerField()),
                ('nombre', models.CharField(max_length=20, unique=True)),
            ],
            options={
                'ordering': ('-anio', 'nombre'),
            },
        ),
        migrations.CreateModel(
            name='CursoGrupo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('periodo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cursos', to='core.periodoacademico')),
            ],
            options={
                'ordering': ('periodo__anio', 'nombre'),
            },
        ),
        migrations.CreateModel(
            name='Matricula',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identificacion', models.CharField(blank=True, max_length=40)),
                ('activa', models.BooleanField(default=True)),
                ('curso', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='matriculas', to='core.cursogrupo')),
                ('estudiante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matriculas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('curso__nombre', 'estudiante__last_name', 'estudiante__first_name'),
            },
        ),
        migrations.AddField(
            model_name='cuestionario',
            name='curso',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cuestionarios', to='core.cursogrupo'),
        ),
        migrations.AddField(
            model_name='intento',
            name='curso',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='intentos', to='core.cursogrupo'),
        ),
        migrations.AddField(
            model_name='intento',
            name='periodo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='intentos', to='core.periodoacademico'),
        ),
        migrations.AlterModelOptions(
            name='cuestionario',
            options={
                'ordering': ('-fecha_apertura',),
                'permissions': [
                    ('manage_users', 'Puede administrar usuarios'),
                    ('manage_roles', 'Puede administrar roles y permisos'),
                    ('manage_question_bank', 'Puede administrar el banco de preguntas'),
                    ('configure_quizzes', 'Puede configurar cuestionarios'),
                    ('view_results', 'Puede consultar resultados'),
                    ('ver_reportes', 'Puede consultar reportes académicos'),
                    ('ver_identificacion_estudiante', 'Puede consultar identificaciones de estudiantes'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='cursogrupo',
            constraint=models.UniqueConstraint(fields=('periodo', 'nombre'), name='uq_curso_periodo_nombre'),
        ),
        migrations.AddConstraint(
            model_name='matricula',
            constraint=models.UniqueConstraint(fields=('estudiante', 'curso'), name='uq_matricula_estudiante_curso'),
        ),
    ]
