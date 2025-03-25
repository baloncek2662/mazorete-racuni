from django.db import models
import os


# Create your models here.
class Person(models.Model):
    email = models.EmailField(verbose_name="E-pošta")
    # Stored as comma-separated values
    bill_names = models.CharField(
        max_length=255,
        verbose_name="Imena računov",
        help_text="Vnesite imena računov ločena z znakom + (npr. MARTIČ+FINK)"
    )
    # Stored as comma-separated values
    extras = models.TextField(
        blank=True,
        null=True,
        verbose_name="Dodatki",
        help_text="Neobvezne dodatne informacije ločene z vejicami. Dodatki morajo biti ločeni Z VEJICO BREZ PRESLEDKOV! Pazi da dodatke navajaš v tožilniku. Če na primer pošiljaš račune za mesec februar se bodo dodatki v obliki 'članarino za mesec januar 2025,kikle' prevedli v tekst 'v priponki vam pošiljam račun za članarino za mesec februar 2025, članarino za mesec januar 2025 in kikle.'"
    )

    def __str__(self):
        return f"{self.email} ({self.bill_names})"

    def get_bill_names_list(self):
        return self.bill_names.split('+')

    def get_extras_list(self):
        return self.extras.split(',') if self.extras else []


class BillFile(models.Model):
    file = models.FileField(upload_to='bills/%Y/%m/', verbose_name="Datoteka")
    month_folder = models.CharField(max_length=50, verbose_name="Mapa meseca")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Čas nalaganja")

    def __str__(self):
        return os.path.basename(self.file.name)

    def filename(self):
        return os.path.basename(self.file.name)

    def delete(self, *args, **kwargs):
        # Delete the file from storage when model is deleted
        self.file.delete()
        super().delete(*args, **kwargs)
