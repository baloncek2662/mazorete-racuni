from django.db import models
import os


# Create your models here.
class Person(models.Model):
    email = models.EmailField()
    # Stored as comma-separated values
    bill_names = models.CharField(max_length=255)
    # Stored as comma-separated values
    extras = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.email} ({self.bill_names})"

    def get_bill_names_list(self):
        return self.bill_names.split('+')

    def get_extras_list(self):
        return self.extras.split(',') if self.extras else []


class BillFile(models.Model):
    file = models.FileField(upload_to='bills/%Y/%m/')
    month_folder = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return os.path.basename(self.file.name)

    def filename(self):
        return os.path.basename(self.file.name)

    def delete(self, *args, **kwargs):
        # Delete the file from storage when model is deleted
        self.file.delete()
        super().delete(*args, **kwargs)
