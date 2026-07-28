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
        [sg.Listbox(values=[b['name'] for b in db.list_borrowers(db_path) if b['name'] != '<deleted borrower>'], size=(30, 10), key='-BORROWERS-', enable_events=True)],
        [sg.Button('Add borrower', key='-ADD-BORR-')]
    ]

    outfits_col = [
        [sg.Text('Outfits')],
        [sg.Listbox(values=[f"{o['code']} ({o['size'] or ''})" for o in db.list_outfits(db_path) if o['code'] != '<deleted-outfit>'], size=(30, 10), key='-OUTFITS-', enable_events=True)],
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
        [sg.Listbox(values=[format_row(r) for r in db.list_overdue(db_path)], size=(60, 6), key='-OVERDUE-')]
    ]

    # layout without explicit fullscreen/exit buttons — allow window maximize via OS controls
    layout = [
        [sg.Column(borrowers_col), sg.VerticalSeparator(), sg.Column(outfits_col), sg.VerticalSeparator(), sg.Column(rentals_col)],
        [sg.HorizontalSeparator()],
        [sg.Column(overdue_col)]
    ]

    window = sg.Window('Outfit Manager', layout, finalize=True, resizable=True)
    is_fullscreen = False

    def refresh_all():
        window['-BORROWERS-'].update([b['name'] for b in db.list_borrowers(db_path) if b['name'] != '<deleted borrower>'])
        window['-OUTFITS-'].update([f"{o['code']} ({o['size'] or ''})" for o in db.list_outfits(db_path) if o['code'] != '<deleted-outfit>'])
        window['-RENTALS-'].update([format_row(r) for r in db.list_active_rentals(db_path)])
        window['-OVERDUE-'].update([format_row(r) for r in db.list_overdue(db_path)])

    # initial refresh so lists are current
    refresh_all()

    # bind double-clicks on listboxes to show details
    try:
        # borrowers
        lb = window['-BORROWERS-'].Widget
        lb.bind('<Double-Button-1>', lambda ev: window.write_event_value('-BORROWER-DBL-', window['-BORROWERS-'].get()))
        # outfits
        ob = window['-OUTFITS-'].Widget
        ob.bind('<Double-Button-1>', lambda ev: window.write_event_value('-OUTFIT-DBL-', window['-OUTFITS-'].get()))
    except Exception:
        pass

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

    # Simple date-picker modal (combos) to avoid Tk calendar positioning issues
    def pick_date_modal(title: str, default_date: datetime):
        y = default_date.year
        m = default_date.month
        d = default_date.day
        years = [str(y + i) for i in range(-5, 6)]
        months = [f"{i:02d}" for i in range(1, 13)]
        days = [f"{i:02d}" for i in range(1, 32)]
        layout = [
            [sg.Text('Year'), sg.Combo(years, default_value=str(y), key='-DP-Y-'),
             sg.Text('Month'), sg.Combo(months, default_value=f"{m:02d}", key='-DP-M-'),
             sg.Text('Day'), sg.Combo(days, default_value=f"{d:02d}", key='-DP-D-')],
            [sg.Button('OK'), sg.Button('Cancel')]
        ]
        win = sg.Window(title, layout, modal=True, location=window.current_location(), keep_on_top=True)
        while True:
            ev, vals = win.read()
            if ev in (sg.WIN_CLOSED, 'Cancel'):
                win.close()
                return None
            if ev == 'OK':
                try:
                    sel = datetime(int(vals['-DP-Y-']), int(vals['-DP-M-']), int(vals['-DP-D-']))
                    win.close()
                    return sel.strftime('%Y-%m-%d')
                except Exception:
                    sg.popup_error('Invalid date selected', location=window.current_location(), keep_on_top=True)
                    continue

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED:
            break

        if event == '-ADD-BORR-':
            # Single-form dialog to add borrower with simple validation
            form_layout = [
                [sg.Text('Name'), sg.Input(key='-NAME-')],
                [sg.Text('Phone'), sg.Input(key='-PHONE-')],
                [sg.Text('Email'), sg.Input(key='-EMAIL-')],
                [sg.Button('Save'), sg.Button('Cancel')]
            ]
            form_win = sg.Window('Add borrower', form_layout, modal=True, location=window.current_location(), keep_on_top=True)
            while True:
                fev, fvals = form_win.read()
                if fev in (sg.WIN_CLOSED, 'Cancel'):
                    form_win.close()
                    break
                if fev == 'Save':
                    name = fvals['-NAME-'].strip()
                    phone = fvals['-PHONE-'].strip()
                    email = fvals['-EMAIL-'].strip()
                    import re
                    def valid_phone(p):
                        return p == '' or re.match(r'^[+\d][0-9 \-()]{6,}$', p)
                    def valid_email(e):
                        return e == '' or re.match(r'^[^@]+@[^@]+\.[^@]+$', e)
                    if not name:
                        sg.popup_error('Name is required', location=window.current_location(), keep_on_top=True)
                        continue
                    if not valid_phone(phone):
                        sg.popup_error('Phone looks invalid', location=window.current_location(), keep_on_top=True)
                        continue
                    if not valid_email(email):
                        sg.popup_error('Email looks invalid', location=window.current_location(), keep_on_top=True)
                        continue
                    db.add_borrower(db_path, name, phone or None, email or None)
                    form_win.close()
                    refresh_all()
                    break

        # show borrower details on double-click
        if event == '-BORROWER-DBL-':
            sel = values[event]
            if sel:
                name = sel[0]
                borrower = db.get_borrower_by_name(db_path, name)
                if borrower:
                    detail_layout = [
                        [sg.Text('Name'), sg.Text(borrower['name'])],
                        [sg.Text('Phone'), sg.Text(borrower['phone'] or '')],
                        [sg.Text('Email'), sg.Text(borrower['email'] or '')],
                        [sg.Button('Close')]
                    ]
                    detail_layout = [
                        [sg.Text('Name'), sg.Text(borrower['name'])],
                        [sg.Text('Phone'), sg.Text(borrower['phone'] or '')],
                        [sg.Text('Email'), sg.Text(borrower['email'] or '')],
                        [sg.Button('Edit'), sg.Button('Delete'), sg.Button('Close')]
                    ]
                    dwin = sg.Window('Borrower details', detail_layout, modal=True, location=window.current_location(), keep_on_top=True)
                    devent, dvals = dwin.read()
                    if devent == 'Edit':
                        # open edit form pre-filled
                        edit_layout = [
                            [sg.Text('Name'), sg.Input(borrower['name'], key='-ENAME-')],
                            [sg.Text('Phone'), sg.Input(borrower['phone'] or '', key='-EPHONE-')],
                            [sg.Text('Email'), sg.Input(borrower['email'] or '', key='-EEMAIL-')],
                            [sg.Button('Save'), sg.Button('Cancel')]
                        ]
                        ewin = sg.Window('Edit borrower', edit_layout, modal=True, location=window.current_location(), keep_on_top=True)
                        while True:
                            eev, evals = ewin.read()
                            if eev in (sg.WIN_CLOSED, 'Cancel'):
                                ewin.close()
                                break
                            if eev == 'Save':
                                new_name = evals['-ENAME-'].strip()
                                new_phone = evals['-EPHONE-'].strip()
                                new_email = evals['-EEMAIL-'].strip()
                                import re
                                def valid_phone(p):
                                    return p == '' or re.match(r'^[+\d][0-9 \-()]{6,}$', p)
                                def valid_email(e):
                                    return e == '' or re.match(r'^[^@]+@[^@]+\.[^@]+$', e)
                                if not new_name:
                                    sg.popup_error('Name is required', location=window.current_location(), keep_on_top=True)
                                    continue
                                if not valid_phone(new_phone):
                                    sg.popup_error('Phone looks invalid', location=window.current_location(), keep_on_top=True)
                                    continue
                                if not valid_email(new_email):
                                    sg.popup_error('Email looks invalid', location=window.current_location(), keep_on_top=True)
                                    continue
                                db.update_borrower(db_path, borrower['id'], new_name, new_phone or None, new_email or None)
                                ewin.close()
                                dwin.close()
                                refresh_all()
                                break
                    elif devent == 'Delete':
                        confirm = sg.popup_ok_cancel('Delete this borrower? This cannot be undone if there are no rentals.', location=window.current_location(), keep_on_top=True)
                        if confirm == 'OK':
                            try:
                                db.delete_borrower(db_path, borrower['id'])
                            except Exception as e:
                                sg.popup_error('Cannot delete borrower', str(e), location=window.current_location(), keep_on_top=True)
                            else:
                                dwin.close()
                                refresh_all()
                                continue
                    dwin.close()

        if event == '-ADD-OUT-':
            form_layout = [
                [sg.Text('Code (unique)'), sg.Input(key='-CODE-')],
                [sg.Text('Description'), sg.Input(key='-DESC-')],
                [sg.Text('Size'), sg.Input(key='-SIZE-')],
                [sg.Button('Save'), sg.Button('Cancel')]
            ]
            form_win = sg.Window('Add outfit', form_layout, modal=True, location=window.current_location(), keep_on_top=True)
            while True:
                fev, fvals = form_win.read()
                if fev in (sg.WIN_CLOSED, 'Cancel'):
                    form_win.close()
                    break
                if fev == 'Save':
                    code = fvals['-CODE-'].strip()
                    desc = fvals['-DESC-'].strip()
                    size = fvals['-SIZE-'].strip()
                    if not code:
                        sg.popup_error('Code is required', location=window.current_location(), keep_on_top=True)
                        continue
                    try:
                        db.add_outfit(db_path, code, desc or None, size or None)
                    except Exception as e:
                        sg.popup_error('Error adding outfit', str(e), location=window.current_location(), keep_on_top=True)
                    else:
                        form_win.close()
                        refresh_all()
                        break

        # show outfit details on double-click
        if event == '-OUTFIT-DBL-':
            sel = values[event]
            if sel:
                item = sel[0]
                # item is like 'CODE (SIZE)'
                code = item.split()[0]
                outfit = db.get_outfit_by_code(db_path, code)
                if outfit:
                    detail_layout = [
                        [sg.Text('Code'), sg.Text(outfit['code'])],
                        [sg.Text('Description'), sg.Text(outfit['description'] or '')],
                        [sg.Text('Size'), sg.Text(outfit['size'] or '')],
                        [sg.Button('Close')]
                    ]
                    detail_layout = [
                        [sg.Text('Code'), sg.Text(outfit['code'])],
                        [sg.Text('Description'), sg.Text(outfit['description'] or '')],
                        [sg.Text('Size'), sg.Text(outfit['size'] or '')],
                        [sg.Button('Edit'), sg.Button('Delete'), sg.Button('Close')]
                    ]
                    dwin = sg.Window('Outfit details', detail_layout, modal=True, location=window.current_location(), keep_on_top=True)
                    devent, dvals = dwin.read()
                    if devent == 'Edit':
                        edit_layout = [
                            [sg.Text('Code'), sg.Input(outfit['code'], key='-ECODE-')],
                            [sg.Text('Description'), sg.Input(outfit['description'] or '', key='-EDESC-')],
                            [sg.Text('Size'), sg.Input(outfit['size'] or '', key='-ESIZE-')],
                            [sg.Button('Save'), sg.Button('Cancel')]
                        ]
                        ewin = sg.Window('Edit outfit', edit_layout, modal=True, location=window.current_location(), keep_on_top=True)
                        while True:
                            eev, evals = ewin.read()
                            if eev in (sg.WIN_CLOSED, 'Cancel'):
                                ewin.close()
                                break
                            if eev == 'Save':
                                new_code = evals['-ECODE-'].strip()
                                new_desc = evals['-EDESC-'].strip()
                                new_size = evals['-ESIZE-'].strip()
                                if not new_code:
                                    sg.popup_error('Code is required', location=window.current_location(), keep_on_top=True)
                                    continue
                                try:
                                    db.update_outfit(db_path, outfit['id'], new_code, new_desc or None, new_size or None)
                                except Exception as e:
                                    sg.popup_error('Cannot update outfit', str(e), location=window.current_location(), keep_on_top=True)
                                    continue
                                ewin.close()
                                dwin.close()
                                refresh_all()
                                break
                    elif devent == 'Delete':
                        confirm = sg.popup_ok_cancel('Delete this outfit? This cannot be undone if there are rentals.', location=window.current_location(), keep_on_top=True)
                        if confirm == 'OK':
                            try:
                                db.delete_outfit(db_path, outfit['id'])
                            except Exception as e:
                                sg.popup_error('Cannot delete outfit', str(e), location=window.current_location(), keep_on_top=True)
                            else:
                                dwin.close()
                                refresh_all()
                                continue
                    dwin.close()

        if event == '-CHECKOUT-':
            borrowers = db.list_borrowers(db_path)
            outfits = db.list_outfits(db_path)
            # filter out placeholder deleted records
            borrowers = [b for b in borrowers if b['name'] != '<deleted borrower>']
            outfits = [o for o in outfits if o['code'] != '<deleted-outfit>']
            if not borrowers or not outfits:
                popup_local('Add at least one borrower and one outfit first')
                continue
            b_names = [b['name'] for b in borrowers]
            o_codes = [o['code'] for o in outfits]
            # Checkout form: choose borrower and outfit from dropdowns and pick due date
            chk_layout = [
                [sg.Text('Borrower'), sg.Combo(b_names, key='-BCHOICE-', size=(30,1))],
                [sg.Text('Outfit'), sg.Combo(o_codes, key='-OCHOICE-', size=(30,1))],
                [sg.Text('Due date (YYYY-MM-DD)'), sg.Input((datetime.utcnow()+timedelta(days=7)).strftime('%Y-%m-%d'), key='-DUE-'), sg.Button('Pick', key='-PICK-DUE-')],
                [sg.Text('Notes (optional)')],
                [sg.Multiline(key='-NOTES-', size=(40,5))],
                [sg.Button('Checkout'), sg.Button('Cancel')]
            ]
            chk_win = sg.Window('Checkout', chk_layout, modal=True, location=window.current_location(), keep_on_top=True)
            while True:
                cev, cvals = chk_win.read()
                if cev in (sg.WIN_CLOSED, 'Cancel'):
                    chk_win.close()
                    break
                if cev == '-PICK-DUE-':
                    picked = pick_date_modal('Pick due date', datetime.utcnow()+timedelta(days=7))
                    if picked:
                        chk_win['-DUE-'].update(picked)
                    continue
                if cev == 'Checkout':
                    b_choice = cvals['-BCHOICE-']
                    o_choice = cvals['-OCHOICE-']
                    due_str = cvals['-DUE-']
                    notes = cvals['-NOTES-'].strip()
                    if not b_choice or not o_choice:
                        sg.popup_error('Select borrower and outfit', location=window.current_location(), keep_on_top=True)
                        continue
                    try:
                        # normalize due to ISO datetime
                        due_iso = datetime.fromisoformat(due_str).isoformat()
                    except Exception:
                        sg.popup_error('Invalid due date format', location=window.current_location(), keep_on_top=True)
                        continue
                    borrower = db.get_borrower_by_name(db_path, b_choice)
                    outfit = db.get_outfit_by_code(db_path, o_choice)
                    if not borrower or not outfit:
                        sg.popup_error('Borrower or outfit not found', location=window.current_location(), keep_on_top=True)
                        continue
                    db.checkout(db_path, borrower['id'], outfit['id'], due_iso, notes or None)
                    chk_win.close()
                    refresh_all()
                    break

        if event == '-RETURN-':
            sel = values['-RENTALS-']
            if not sel:
                popup_local('Select an active rental from the list to return')
                continue
            # listbox item formatted as: id | borrower | outfit_code | due YYYY-MM-DD
            item = sel[0]
            rental_id = int(item.split('|')[0].strip())
            # ask returned date via calendar
            ret_layout = [
                [sg.Text('Returned date (YYYY-MM-DD)'), sg.Input(datetime.utcnow().strftime('%Y-%m-%d'), key='-RET-'), sg.Button('Pick', key='-PICK-RET-')],
                [sg.Button('Confirm Return'), sg.Button('Cancel')]
            ]
            ret_win = sg.Window('Return rental', ret_layout, modal=True, location=window.current_location(), keep_on_top=True)
            while True:
                rev, rvals = ret_win.read()
                if rev in (sg.WIN_CLOSED, 'Cancel'):
                    ret_win.close()
                    break
                if rev == '-PICK-RET-':
                    picked = pick_date_modal('Pick return date', datetime.utcnow())
                    if picked:
                        ret_win['-RET-'].update(picked)
                    continue
                if rev == 'Confirm Return':
                    ret_str = rvals['-RET-']
                    try:
                        ret_iso = datetime.fromisoformat(ret_str).isoformat()
                    except Exception:
                        sg.popup_error('Invalid date', location=window.current_location(), keep_on_top=True)
                        continue
                    db.return_rental(db_path, rental_id, ret_iso)
                    ret_win.close()
                    refresh_all()
                    break

    window.close()
