import os
import shutil
import unicodedata
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Person, LogEntry
from .forms import SendBillsForm, PersonForm, FolderCreateForm, BillUploadForm
from email_send import send_email, CONTENT_TEMPLATE


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
            persons_without_bills = []  # Track persons who don't have matching bills
            found_bill_paths = {}  # Track which person owns each bill path
            duplicate_assignments = []  # Track duplicate bill assignments

            # Get bills for each person
            for person in Person.objects.all():
                person_bills = get_bills_for_person(month_bills_list, person)

                if person_bills:
                    # Check for duplicates
                    duplicate_bills = []
                    valid_bills = []

                    for bill in person_bills:
                        if bill in found_bill_paths:
                            # This bill was already assigned to someone else
                            original_owner = found_bill_paths[bill]
                            duplicate_bills.append(bill)

                            # Track for display
                            duplicate_assignments.append({
                                'bill': bill,
                                'skipped_email': person.email,
                                'original_email': original_owner
                            })
                        else:
                            valid_bills.append(bill)
                            found_bill_paths[bill] = person.email

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
                    elif duplicate_bills:
                        # If all bills were duplicates, add to persons_without_bills
                        persons_without_bills.append({
                            'id': person.id,
                            'email': person.email,
                            'bill_names': person.bill_names,
                            'all_duplicates': True,
                            'duplicate_bills': duplicate_bills
                        })
                else:
                    # No bills found for this person
                    persons_without_bills.append({
                        'id': person.id,
                        'email': person.email,
                        'bill_names': person.bill_names,
                        'all_duplicates': False,
                        'duplicate_bills': []
                    })

            # Find unassigned bills
            for month_bills in month_bills_list:
                for bill_path in month_bills['bills']:
                    if bill_path not in found_bill_paths:
                        unassigned_bills.append(bill_path)

            # Store in session and redirect to confirmation
            request.session['bill_assignments'] = bill_assignments
            request.session['unassigned_bills'] = unassigned_bills
            request.session['persons_without_bills'] = persons_without_bills
            request.session['duplicate_assignments'] = duplicate_assignments

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
    persons_without_bills = request.session.get('persons_without_bills', [])
    duplicate_assignments = request.session.get('duplicate_assignments', [])

    # Process each assignment to include email preview
    for assignment in bill_assignments:
        person = assignment['person']

        # Create email subject preview
        assignment['email_subject'] = f"račun {month} 2025"

        # Create email content preview
        extras_str = ""
        extras = None
        if person['extras']:
            extras = [x.strip() for x in person['extras'].split(',') if x.strip()]
            if extras:
                if len(extras) == 1:
                    extras_str = f" in {extras[0]}"
                elif len(extras) > 1:
                    extras_str = f", {', '.join(extras[:-1])} in {extras[-1]}"

        assignment['email_content'] = CONTENT_TEMPLATE.format(
            month=month, extras_str=extras_str
        )

        # Identify duplicate bill filenames
        filenames = {}
        duplicate_filenames = set()

        for bill_path in assignment['bills']:
            filename = os.path.basename(bill_path)
            if filename in filenames:
                duplicate_filenames.add(filename)
            else:
                filenames[filename] = True

        if duplicate_filenames:
            # Convert set to list for JSON serialization
            assignment['duplicate_bill_names'] = list(duplicate_filenames)

    if request.method == 'POST':
        # Store the selected email indices in session for processing
        selected_indices = []
        for i, _ in enumerate(bill_assignments):
            if f'send_{i}' in request.POST:
                selected_indices.append(i)

        if selected_indices:
            request.session['selected_indices'] = selected_indices
            return render(request, 'bills/sending_progress.html', {
                'total_emails': len(selected_indices)
            })
        else:
            messages.warning(request, 'Ni bil izbran noben email za pošiljanje.')
            return redirect('bills:index')

    # Prepare data for template
    context = {
        'month': month,
        'bill_assignments': bill_assignments,
        'unassigned_bills': unassigned_bills,
        'persons_without_bills': persons_without_bills,
        'duplicate_assignments': duplicate_assignments,
    }

    return render(request, 'bills/confirm_send_bills.html', context)


def send_email_async(request):
    """Process one email at a time and return progress."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Dovoljena je samo POST metoda'}, status=405)

    # Check if request is AJAX by looking for the X-Requested-With header
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Ajax zahteva je potrebna'}, status=400)

    # Get required session data
    month = request.session.get('month')
    bill_assignments = request.session.get('bill_assignments', [])
    selected_indices = request.session.get('selected_indices', [])
    persons_without_bills = request.session.get('persons_without_bills', [])
    duplicate_assignments = request.session.get('duplicate_assignments', [])

    if not month or not bill_assignments or not selected_indices:
        LogEntry.log_system_event(
            "Missing session data for email sending",
            LogEntry.ERROR,
            {"month": month is not None, "assignments": len(bill_assignments)}
        )
        return JsonResponse({'error': 'Manjkajo podatki seje'}, status=400)

    # Get the current progress index
    current_index = int(request.POST.get('current_index', 0))

    if current_index >= len(selected_indices):
        # We've processed all emails, clear session
        for key in ['month', 'bill_assignments', 'unassigned_bills',
                   'selected_indices', 'persons_without_bills',
                   'duplicate_assignments']:
            if key in request.session:
                del request.session[key]

        # Collect all selected person emails for filtering
        selected_emails = set()
        for idx in selected_indices:
            if idx < len(bill_assignments):
                selected_emails.add(bill_assignments[idx]['person']['email'])

        # Log duplicate bill assignments - only for selected emails
        logged_duplicates = 0
        for duplicate in duplicate_assignments:
            # Only log if the skipped email was actually selected for sending
            if duplicate['skipped_email'] in selected_emails:
                LogEntry.log_duplicate_bill_skipped(
                    email=duplicate['skipped_email'],
                    bill_path=duplicate['bill'],
                    original_recipient=duplicate['original_email']
                )
                logged_duplicates += 1

        # Log persons without matching bills - only for selected emails
        logged_persons_without_bills = 0
        for person in persons_without_bills:
            # Only log if the person was selected for sending
            if person['email'] in selected_emails:
                LogEntry.log_no_bills_found(
                    email=person['email'],
                    bill_names=person['bill_names']
                )
                logged_persons_without_bills += 1

        # Log summary of email sending process
        LogEntry.log_system_event(
            f"Bill sending summary for {month}: {len(selected_indices)} sent, "
            f"{logged_persons_without_bills} persons without bills, "
            f"{logged_duplicates} duplicate assignments",
            LogEntry.INFO,
            {
                "month": month,
                "emails_sent": len(selected_indices),
                "persons_without_bills": logged_persons_without_bills,
                "duplicate_assignments": logged_duplicates
            }
        )

        LogEntry.log_system_event(
            f"Completed sending {len(selected_indices)} emails for month {month}",
            LogEntry.SUCCESS,
            {"month": month, "email_count": len(selected_indices)}
        )

        return JsonResponse({
            'success': True,
            'completed': True,
            'message': f'Vsi emaili uspešno poslani ({len(selected_indices)})'
        })

    # Get the assignment index to process
    assignment_index = selected_indices[current_index]

    if assignment_index >= len(bill_assignments):
        LogEntry.log_system_event(
            f"Invalid assignment index: {assignment_index}",
            LogEntry.ERROR
        )
        return JsonResponse({'error': 'Neveljaven indeks dodelitve'}, status=400)

    # Get the assignment and send the email
    assignment = bill_assignments[assignment_index]
    person = assignment['person']
    bills = assignment['bills']

    # Extract extras if available
    extras = None
    if person['extras']:
        extras = [x.strip() for x in person['extras'].split(',') if x.strip()]

    result = {
        'success': False,
        'completed': False,
        'current_index': current_index,
        'total': len(selected_indices),
        'email': person['email']
    }

    try:
        response = send_email(
            month=month,
            to_email=person['email'],
            bill_names=bills,
            extras=extras
        )

        if response:
            result['success'] = True
            result['message'] = f'Email poslan: {person["email"]}'
            # Log successful email sending
            LogEntry.log_email_sent(
                email=person['email'],
                bill_files=bills,
                extras=extras,
                month=month
            )
        else:
            result['message'] = f'Neuspešno pošiljanje na: {person["email"]}'
            # Log email sending failure
            LogEntry.log_email_error(
                email=person['email'],
                error_message="Neuspešno pošiljanje (neznana napaka)",
                bill_files=bills,
                extras=extras,
                month=month
            )
    except Exception as e:
        result['message'] = f'Napaka: {str(e)}'
        # Log email sending error
        LogEntry.log_email_error(
            email=person['email'],
            error_message=str(e),
            bill_files=bills,
            extras=extras,
            month=month
        )

    # Increment for next request
    result['next_index'] = current_index + 1

    return JsonResponse(result)


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


def logs(request):
    """View for displaying log entries with filtering options."""
    # Get filters from request parameters
    level = request.GET.get('level', '')
    category = request.GET.get('category', '')
    search = request.GET.get('search', '')
    days = request.GET.get('days', '7')  # Default to last 7 days

    # Base queryset
    logs_queryset = LogEntry.objects.all()

    # Apply filters
    if level:
        logs_queryset = logs_queryset.filter(level=level)

    if category:
        logs_queryset = logs_queryset.filter(category=category)

    if search:
        logs_queryset = logs_queryset.filter(message__icontains=search)

    # Date filter
    try:
        days_int = int(days)
        if days_int > 0:
            from django.utils import timezone
            import datetime
            start_date = timezone.now() - datetime.timedelta(days=days_int)
            logs_queryset = logs_queryset.filter(timestamp__gte=start_date)
    except (ValueError, TypeError):
        # Invalid days value, ignore filter
        pass

    # Prepare context
    context = {
        'logs': logs_queryset,
        'levels': LogEntry.LEVEL_CHOICES,
        'categories': LogEntry.CATEGORY_CHOICES,
        'current_filters': {
            'level': level,
            'category': category,
            'search': search,
            'days': days,
        }
    }

    return render(request, 'bills/logs.html', context)
