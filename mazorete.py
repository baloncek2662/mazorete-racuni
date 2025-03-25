import os
import csv

from email_send import send_email


BILLS_DIR = "racuni"
MAPPING_FILE = "seznam.csv"


class MonthBills:
    def __init__(self, name):
        self.name = name
        self.bill_paths = []

    def add_bill(self, bill_path):
        self.bill_paths.append(bill_path)

    def __repr__(self):
        return f"MonthBills(name={self.name}, bills={self.bill_paths})"


class Person:
    def __init__(self, email, bill_names, extras=None):
        self.email = email
        self.bill_names = bill_names
        self.extras = extras if extras else []

    def __repr__(self):
        return f"Person(email={self.email}, bill_names={self.bill_names}, extras={self.extras})"


def get_month_bills_list() -> list[MonthBills]:
    bills = []
    # Each folder in the 'racuni' dir is a month. Parse through each of them and get the bills.
    for month_folder in os.listdir(BILLS_DIR):
        if os.path.isdir(os.path.join(BILLS_DIR, month_folder)):
            month = MonthBills(month_folder)
            month_bills = os.listdir(os.path.join(BILLS_DIR, month_folder))
            for bill in month_bills:
                # append full path to the bill
                bill_path = os.path.join(BILLS_DIR, month_folder, bill)
                month.add_bill(bill_path)
            bills.append(month)
    return bills


def get_persons_list() -> list[Person]:
    persons_list = []
    with open(f"{BILLS_DIR}/{MAPPING_FILE}", "r") as f:
        reader = csv.reader(f)
        next(reader)  # skip the header
        for line in reader:
            if len(line) < 2 or not line[0] or not line[1]:
                raise ValueError(f"Napaka v vrstici: {line}")
            email = line[0]
            bill_names = line[1].split("+")
            extras = line[2:] if len(line) > 2 else []
            new_person = Person(email, bill_names, extras)
            persons_list.append(new_person)
    return persons_list


# Bills may exist for several months backwards. However the email subject should only name the latest one
def send_bills_for_persons(month_bills_list: list[MonthBills], persons_list: list[Person], curr_month: str) -> None:
    found_bill_paths = set()  # Used to check for duplicates in month_bills.bill_paths

    for person in persons_list:
        person_bills = get_bills_for_person(month_bills_list, person)
        if len(person_bills) == 0:
            print(f"Oseba {person} nima nobenega računa! Email tej osebi ne bo poslan.")
            continue

        for bill in person_bills:
            bill_name = bill
            if bill_name in found_bill_paths:
                confirmation = input(f"OPOZORILO! Ta račun je bil že poslan: {bill_name}. Vnesi 'da' če želiš da se račun vseeno pošlje: ").strip().lower()
                if confirmation != "da":
                    print("Nadaljevanje preklicano.")
                    break
            else:
                found_bill_paths.add(bill_name)
        else:
            # If the loop didn't break because the didn't want to send duplicate bills, send the email
            confirmation = input(f"Pošlji račune {person_bills} z dodatki {person.extras} osebi {person.email}? Vnesi 'da' za potrditev: ").strip().lower()
            if confirmation == "da":
                send_email(person.email, curr_month, person_bills, person.extras)
            else:
                print("Pošiljanje emaila preklicano.")

    for month_bills in month_bills_list:
        for bill_path in month_bills.bill_paths:
            if bill_path not in found_bill_paths:
                print(f"OPOZORILO! Račun {bill_path} ni bil poslan nobeni osebi!")


def get_bills_for_person(month_bills_list: list[MonthBills], person: Person) -> list[str]:
    bills = []
    for month_bills in month_bills_list:
        for bill in month_bills.bill_paths:
            for person_bill in person.bill_names:
                if bill.endswith(f"{person_bill}.pdf"):
                    bills.append(bill)
    return bills


if __name__ == "__main__":
    month_bills_list = get_month_bills_list()
    persons_list = get_persons_list()
    month = input("Vnesi mesec za katerega pošiljaš račune: ").strip()
    confirmation = input(f"Računi bodo poslani z naslovom za mesec {month}. Vnesi 'da' za potrditev: ").strip().lower()
    if confirmation == "da":
        send_bills_for_persons(month_bills_list, persons_list, month)
    else:
        print("Pošiljanje računov preklicano.")
