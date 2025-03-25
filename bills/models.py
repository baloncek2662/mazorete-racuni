from django.db import models
import os
from django.utils import timezone


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
        help_text="Neobvezne dodatne informacije ločene z vejicami"
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


class LogEntry(models.Model):
    """Model for logging important events in the application."""

    # Log levels
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    SUCCESS = 'SUCCESS'

    LEVEL_CHOICES = [
        (INFO, 'Informacija'),
        (WARNING, 'Opozorilo'),
        (ERROR, 'Napaka'),
        (SUCCESS, 'Uspeh'),
    ]

    # Log categories
    EMAIL = 'EMAIL'
    SYSTEM = 'SYSTEM'
    USER = 'USER'

    CATEGORY_CHOICES = [
        (EMAIL, 'Email'),
        (SYSTEM, 'Sistem'),
        (USER, 'Uporabnik'),
    ]

    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Čas")
    level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        default=INFO,
        verbose_name="Tip"
    )
    category = models.CharField(
        max_length=10,
        choices=CATEGORY_CHOICES,
        default=SYSTEM,
        verbose_name="Kategorija"
    )
    message = models.TextField(verbose_name="Sporočilo")
    details = models.JSONField(blank=True, null=True, verbose_name="Podrobnosti")

    class Meta:
        verbose_name = "Dnevniški zapis"
        verbose_name_plural = "Dnevniški zapisi"
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.level}: {self.message[:50]}"

    @classmethod
    def log_email_sent(cls, email, bill_files, extras=None, month=None):
        """Log a successful email sending event."""
        details = {
            "email": email,
            "bill_files": bill_files,
            "extras": extras,
            "month": month,
        }
        return cls.objects.create(
            level=cls.SUCCESS,
            category=cls.EMAIL,
            message=f"Email poslan na: {email} ({len(bill_files)} prilog)",
            details=details
        )

    @classmethod
    def log_email_error(cls, email, error_message, bill_files=None, extras=None, month=None):
        """Log an email sending error."""
        details = {
            "email": email,
            "error": str(error_message),
            "bill_files": bill_files,
            "extras": extras,
            "month": month,
        }
        return cls.objects.create(
            level=cls.ERROR,
            category=cls.EMAIL,
            message=f"Napaka pri pošiljanju na: {email} - {error_message}",
            details=details
        )

    @classmethod
    def log_no_bills_found(cls, email, bill_names):
        """Log when no bills match a person's criteria."""
        details = {
            "email": email,
            "bill_names": bill_names,
        }
        return cls.objects.create(
            level=cls.WARNING,
            category=cls.EMAIL,
            message=f"Ni najdenih računov za: {email}",
            details=details
        )

    @classmethod
    def log_duplicate_bill_skipped(cls, email, bill_path, original_recipient):
        """Log when a bill is skipped because it was already assigned to another person."""
        details = {
            "email": email,
            "bill": bill_path,
            "original_recipient": original_recipient,
        }
        return cls.objects.create(
            level=cls.WARNING,
            category=cls.EMAIL,
            message=f"Preskok podvojenega računa {os.path.basename(bill_path)} za: {email}",
            details=details
        )

    @classmethod
    def log_system_event(cls, message, level=INFO, details=None):
        """Log a general system event."""
        return cls.objects.create(
            level=level,
            category=cls.SYSTEM,
            message=message,
            details=details
        )
