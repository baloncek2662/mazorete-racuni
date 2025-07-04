# Generated by Django 5.1.7 on 2025-03-25 18:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bills", "0003_alter_person_bill_names_alter_person_extras"),
    ]

    operations = [
        migrations.AlterField(
            model_name="billfile",
            name="file",
            field=models.FileField(upload_to="bills/%Y/%m/", verbose_name="Datoteka"),
        ),
        migrations.AlterField(
            model_name="billfile",
            name="month_folder",
            field=models.CharField(max_length=50, verbose_name="Mapa meseca"),
        ),
        migrations.AlterField(
            model_name="billfile",
            name="uploaded_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Čas nalaganja"),
        ),
        migrations.AlterField(
            model_name="person",
            name="bill_names",
            field=models.CharField(
                help_text="Vnesite imena računov ločena z znakom + (npr. GASPER+JANEZ+MATEJA)",
                max_length=255,
                verbose_name="Imena računov",
            ),
        ),
        migrations.AlterField(
            model_name="person",
            name="email",
            field=models.EmailField(max_length=254, verbose_name="E-pošta"),
        ),
        migrations.AlterField(
            model_name="person",
            name="extras",
            field=models.TextField(
                blank=True,
                help_text="Neobvezne dodatne informacije ločene z vejicami",
                null=True,
                verbose_name="Dodatki",
            ),
        ),
    ]
