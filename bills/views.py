import os
import shutil
import unicodedata
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Person
from .forms import SendBillsForm, PersonForm, FolderCreateForm, BillUploadForm
from email_send import send_email


BILLS_DIR = "racuni"


def get_month_bills_list():
    bills = []
    for month_folder in os.listdir(BILLS_DIR):
        if os.path.isdir(os.path.join(BILLS_DIR, month_folder)):
            month_bills = os.listdir(os.path.join(BILLS_DIR, month_folder))
            bills.append({
                'name': month_folder,
                'bills': [
                    os.path.join(BILLS_DIR, month_folder, bill)
                    for bill in month_bills
                ]
            })
    return bills


def normalize_unicode(text):
    """
    Normalize Unicode text to NFC form and convert to ASCII for comparison.
    """
    # First normalize to composed form (NFC)
    normalized = unicodedata.normalize('NFC', text)

    # Then create an ASCII version by replacing special Slovenian characters
    ascii_version = normalized.replace('Š', 'S').replace('š', 's') \
                             .replace('Č', 'C').replace('č', 'c') \
                             .replace('Ž', 'Z').replace('ž', 'z')

    return normalized, ascii_version


def get_bills_for_person(month_bills_list, person):
    bills = []
    person_bill_names = person.get_bill_names_list()

    for month_bills in month_bills_list:
        for bill in month_bills['bills']:
            bill_basename = os.path.basename(bill)
            bill_name_without_ext = os.path.splitext(bill_basename)[0]

            # Normalize the bill name
            norm_bill_name, ascii_bill_name = normalize_unicode(bill_name_without_ext)

            # Check if bill matches any of the person's bill names
            for person_bill in person_bill_names:
                if not person_bill.strip():
                    continue

                # Normalize person's bill name
                norm_person_bill, ascii_person_bill = normalize_unicode(person_bill)

                # Try multiple matching strategies with normalized strings
                if (norm_bill_name == norm_person_bill):
                    bills.append(bill)
                    break

    return bills


def index(request):
    if request.method == 'POST':
        form = SendBillsForm(request.POST)
        if form.is_valid():
            # Store data in session for the confirmation page
            month = form.cleaned_data['month']
            request.session['month'] = month

            # Calculate bill assignments
            month_bills_list = get_month_bills_list()

            # Prepare the bill assignment data
            bill_assignments = []
            unassigned_bills = []
            found_bill_paths = set()

            # Get bills for each person
            for person in Person.objects.all():
                person_bills = get_bills_for_person(month_bills_list, person)

                if person_bills:
                    # Check for duplicates
                    duplicate_bills = []
                    valid_bills = []

                    for bill in person_bills:
                        if bill in found_bill_paths:
                            duplicate_bills.append(bill)
                        else:
                            valid_bills.append(bill)
                            found_bill_paths.add(bill)

                    # Add to assignments if there are valid bills
                    if valid_bills:
                        bill_assignments.append({
                            'person': {
                                'id': person.id,
                                'email': person.email,
                                'bill_names': person.bill_names,
                                'extras': person.extras
                            },
                            'bills': valid_bills,
                            'duplicate_bills': duplicate_bills
                        })

            # Find unassigned bills
            for month_bills in month_bills_list:
                for bill_path in month_bills['bills']:
                    if bill_path not in found_bill_paths:
                        unassigned_bills.append(bill_path)

            # Store in session and redirect to confirmation
            request.session['bill_assignments'] = bill_assignments
            request.session['unassigned_bills'] = unassigned_bills

            return redirect('bills:confirm_send_bills')
    else:
        form = SendBillsForm()

    return render(request, 'bills/index.html', {'form': form})


def confirm_send_bills(request):
    if 'month' not in request.session or 'bill_assignments' not in request.session:
        messages.error(request, 'Ni podatkov za potrditev. Prosimo, poskusite znova.')
        return redirect('bills:index')

    month = request.session.get('month')
    bill_assignments = request.session.get('bill_assignments', [])
    unassigned_bills = request.session.get('unassigned_bills', [])

    if request.method == 'POST':
        emails_sent = 0
        for i, assignment in enumerate(bill_assignments):
            if f'send_{i}' in request.POST:
                # Send email to this person
                person = assignment['person']
                bills = assignment['bills']

                # Extract extras if available
                extras = None
                if person['extras']:
                    extras = [x.strip() for x in person['extras'].split(',') if x.strip()]

                try:
                    response = send_email(
                        month=month,
                        to_email=person['email'],
                        bill_names=bills,
                        extras=extras
                    )
                    if response:
                        emails_sent += 1
                except Exception as e:
                    error_msg = f"Napaka pri pošiljanju računa za {person['email']}: {str(e)}"
                    messages.error(request, error_msg)

        # Clear session data
        for key in ['month', 'bill_assignments', 'unassigned_bills']:
            if key in request.session:
                del request.session[key]

        if emails_sent > 0:
            plural = 'e' if emails_sent > 1 else ''
            messages.success(request, f'Uspešno poslanih {emails_sent} email{plural}.')
        else:
            messages.warning(request, 'Ni bil poslan noben email.')

        return redirect('bills:index')

    # Prepare data for template
    context = {
        'month': month,
        'bill_assignments': bill_assignments,
        'unassigned_bills': unassigned_bills,
    }

    return render(request, 'bills/confirm_send_bills.html', context)


def manage_persons(request):
    if request.method == 'POST':
        form = PersonForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Oseba uspešno dodana!')
            return redirect('bills:manage_persons')
    else:
        form = PersonForm()

    persons = Person.objects.all()
    return render(
        request,
        'bills/manage_persons.html',
        {'form': form, 'persons': persons}
    )


def edit_person(request, person_id):
    person = get_object_or_404(Person, pk=person_id)

    if request.method == 'POST':
        form = PersonForm(request.POST, instance=person)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Podatki o osebi so bili uspešno posodobljeni!'
            )
            return redirect('bills:manage_persons')
    else:
        form = PersonForm(instance=person)

    return render(
        request,
        'bills/edit_person.html',
        {'form': form, 'person': person}
    )


def delete_person(request, person_id):
    person = get_object_or_404(Person, pk=person_id)

    if request.method == 'POST':
        person.delete()
        messages.success(request, f'Oseba {person.email} je bila izbrisana!')
        return redirect('bills:manage_persons')

    return render(
        request,
        'bills/delete_person.html',
        {'person': person}
    )


def manage_bills(request):
    # Get all folders
    folders = []
    if os.path.exists(BILLS_DIR):
        folders = [
            folder for folder in os.listdir(BILLS_DIR)
            if os.path.isdir(os.path.join(BILLS_DIR, folder))
        ]

    # Create a new folder
    folder_form = FolderCreateForm()
    if request.method == 'POST' and 'create_folder' in request.POST:
        folder_form = FolderCreateForm(request.POST)
        if folder_form.is_valid():
            folder_name = folder_form.cleaned_data['name']
            folder_path = os.path.join(BILLS_DIR, folder_name)

            if not os.path.exists(BILLS_DIR):
                os.makedirs(BILLS_DIR)

            if os.path.exists(folder_path):
                messages.error(
                    request,
                    f'Mapa "{folder_name}" že obstaja!'
                )
            else:
                os.makedirs(folder_path)
                messages.success(
                    request,
                    f'Mapa "{folder_name}" uspešno ustvarjena!'
                )
            return redirect('bills:manage_bills')

    # Upload a bill
    bill_form = BillUploadForm()
    if folders:
        bill_form.fields['month_folder'].widget.choices = [
            (folder, folder) for folder in folders
        ]

    if request.method == 'POST' and 'upload_bill' in request.POST:
        bill_form = BillUploadForm(request.POST, request.FILES)
        bill_form.fields['month_folder'].widget.choices = [
            (folder, folder) for folder in folders
        ]

        if bill_form.is_valid():
            bill = bill_form.save(commit=False)

            # Save the file to the appropriate folder in racuni
            file_obj = bill.file
            month_folder = bill.month_folder
            filename = file_obj.name

            # Create the destination path
            dest_folder = os.path.join(BILLS_DIR, month_folder)
            dest_path = os.path.join(dest_folder, filename)

            # Make sure the folder exists
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)

            # Save the file to the racuni folder
            with open(dest_path, 'wb+') as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)

            messages.success(
                request,
                f'Račun "{filename}" uspešno naložen v mapo "{month_folder}"!'
            )
            return redirect('bills:manage_bills')

    # Get all bills in each folder
    folder_bills = {}
    for folder in folders:
        folder_path = os.path.join(BILLS_DIR, folder)
        folder_bills[folder] = [
            f for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]

    return render(
        request,
        'bills/manage_bills.html',
        {
            'folder_form': folder_form,
            'bill_form': bill_form,
            'folders': folders,
            'folder_bills': folder_bills
        }
    )


def delete_folder(request, folder_name):
    folder_path = os.path.join(BILLS_DIR, folder_name)

    if request.method == 'POST':
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            messages.success(
                request,
                f'Mapa "{folder_name}" je bila izbrisana!'
            )
        else:
            messages.error(
                request,
                f'Mapa "{folder_name}" ne obstaja!'
            )
        return redirect('bills:manage_bills')

    return render(
        request,
        'bills/delete_folder.html',
        {'folder_name': folder_name}
    )


def delete_bill(request, folder_name, bill_name):
    bill_path = os.path.join(BILLS_DIR, folder_name, bill_name)

    if request.method == 'POST':
        if os.path.exists(bill_path):
            os.remove(bill_path)
            messages.success(
                request,
                f'Račun "{bill_name}" je bil izbrisan!'
            )
        else:
            messages.error(
                request,
                f'Račun "{bill_name}" ne obstaja!'
            )
        return redirect('bills:manage_bills')

    return render(
        request,
        'bills/delete_bill.html',
        {'folder_name': folder_name, 'bill_name': bill_name}
    )
