from django import forms
from .models import Person, BillFile


class SendBillsForm(forms.Form):
    month = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ['email', 'bill_names', 'extras']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bill_names': forms.TextInput(attrs={'class': 'form-control'}),
            'extras': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
        }


class FolderCreateForm(forms.Form):
    name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Vnesite ime mape (na primer 'januar', 'februar')"
    )


class BillUploadForm(forms.ModelForm):
    class Meta:
        model = BillFile
        fields = ['file', 'month_folder']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'month_folder': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This will be populated in the view with available folders
        self.fields['month_folder'].widget.choices = []
