import PySimpleGUI as sg
from datetime import datetime, timedelta
import db


def format_row(r):
    return f"{r['id']} | {r['borrower']} | {r['outfit_code']} | due {r['due_at'][:10]}"


def run_gui(db_path: str):
    sg.theme('LightBlue')

    # Left column: borrowers & outfits
    borrowers_col = [
        [sg.Text('Borrowers')],
        [sg.Listbox(values=[b['name'] for b in db.list_borrowers(db_path)], size=(30, 10), key='-BORROWERS-')],
        [sg.Button('Add borrower', key='-ADD-BORR-')]
    ]

    outfits_col = [
        [sg.Text('Outfits')],
        [sg.Listbox(values=[f"{o['code']} ({o['size'] or ''})" for o in db.list_outfits(db_path)], size=(30, 10), key='-OUTFITS-')],
        [sg.Button('Add outfit', key='-ADD-OUT-')]
    ]

    # Right column: active rentals & actions
    rentals_col = [
        [sg.Text('Active rentals (not returned)')],
        [sg.Listbox(values=[format_row(r) for r in db.list_active_rentals(db_path)], size=(60, 10), key='-RENTALS-')],
        [sg.Button('Checkout', key='-CHECKOUT-'), sg.Button('Return', key='-RETURN-')]
    ]

    overdue_col = [
        [sg.Text('Overdue')],
        [sg.Listbox(values=[format_row(r) for r in db.list_overdue(db_path)], size=(60, 6), key='-OVERDUE-')],
        [sg.Button('Refresh', key='-REFRESH-')]
    ]

    layout = [
        [sg.Column(borrowers_col), sg.VerticalSeparator(), sg.Column(outfits_col), sg.VerticalSeparator(), sg.Column(rentals_col)],
        [sg.HorizontalSeparator()],
        [sg.Column(overdue_col)]
    ]

    window = sg.Window('Outfit Manager', layout, finalize=True)

    def refresh_all():
        window['-BORROWERS-'].update([b['name'] for b in db.list_borrowers(db_path)])
        window['-OUTFITS-'].update([f"{o['code']} ({o['size'] or ''})" for o in db.list_outfits(db_path)])
        window['-RENTALS-'].update([format_row(r) for r in db.list_active_rentals(db_path)])
        window['-OVERDUE-'].update([format_row(r) for r in db.list_overdue(db_path)])

    # helper to show popups near the main window (avoids centering between monitors)
    def popup_get_text_local(*args, **kwargs):
        loc = (0, 0)
        try:
            if hasattr(window, 'current_location'):
                loc = window.current_location()
            elif hasattr(window, 'CurrentLocation'):
                loc = window.CurrentLocation()
        except Exception:
            loc = (0, 0)
        kwargs.setdefault('location', loc)
        kwargs.setdefault('keep_on_top', True)
        return sg.popup_get_text(*args, **kwargs)

    def popup_local(*args, **kwargs):
        loc = (0, 0)
        try:
            if hasattr(window, 'current_location'):
                loc = window.current_location()
            elif hasattr(window, 'CurrentLocation'):
                loc = window.CurrentLocation()
        except Exception:
            loc = (0, 0)
        kwargs.setdefault('location', loc)
        kwargs.setdefault('keep_on_top', True)
        return sg.popup(*args, **kwargs)

    def popup_error_local(*args, **kwargs):
        loc = (0, 0)
        try:
            if hasattr(window, 'current_location'):
                loc = window.current_location()
            elif hasattr(window, 'CurrentLocation'):
                loc = window.CurrentLocation()
        except Exception:
            loc = (0, 0)
        kwargs.setdefault('location', loc)
        kwargs.setdefault('keep_on_top', True)
        return sg.popup_error(*args, **kwargs)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break

        if event == '-ADD-BORR-':
            name = popup_get_text_local('Borrower name')
            if name:
                phone = popup_get_text_local('Phone (optional)')
                email = popup_get_text_local('Email (optional)')
                db.add_borrower(db_path, name, phone, email)
                refresh_all()

        if event == '-ADD-OUT-':
            code = popup_get_text_local('Outfit code (unique)')
            if code:
                desc = popup_get_text_local('Description (optional)')
                size = popup_get_text_local('Size (optional)')
                try:
                    db.add_outfit(db_path, code, desc, size)
                except Exception as e:
                    popup_error_local('Error adding outfit', str(e))
                refresh_all()

        if event == '-CHECKOUT-':
            borrowers = db.list_borrowers(db_path)
            outfits = db.list_outfits(db_path)
            if not borrowers or not outfits:
                popup_local('Add at least one borrower and one outfit first')
                continue
            b_names = [b['name'] for b in borrowers]
            o_codes = [o['code'] for o in outfits]
            b_choice = popup_get_text_local('Borrower name (choose exact)', 'Checkout', default_text=b_names[0])
            if not b_choice:
                continue
            o_choice = popup_get_text_local('Outfit code (choose exact)', 'Checkout', default_text=o_codes[0])
            if not o_choice:
                continue
            days = popup_get_text_local('Days to lend (default 7)', default_text='7')
            try:
                days_i = int(days)
            except Exception:
                days_i = 7
            borrower = db.get_borrower_by_name(db_path, b_choice)
            outfit = db.get_outfit_by_code(db_path, o_choice)
            if not borrower or not outfit:
                popup_local('Borrower or outfit not found')
                continue
            due = (datetime.utcnow() + timedelta(days=days_i)).isoformat()
            db.checkout(db_path, borrower['id'], outfit['id'], due)
            refresh_all()

        if event == '-RETURN-':
            sel = values['-RENTALS-']
            if not sel:
                popup_local('Select an active rental from the list to return')
                continue
            # listbox item formatted as: id | borrower | outfit_code | due YYYY-MM-DD
            item = sel[0]
            rental_id = int(item.split('|')[0].strip())
            db.return_rental(db_path, rental_id)
            refresh_all()

        if event == '-REFRESH-':
            refresh_all()

    window.close()
