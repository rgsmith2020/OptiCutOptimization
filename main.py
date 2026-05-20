# ================================================================================
#
#   .___  _________  ___________  __________  ___________   _____   __________
#   |   | \_   ___ \ \_   _____/  \______   \ \_   _____/  /  _  \  \______   \
#   |   | /    \  \/  |    __)_    |    __  /  |    __)_  /  /_\  \  |       _/
#   |   | \     \____ |        \   |    |   \  |        \/    |    \ |    |   \
#   |___|  \______  //_______  /   |____|_  / /_______  /\____|__  / |____|_  /
#                 \/         \/           \/          \/         \/         \/
#                                                                             2026
#
# ================================================================================

import csv
import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

_HERE = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent

MODELS = {
    'Model A': {'fractional_openings': 1,     'doors_per_frame': 1},
    'Model Z': {'fractional_openings': 1/2,   'doors_per_frame': 2},
    'Model B': {'fractional_openings': 1/2,   'doors_per_frame': 2},
    'Model C': {'fractional_openings': 1/3,   'doors_per_frame': 3},
    'Model D': {'fractional_openings': 1/4,   'doors_per_frame': 4},
    'Model E': {'fractional_openings': 1/5,   'doors_per_frame': 5},
    'Model F': {'fractional_openings': 1/6,   'doors_per_frame': 6},
    'Custom':  None,
}

STOCK_SIZES = {
    '4x8  (48" × 96")':   (48,  96),
    '5x8  (60" × 96")':   (60,  96),
    '4x10 (48" × 120")':  (48, 120),
    '5x10 (60" × 120")':  (60, 120),
    '4x12 (48" × 144")':  (48, 144),
    '5x12 (60" × 144")':  (60, 144),
    'Custom':              None,
}

PALETTE = [
    ('#4a90d9', '#1a5fa8'),
    ('#50b86c', '#207a40'),
    ('#e07b54', '#a04020'),
    ('#9b59b6', '#5c3080'),
    ('#16a085', '#0a6655'),
    ('#e74c3c', '#922b21'),
    ('#f39c12', '#b07d09'),
    ('#2980b9', '#1a5276'),
]

_CSV_MODELS = {
    'A': 'Model A', 'B': 'Model B', 'C': 'Model C', 'D': 'Model D',
    'E': 'Model E', 'F': 'Model F', 'Z': 'Model Z', 'CUSTOM': 'Custom',
}

CANVAS_W = 340
CANVAS_H = 500
MARGIN   = 24
KERF_DEF = 0.0

C_DARK_BLUE = '#1F4E79'
C_MED_BLUE  = '#2E75B6'
C_LITE_BLUE = '#D6E4F0'
C_ROW_ALT   = '#e8f0f8'
C_GREEN     = '#1a7a1a'
C_AMBER     = '#996600'
C_RED       = '#C00000'
C_WHITE     = '#ffffff'


# ── pack engine ───────────────────────────────────────────────────────────────

def _choose_orientation(dw, dh, sw, sl, kerf, grain_match=False, grain_direction='vertical'):
    """Return (w, h, rotated) for the orientation that packs the most items/sheet.

    When grain_match is True the orientation is forced to preserve grain alignment:
      vertical   – grain runs along piece height (door_h stays on Y-axis, rotated=False)
      horizontal – grain runs along piece width  (piece rotated 90°, rotated=True)
    """
    if grain_match:
        if grain_direction == 'horizontal':
            return dh, dw, True
        return dw, dh, False
    def capacity(w, h):
        if w > sw or h > sl:
            return 0
        a = int((sw + kerf) / (w + kerf)) if kerf > 0 else int(sw / w)
        d = int((sl + kerf) / (h + kerf)) if kerf > 0 else int(sl / h)
        return a * d
    if capacity(dh, dw) > capacity(dw, dh):
        return dh, dw, True
    return dw, dh, False


def _pack(pieces, sw, sl, kerf, grain_match=False, grain_direction='vertical'):
    items = []
    for p in pieces:
        w, h, rot = _choose_orientation(p['door_w'], p['door_h'], sw, sl, kerf,
                                        grain_match, grain_direction)
        for _ in range(int(p['qty'])):
            items.append({'w': w, 'h': h,
                          'fill': p['fill'], 'outline': p['outline'],
                          'name': p['name'], 'rotated': rot})
    items.sort(key=lambda x: (x['h'], x['w']), reverse=True)

    sheets = []
    while items:
        placed = set()
        sheet  = []
        y      = 0.0
        while True:
            leader = next(
                (i for i, it in enumerate(items)
                 if i not in placed and y + it['h'] <= sl + 1e-9), None)
            if leader is None:
                break
            row_h = items[leader]['h']
            x = 0.0
            for i, it in enumerate(items):
                if i in placed or abs(it['h'] - row_h) > 1e-9:
                    continue
                xs = x + (kerf if x > 0 else 0)
                if xs + it['w'] <= sw + 1e-9:
                    sheet.append({**it, 'x': xs, 'y': y})
                    x = xs + it['w']
                    placed.add(i)
            y += row_h + kerf
        if not sheet:
            break
        items = [it for i, it in enumerate(items) if i not in placed]
        sheets.append(sheet)
    return sheets


def calculate_multi(pieces, sw, sl, kerf, grain_match=False, grain_direction='vertical'):
    if not pieces:
        raise ValueError('Add at least one piece type before calculating.')
    for p in pieces:
        if p['door_w'] <= 0 or p['door_h'] <= 0:
            raise ValueError(f'"{p["name"]}" has invalid dimensions.')
        if p['qty'] <= 0:
            raise ValueError(f'"{p["name"]}" quantity must be > 0.')
        if grain_match:
            if grain_direction == 'horizontal':
                fits = p['door_h'] <= sw and p['door_w'] <= sl
            else:
                fits = p['door_w'] <= sw and p['door_h'] <= sl
            if not fits:
                orient = grain_direction.capitalize()
                raise ValueError(
                    f'"{p["name"]}" ({p["door_w"]:.3f}" × {p["door_h"]:.3f}") '
                    f'cannot fit on the stock sheet ({sw}" × {sl}") with '
                    f'{orient} grain matching. Disable grain matching or use a larger stock sheet.')
        else:
            fits_orig = p['door_w'] <= sw and p['door_h'] <= sl
            fits_rot  = p['door_h'] <= sw and p['door_w'] <= sl
            if not fits_orig and not fits_rot:
                raise ValueError(
                    f'"{p["name"]}" ({p["door_w"]:.3f}" × {p["door_h"]:.3f}") '
                    f'cannot fit on the stock sheet ({sw}" × {sl}") in any orientation.')

    sheets     = _pack(pieces, sw, sl, kerf, grain_match, grain_direction)
    n_sheets   = len(sheets)
    area_stock = sw * sl
    sqf_stock  = area_stock / 144
    total_qty  = sum(p['qty'] for p in pieces)
    total_area = sum(p['qty'] * p['door_w'] * p['door_h'] for p in pieces)
    total_sqf  = total_area / 144

    placed = sum(len(s) for s in sheets)
    if placed < total_qty:
        raise ValueError(f'Only {placed} of {total_qty} pieces could be packed. '
                         'Check that all piece dimensions fit within the stock sheet.')

    util_overall = total_area / (n_sheets * area_stock) if n_sheets else 0.0
    waste_pct    = 1.0 - util_overall
    scrap_sqf    = max(0.0, (n_sheets * area_stock - total_area) / 144)

    return {
        'sheets':          sheets,
        'total_sheets':    n_sheets,
        'total_qty':       total_qty,
        'total_sqf':       total_sqf,
        'sqf_stock':       sqf_stock,
        'utilization':     util_overall,
        'waste_pct':       waste_pct,
        'scrap_sqf':       scrap_sqf,
        'stock_width':     sw,
        'stock_length':    sl,
        'kerf':            kerf,
        'grain_match':     grain_match,
        'grain_direction': grain_direction,
    }


# ── application ───────────────────────────────────────────────────────────────

class OptiCutApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title('OptiCut')
        self.resizable(False, False)
        self.iconbitmap(str(_HERE / 'saw-blade.ico'))
        self._result      = None
        self._sheet_index = 0
        self._pieces      = []
        self._build_ui()

    # ── menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        menubar   = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='File', menu=file_menu)
        file_menu.add_command(label='Open...', accelerator='Ctrl+O', command=self._open)
        file_menu.add_command(label='Save...', accelerator='Ctrl+S',
                              command=self._save, state='disabled')
        file_menu.add_separator()
        file_menu.add_command(label='About', command=self._show_about)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', accelerator='Alt+F4', command=self.destroy)
        self._file_menu = file_menu

        import_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Import', menu=import_menu)
        import_menu.add_command(label='Import from CSV...', command=self._import_csv)
        import_menu.add_command(label='Download Template', command=self._download_template)

        self.bind_all('<Control-o>', lambda _: self._open())
        self.bind_all('<Control-s>', lambda _: self._save())

    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('OptiCut config', '*.json'), ('All files', '*.*')],
            title='Save Configuration',
        )
        if not path:
            return
        data = {
            'stock_size':      self.stock_size_var.get(),
            'stock_width':     self.stock_w_var.get(),
            'stock_length':    self.stock_l_var.get(),
            'kerf':            self.kerf_var.get(),
            'grain_match':     self.grain_match_var.get(),
            'grain_direction': self.grain_dir_var.get(),
            'pieces': [
                {'name': p['name'], 'door_w': p['door_w'],
                 'door_h': p['door_h'], 'qty': p['qty']}
                for p in self._pieces
            ],
        }
        if self._result:
            r = self._result
            data['output'] = {
                'total_sheets': r['total_sheets'],
                'total_qty':    r['total_qty'],
                'total_sqf':    round(r['total_sqf'],   4),
                'utilization':  round(r['utilization'], 6),
                'waste_pct':    round(r['waste_pct'],   6),
                'scrap_sqf':    round(r['scrap_sqf'],   4),
            }
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            messagebox.showerror('Save Error', str(e))

    def _open(self):
        path = filedialog.askopenfilename(
            filetypes=[('OptiCut config', '*.json'), ('All files', '*.*')],
            title='Open Configuration',
        )
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            messagebox.showerror('Invalid File',
                'This file could not be read.\n\nPlease open an OptiCut file only (.json).')
            return
        if not isinstance(data, dict) or 'pieces' not in data or 'stock_width' not in data:
            messagebox.showerror('Invalid File',
                'This does not appear to be an OptiCut file.\n\nPlease open an OptiCut file only (.json).')
            return
        try:
            self.stock_size_var.set(data.get('stock_size', 'Custom'))
            self.stock_w_var.set(float(data['stock_width']))
            self.stock_l_var.set(float(data['stock_length']))
            self.kerf_var.set(float(data.get('kerf', KERF_DEF)))
            self.grain_match_var.set(bool(data.get('grain_match', False)))
            self.grain_dir_var.set(data.get('grain_direction', 'vertical'))
            self._pieces = []
            for i, p in enumerate(data['pieces']):
                fill, outline = PALETTE[i % len(PALETTE)]
                self._pieces.append({
                    'name':    p['name'],
                    'door_w':  float(p['door_w']),
                    'door_h':  float(p['door_h']),
                    'qty':     int(p['qty']),
                    'fill':    fill,
                    'outline': outline,
                })
            self._refresh_pieces_table()
            self.on_calculate()
        except Exception as e:
            messagebox.showerror('Open Error', str(e))

    def _show_about(self):
        win = tk.Toplevel(self)
        win.title('About OptiCut')
        win.resizable(False, False)
        win.grab_set()
        ttk.Label(win, text='OptiCut', font=('Segoe UI', 16, 'bold')).pack(pady=(20, 4))
        ttk.Label(win, text='Version 3.0.0').pack()
        ttk.Label(win, text='Locker door nesting calculator.').pack(pady=(8, 0))
        ttk.Label(win, text='Optimized for Hollman Inc. Lockers').pack(pady=(8, 0))
        ttk.Label(win, text='© 2026 - Northern Lights Studios').pack(pady=(4, 8))
        img_scale = -16
        img = tk.PhotoImage(file=str(_HERE / 'NorthernLights SM.png'))
        if img_scale > 1:
            img = img.zoom(img_scale)
        elif img_scale < -1:
            img = img.subsample(-img_scale)
        lbl = ttk.Label(win, image=img)
        lbl.image = img
        lbl.pack(pady=(0, 12))
        ttk.Button(win, text='OK', command=win.destroy).pack(pady=(0, 16))

    # ── CSV import ────────────────────────────────────────────────────────────

    def _import_csv(self):
        path = filedialog.askopenfilename(
            filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
            title='Import from CSV',
        )
        if not path:
            return

        errors   = []
        imported = []
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                lines = [ln for ln in f if not ln.lstrip().startswith('#')]
            reader = csv.DictReader(lines)
            if not reader.fieldnames:
                messagebox.showerror('Import Error', 'CSV file is empty.')
                return
            norm_headers = {k.strip().lower() for k in reader.fieldnames if k}
            required = {'label', 'model', 'width', 'height', 'qty'}
            missing  = required - norm_headers
            if missing:
                messagebox.showerror('Import Error',
                    f'Missing column(s): {", ".join(sorted(missing))}\n\n'
                    'Use Import → Download Template for the correct format.')
                return
            for row_num, row in enumerate(reader, start=2):
                r = {k.strip().lower(): (v or '').strip()
                     for k, v in row.items() if k}
                model_code = r.get('model', '').upper()
                if model_code not in _CSV_MODELS:
                    errors.append(
                        f'Row {row_num}: invalid Model "{r.get("model","")}"'
                        f' — accepted values: A B C D E F Z CUSTOM')
                    continue
                try:
                    width  = float(r['width'])
                    height = float(r['height'])
                    qty    = int(float(r['qty']))
                except ValueError:
                    errors.append(
                        f'Row {row_num}: Width, Height, Qty must be numeric.')
                    continue
                if width <= 0 or height <= 0:
                    errors.append(
                        f'Row {row_num}: Width and Height must be > 0.')
                    continue
                if qty <= 0:
                    errors.append(f'Row {row_num}: Qty must be > 0.')
                    continue
                label     = r.get('label', '').strip()
                model_key = _CSV_MODELS[model_code]
                if model_key == 'Custom':
                    door_w, door_h = width, height
                    auto_name = f'Custom {door_w:.2f}×{door_h:.2f}'
                else:
                    frac      = MODELS[model_key]['fractional_openings']
                    door_w    = width
                    door_h    = height * frac
                    auto_name = f'{model_key} {width:.2f}×{height:.2f}'
                imported.append({
                    'name':   label if label else auto_name,
                    'door_w': door_w,
                    'door_h': door_h,
                    'qty':    qty,
                })
        except Exception as e:
            messagebox.showerror('Import Error', f'Could not read file:\n{e}')
            return

        if errors:
            err_msg = '\n'.join(errors)
            if imported:
                if not messagebox.askyesno('Import Warnings',
                        f'{len(errors)} row(s) skipped due to errors:\n\n'
                        f'{err_msg}\n\nImport {len(imported)} valid row(s)?'):
                    return
            else:
                messagebox.showerror('Import Error',
                    f'No valid rows found:\n\n{err_msg}')
                return

        if not imported:
            messagebox.showinfo('Import', 'No pieces found in the CSV file.')
            return

        for p in imported:
            idx = len(self._pieces)
            p['fill'], p['outline'] = PALETTE[idx % len(PALETTE)]
            self._pieces.append(p)

        self._refresh_pieces_table()
        messagebox.showinfo('Import Complete',
            f'{len(imported)} piece type(s) imported successfully.')

    def _download_template(self):
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
            initialfile='OptiCut_template.csv',
            title='Save CSV Template',
        )
        if not path:
            return
        data_rows = [
            ['Label',        'Model', 'Width', 'Height', 'Qty'],
            ['Main Doors',   'A',     '9',     '96',     '100'],
            ['Half Doors',   'Z',     '9',     '96',     '50'],
            ['Custom Panel', 'CUSTOM','12',    '48',     '20'],
        ]
        notes = [
            '# ─────────────────────────────────────────────────────────────────',
            '# Model codes : A  B  C  D  E  F  Z  →  Width/Height = Locker dims',
            '#               CUSTOM               →  Width/Height = Door cut dims',
            '# Label is optional — leave blank to auto-generate name',
        ]
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                csv.writer(f).writerows(data_rows)
                for note in notes:
                    f.write(note + '\n')
            messagebox.showinfo('Template Saved', f'Template saved to:\n{path}')
        except Exception as e:
            messagebox.showerror('Save Error', str(e))

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_menu()
        pad = {'padx': 8, 'pady': 4}

        # ── Left panel ────────────────────────────────────────────────────────
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky='nsew', padx=(8, 4), pady=8)

        self._section_header(left, 'CONFIGURATION', C_DARK_BLUE, row=0)

        cfg = tk.Frame(left, bg=C_LITE_BLUE, bd=1, relief='flat')
        cfg.grid(row=1, column=0, sticky='ew')

        # Stock Sheet
        stk = ttk.LabelFrame(cfg, text='Stock Sheet')
        stk.grid(row=0, column=0, sticky='n', **pad)

        ttk.Label(stk, text='Stock Size').grid(row=0, column=0, sticky='w', **pad)
        self.stock_size_var = tk.StringVar(value='5x8  (60" × 96")')
        self.stock_cb = ttk.Combobox(stk, textvariable=self.stock_size_var,
                                     values=list(STOCK_SIZES.keys()),
                                     state='readonly', width=18)
        self.stock_cb.grid(row=0, column=1, **pad)

        ttk.Label(stk, text='Width (in)').grid(row=1, column=0, sticky='w', **pad)
        self.stock_w_var = tk.DoubleVar(value=60.0)
        self.stock_w_entry = ttk.Entry(stk, textvariable=self.stock_w_var, width=13)
        self.stock_w_entry.grid(row=1, column=1, **pad)

        ttk.Label(stk, text='Length (in)').grid(row=2, column=0, sticky='w', **pad)
        self.stock_l_var = tk.DoubleVar(value=96.0)
        self.stock_l_entry = ttk.Entry(stk, textvariable=self.stock_l_var, width=13)
        self.stock_l_entry.grid(row=2, column=1, **pad)

        ttk.Separator(stk, orient='horizontal').grid(
            row=3, column=0, columnspan=2, sticky='ew', padx=6, pady=2)

        ttk.Label(stk, text='Kerf / Blade (in)').grid(row=4, column=0, sticky='w', **pad)
        self.kerf_var = tk.DoubleVar(value=KERF_DEF)
        ttk.Entry(stk, textvariable=self.kerf_var, width=13).grid(row=4, column=1, **pad)

        ttk.Separator(stk, orient='horizontal').grid(
            row=5, column=0, columnspan=2, sticky='ew', padx=6, pady=2)

        self.grain_match_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(stk, text='Grain Match', variable=self.grain_match_var).grid(
            row=6, column=0, columnspan=2, sticky='w', padx=8, pady=(2, 0))

        self._grain_dir_frame = ttk.Frame(stk)
        self._grain_dir_frame.grid(row=7, column=0, columnspan=2, sticky='w', padx=16, pady=(0, 4))
        self.grain_dir_var = tk.StringVar(value='vertical')
        ttk.Radiobutton(self._grain_dir_frame, text='Vertical',
                        variable=self.grain_dir_var, value='vertical').pack(side='left', padx=(0, 6))
        ttk.Radiobutton(self._grain_dir_frame, text='Horizontal',
                        variable=self.grain_dir_var, value='horizontal').pack(side='left')
        self._grain_dir_frame.grid_remove()

        # Add Piece
        ap = ttk.LabelFrame(cfg, text='Add Piece')
        ap.grid(row=0, column=1, sticky='n', **pad)

        ttk.Label(ap, text='Model').grid(row=0, column=0, sticky='w', **pad)
        self.ap_model_var = tk.StringVar(value='Model A')
        self.ap_model_cb = ttk.Combobox(ap, textvariable=self.ap_model_var,
                                        values=list(MODELS.keys()),
                                        state='readonly', width=13)
        self.ap_model_cb.grid(row=0, column=1, **pad)

        # Standard-model rows (Locker W/H + computed Door W/H)
        self.ap_lbl_lw = ttk.Label(ap, text='Locker W (in)')
        self.ap_lbl_lw.grid(row=1, column=0, sticky='w', **pad)
        self.ap_lw_var = tk.DoubleVar(value=9.0)
        self.ap_lw_entry = ttk.Entry(ap, textvariable=self.ap_lw_var, width=13)
        self.ap_lw_entry.grid(row=1, column=1, **pad)

        self.ap_lbl_lh = ttk.Label(ap, text='Locker H (in)')
        self.ap_lbl_lh.grid(row=2, column=0, sticky='w', **pad)
        self.ap_lh_var = tk.DoubleVar(value=96.0)
        self.ap_lh_entry = ttk.Entry(ap, textvariable=self.ap_lh_var, width=13)
        self.ap_lh_entry.grid(row=2, column=1, **pad)

        self.ap_lbl_dw = ttk.Label(ap, text='Door Cut W', foreground='#555')
        self.ap_lbl_dw.grid(row=3, column=0, sticky='w', **pad)
        self.ap_dw_var = tk.StringVar(value='9.0000')
        self.ap_dw_lbl = ttk.Label(ap, textvariable=self.ap_dw_var, width=13,
                                   relief='sunken', anchor='e')
        self.ap_dw_lbl.grid(row=3, column=1, **pad)

        self.ap_lbl_dh = ttk.Label(ap, text='Door Cut H', foreground='#555')
        self.ap_lbl_dh.grid(row=4, column=0, sticky='w', **pad)
        self.ap_dh_var = tk.StringVar(value='96.0000')
        self.ap_dh_lbl = ttk.Label(ap, textvariable=self.ap_dh_var, width=13,
                                   relief='sunken', anchor='e')
        self.ap_dh_lbl.grid(row=4, column=1, **pad)

        # Custom-model rows (Direct Door W/H — not gridded initially)
        self.ap_lbl_cdw = ttk.Label(ap, text='Door W (in)')
        self.ap_cdw_var = tk.DoubleVar(value=9.0)
        self.ap_cdw_entry = ttk.Entry(ap, textvariable=self.ap_cdw_var, width=13)

        self.ap_lbl_cdh = ttk.Label(ap, text='Door H (in)')
        self.ap_cdh_var = tk.DoubleVar(value=48.0)
        self.ap_cdh_entry = ttk.Entry(ap, textvariable=self.ap_cdh_var, width=13)

        ttk.Label(ap, text='Qty').grid(row=5, column=0, sticky='w', **pad)
        self.ap_qty_var = tk.IntVar(value=100)
        ttk.Entry(ap, textvariable=self.ap_qty_var, width=13).grid(row=5, column=1, **pad)

        ttk.Label(ap, text='Label').grid(row=6, column=0, sticky='w', **pad)
        self.ap_label_var = tk.StringVar(value='')
        ttk.Entry(ap, textvariable=self.ap_label_var, width=13).grid(row=6, column=1, **pad)

        ttk.Button(ap, text='Add Piece', command=self._add_piece).grid(
            row=7, column=0, columnspan=2, pady=(4, 6))

        # PIECES TO CUT
        tk.Frame(left, height=4).grid(row=2)
        self._section_header(left, 'PIECES TO CUT', C_MED_BLUE, row=3)

        pieces_frame = tk.Frame(left)
        pieces_frame.grid(row=4, column=0, sticky='ew')

        style = ttk.Style()
        style.configure('OptiCut.Treeview.Heading',
                        background=C_LITE_BLUE, font=('Segoe UI', 9, 'bold'))
        style.configure('OptiCut.Treeview', font=('Segoe UI', 9), rowheight=22)

        pcols = ('name', 'dw', 'dh', 'qty')
        self.pieces_tree = ttk.Treeview(pieces_frame, columns=pcols, show='headings',
                                        height=4, style='OptiCut.Treeview')
        phdrs = [('name', 'Name', 130), ('dw', 'Door W"', 65),
                 ('dh', 'Door H"', 65), ('qty', 'Qty', 48)]
        for col, hdr, w in phdrs:
            self.pieces_tree.heading(col, text=hdr)
            self.pieces_tree.column(col, width=w, anchor='center', stretch=False)
        pvsb = ttk.Scrollbar(pieces_frame, orient='vertical', command=self.pieces_tree.yview)
        self.pieces_tree.configure(yscrollcommand=pvsb.set)
        self.pieces_tree.grid(row=0, column=0, sticky='nsew')
        pvsb.grid(row=0, column=1, sticky='ns')

        btn_row = tk.Frame(left)
        btn_row.grid(row=5, column=0, sticky='w', pady=(2, 4))
        ttk.Button(btn_row, text='Remove Selected',
                   command=self._remove_piece).pack(side='left', padx=8)
        ttk.Button(btn_row, text='Clear All',
                   command=self._clear_pieces).pack(side='left', padx=4)

        # Calculate
        tk.Frame(left, height=4).grid(row=6)
        ttk.Button(left, text='     Calculate     ',
                   command=self.on_calculate).grid(row=7, column=0, pady=6)

        # ── Middle panel ──────────────────────────────────────────────────────
        mid = ttk.Frame(self)
        mid.grid(row=0, column=1, sticky='nsew', padx=(4, 4), pady=8)

        # RESULTS SUMMARY
        self._section_header(mid, 'RESULTS SUMMARY', C_MED_BLUE, row=0)

        res = tk.Frame(mid, bg=C_LITE_BLUE)
        res.grid(row=1, column=0, sticky='ew')
        res.grid_columnconfigure(0, weight=1)

        result_rows = [
            ('Total Sheets Needed',  'total_sheets', '',     None),
            ('Total Pieces',         'total_qty',    '',     None),
            ('Total Piece Area',     'total_sqf',    ' SQF', None),
            ('Stock Sheet Area',     'sqf_stock',    ' SQF', None),
            ('Material Utilization', 'utilization',  '',     'util'),
            ('Waste',                'waste_pct',    '',     'waste'),
            ('Drop / Scrap',         'scrap_sqf',    ' SQF', None),
        ]
        self.result_vars  = {}
        self.result_units = {}
        self._color_lbls  = {}

        for i, (label, key, unit, tag) in enumerate(result_rows):
            bg = C_LITE_BLUE if i % 2 == 0 else C_ROW_ALT
            tk.Label(res, text=label, bg=bg, anchor='w',
                     font=('Segoe UI', 9)).grid(row=i, column=0, sticky='ew', padx=(8, 4), pady=2)
            var = tk.StringVar(value='—')
            lbl = tk.Label(res, textvariable=var, bg=bg, width=20, anchor='e',
                           font=('Segoe UI', 9, 'bold'))
            lbl.grid(row=i, column=1, sticky='e', padx=(4, 8), pady=2)
            self.result_vars[key]  = var
            self.result_units[key] = unit
            if tag:
                self._color_lbls[tag] = lbl

        # PER-SHEET BREAKDOWN
        tk.Frame(mid, height=4).grid(row=2)
        self._section_header(mid, 'PER-SHEET BREAKDOWN', C_MED_BLUE, row=3)

        tree_frame = tk.Frame(mid)
        tree_frame.grid(row=4, column=0, sticky='ew')

        cols = ('sheet', 'pieces', 'used_sqf', 'utilization', 'status')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings',
                                 height=5, style='OptiCut.Treeview')
        hdrs = [('sheet', 'Sheet #', 56), ('pieces', 'Pieces', 56),
                ('used_sqf', 'Used SQF', 80), ('utilization', 'Utilization', 80),
                ('status', 'Status', 90)]
        for col, hdr, w in hdrs:
            self.tree.heading(col, text=hdr)
            self.tree.column(col, width=w, anchor='center', stretch=False)
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        self.tree.tag_configure('full',    foreground=C_GREEN)
        self.tree.tag_configure('partial', foreground=C_AMBER)

        # ── Right panel ───────────────────────────────────────────────────────
        right = ttk.Frame(self)
        right.grid(row=0, column=2, sticky='nsew', padx=(4, 8), pady=8)

        self._section_header(right, 'NESTING LAYOUT', C_DARK_BLUE, row=0)

        self.canvas = tk.Canvas(right, width=CANVAS_W, height=CANVAS_H,
                                bg='#f5f5f5', relief='sunken', bd=1)
        self.canvas.grid(row=1, column=0, padx=4, pady=(4, 2))

        nav = ttk.Frame(right)
        nav.grid(row=2, column=0, pady=(2, 4))

        self.btn_prev = ttk.Button(nav, text='◀', width=3, command=self._prev_sheet)
        self.btn_prev.grid(row=0, column=0, padx=4)

        self.sheet_label_var = tk.StringVar(value='—')
        ttk.Label(nav, textvariable=self.sheet_label_var, width=18,
                  anchor='center').grid(row=0, column=1, padx=4)

        self.btn_next = ttk.Button(nav, text='▶', width=3, command=self._next_sheet)
        self.btn_next.grid(row=0, column=2, padx=4)

        self.legend_frame = tk.Frame(right)
        self.legend_frame.grid(row=3, column=0, pady=(0, 4))
        self._build_default_legend()

        self._draw_placeholder()

        # Traces
        self.ap_model_var.trace_add('write', lambda *_: self._on_ap_model_change())
        self.stock_size_var.trace_add('write', lambda *_: self._on_stock_size_change())
        self.ap_lw_var.trace_add('write', lambda *_: self._update_door_preview())
        self.ap_lh_var.trace_add('write', lambda *_: self._update_door_preview())
        self.grain_match_var.trace_add('write', lambda *_: self._on_grain_match_change())
        self._on_stock_size_change()
        self._update_door_preview()

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _section_header(parent, text, color, row):
        f = tk.Frame(parent, bg=color)
        f.grid(row=row, column=0, sticky='ew')
        tk.Label(f, text=f'  {text}', bg=color, fg=C_WHITE,
                 font=('Segoe UI', 10, 'bold')).pack(side='left', pady=5)

    def _on_stock_size_change(self):
        dims = STOCK_SIZES.get(self.stock_size_var.get())
        if dims is None:
            self.stock_w_entry.config(state='normal')
            self.stock_l_entry.config(state='normal')
        else:
            self.stock_w_var.set(dims[0])
            self.stock_l_var.set(dims[1])
            self.stock_w_entry.config(state='disabled')
            self.stock_l_entry.config(state='disabled')

    def _on_grain_match_change(self):
        if self.grain_match_var.get():
            self._grain_dir_frame.grid()
        else:
            self._grain_dir_frame.grid_remove()

    def _on_ap_model_change(self):
        is_custom = self.ap_model_var.get() == 'Custom'
        pad = {'padx': 8, 'pady': 4}
        if is_custom:
            self.ap_lbl_lw.grid_remove()
            self.ap_lw_entry.grid_remove()
            self.ap_lbl_lh.grid_remove()
            self.ap_lh_entry.grid_remove()
            self.ap_lbl_dw.grid_remove()
            self.ap_dw_lbl.grid_remove()
            self.ap_lbl_dh.grid_remove()
            self.ap_dh_lbl.grid_remove()
            self.ap_lbl_cdw.grid(row=1, column=0, sticky='w', **pad)
            self.ap_cdw_entry.grid(row=1, column=1, **pad)
            self.ap_lbl_cdh.grid(row=2, column=0, sticky='w', **pad)
            self.ap_cdh_entry.grid(row=2, column=1, **pad)
        else:
            self.ap_lbl_cdw.grid_remove()
            self.ap_cdw_entry.grid_remove()
            self.ap_lbl_cdh.grid_remove()
            self.ap_cdh_entry.grid_remove()
            self.ap_lbl_lw.grid(row=1, column=0, sticky='w', **pad)
            self.ap_lw_entry.grid(row=1, column=1, **pad)
            self.ap_lbl_lh.grid(row=2, column=0, sticky='w', **pad)
            self.ap_lh_entry.grid(row=2, column=1, **pad)
            self.ap_lbl_dw.grid(row=3, column=0, sticky='w', **pad)
            self.ap_dw_lbl.grid(row=3, column=1, **pad)
            self.ap_lbl_dh.grid(row=4, column=0, sticky='w', **pad)
            self.ap_dh_lbl.grid(row=4, column=1, **pad)
            self._update_door_preview()

    def _update_door_preview(self):
        model = self.ap_model_var.get()
        if model == 'Custom' or model not in MODELS or MODELS[model] is None:
            return
        try:
            frac = MODELS[model]['fractional_openings']
            self.ap_dw_var.set(f'{self.ap_lw_var.get():.4f}')
            self.ap_dh_var.set(f'{self.ap_lh_var.get() * frac:.4f}')
        except Exception:
            pass

    # ── pieces management ─────────────────────────────────────────────────────

    def _add_piece(self):
        model = self.ap_model_var.get()
        try:
            qty = int(self.ap_qty_var.get())
            if qty <= 0:
                raise ValueError('Qty must be > 0')
            if model == 'Custom':
                dw       = float(self.ap_cdw_var.get())
                dh       = float(self.ap_cdh_var.get())
                auto_name = f'Custom {dw:.2f}×{dh:.2f}'
            else:
                lw       = self.ap_lw_var.get()
                lh       = self.ap_lh_var.get()
                frac     = MODELS[model]['fractional_openings']
                dw       = lw
                dh       = lh * frac
                auto_name = f'{model} {lw:.2f}×{lh:.2f}'
            if dw <= 0 or dh <= 0:
                raise ValueError('Door dimensions must be > 0')
        except ValueError as e:
            messagebox.showerror('Input Error', str(e))
            return

        label = self.ap_label_var.get().strip()
        name  = label if label else auto_name

        idx = len(self._pieces)
        fill, outline = PALETTE[idx % len(PALETTE)]
        self._pieces.append({
            'name': name, 'door_w': dw, 'door_h': dh,
            'qty': qty, 'fill': fill, 'outline': outline,
        })
        self.ap_label_var.set('')
        self._refresh_pieces_table()

    def _remove_piece(self):
        sel = self.pieces_tree.selection()
        if not sel:
            return
        self._pieces.pop(int(sel[0]))
        for i, p in enumerate(self._pieces):
            p['fill'], p['outline'] = PALETTE[i % len(PALETTE)]
        self._refresh_pieces_table()

    def _clear_pieces(self):
        if self._pieces and messagebox.askyesno('Clear All', 'Remove all pieces?'):
            self._pieces.clear()
            self._refresh_pieces_table()

    def _refresh_pieces_table(self):
        self.pieces_tree.delete(*self.pieces_tree.get_children())
        for i, p in enumerate(self._pieces):
            tag = f'pc{i}'
            self.pieces_tree.tag_configure(tag, foreground=p['outline'])
            self.pieces_tree.insert('', 'end', iid=str(i),
                                    values=(p['name'], f'{p["door_w"]:.3f}',
                                            f'{p["door_h"]:.3f}', p['qty']),
                                    tags=(tag,))

    # ── legend ────────────────────────────────────────────────────────────────

    def _build_default_legend(self):
        for w in self.legend_frame.winfo_children():
            w.destroy()
        for color, text in (('#4a90d9', 'Piece (example)'),
                            ('#fff0b3', 'Drop / Scrap')):
            tk.Canvas(self.legend_frame, width=12, height=12, bg=color,
                      highlightthickness=1, highlightbackground='#888').pack(side='left', padx=3)
            tk.Label(self.legend_frame, text=text,
                     font=('Segoe UI', 8)).pack(side='left', padx=(0, 8))

    def _refresh_legend(self):
        for w in self.legend_frame.winfo_children():
            w.destroy()
        tk.Canvas(self.legend_frame, width=12, height=12, bg='#fff0b3',
                  highlightthickness=1, highlightbackground='#cc8800').pack(side='left', padx=3)
        tk.Label(self.legend_frame, text='Drop/Scrap',
                 font=('Segoe UI', 8)).pack(side='left', padx=(0, 8))
        seen = set()
        for p in self._pieces:
            if p['fill'] not in seen:
                seen.add(p['fill'])
                tk.Canvas(self.legend_frame, width=12, height=12, bg=p['fill'],
                          highlightthickness=1,
                          highlightbackground=p['outline']).pack(side='left', padx=3)
                nm = p['name'] if len(p['name']) <= 14 else p['name'][:13] + '…'
                tk.Label(self.legend_frame, text=nm,
                         font=('Segoe UI', 8)).pack(side='left', padx=(0, 8))

    # ── calculate ─────────────────────────────────────────────────────────────

    def on_calculate(self):
        try:
            r = calculate_multi(
                self._pieces,
                self.stock_w_var.get(),
                self.stock_l_var.get(),
                self.kerf_var.get(),
                self.grain_match_var.get(),
                self.grain_dir_var.get(),
            )
        except Exception as e:
            messagebox.showerror('Calculation Error', str(e))
            return

        self._result      = r
        self._sheet_index = 0
        self._file_menu.entryconfig('Save...', state='normal')

        fmt = {
            'total_sheets': str(r['total_sheets']),
            'total_qty':    str(r['total_qty']),
            'total_sqf':    f'{r["total_sqf"]:.4f}',
            'sqf_stock':    f'{r["sqf_stock"]:.4f}',
            'utilization':  f'{r["utilization"]:.1%}',
            'waste_pct':    f'{r["waste_pct"]:.1%}',
            'scrap_sqf':    f'{r["scrap_sqf"]:.4f}',
        }
        for key, var in self.result_vars.items():
            var.set(fmt[key] + self.result_units[key])

        u = r['utilization']
        self._color_lbls['util'].config(
            fg=C_GREEN if u >= 0.80 else (C_AMBER if u >= 0.50 else C_RED))
        w = r['waste_pct']
        self._color_lbls['waste'].config(
            fg=C_GREEN if w <= 0.20 else (C_AMBER if w <= 0.50 else C_RED))

        self._refresh_table(r)
        self._refresh_legend()
        self._draw_sheet()

    def _refresh_table(self, r):
        self.tree.delete(*self.tree.get_children())
        area_stk = r['stock_width'] * r['stock_length']
        max_n    = max(len(s) for s in r['sheets']) if r['sheets'] else 1
        for i, sheet in enumerate(r['sheets']):
            n        = len(sheet)
            used_sqf = sum(it['w'] * it['h'] for it in sheet) / 144
            util_pct = (used_sqf * 144) / area_stk
            is_full  = n >= max_n
            status   = 'Full' if is_full else f'Partial ({n}/{max_n})'
            tag      = 'full' if is_full else 'partial'
            self.tree.insert('', 'end', iid=str(i),
                             values=(i + 1, n, f'{used_sqf:.3f}',
                                     f'{util_pct:.1%}', status),
                             tags=(tag,))

    # ── canvas ────────────────────────────────────────────────────────────────

    def _draw_placeholder(self):
        self.canvas.delete('all')
        self.canvas.create_text(CANVAS_W // 2, CANVAS_H // 2,
                                text='Add pieces and run\nCalculate to see layout',
                                fill='#aaaaaa', font=('Segoe UI', 11), justify='center')
        self.sheet_label_var.set('—')
        self.btn_prev.config(state='disabled')
        self.btn_next.config(state='disabled')

    def _prev_sheet(self):
        self._sheet_index -= 1
        self._draw_sheet()

    def _next_sheet(self):
        self._sheet_index += 1
        self._draw_sheet()

    def _draw_sheet(self):
        r = self._result
        if r is None:
            self._draw_placeholder()
            return

        total = r['total_sheets']
        idx   = max(0, min(self._sheet_index, total - 1))
        self._sheet_index = idx

        self.sheet_label_var.set(f'Sheet {idx + 1} of {total}')
        self.btn_prev.config(state='normal' if idx > 0         else 'disabled')
        self.btn_next.config(state='normal' if idx < total - 1 else 'disabled')

        self.canvas.delete('all')

        sw    = r['stock_width']
        sl    = r['stock_length']
        kerf  = r['kerf']
        scale = min((CANVAS_W - 2 * MARGIN) / sw, (CANVAS_H - 2 * MARGIN) / sl)
        spx   = sw * scale
        spy   = sl * scale
        ox    = (CANVAS_W - spx) / 2
        oy    = (CANVAS_H - spy) / 2

        # Sheet outline
        self.canvas.create_rectangle(ox, oy, ox + spx, oy + spy,
                                     fill='#ffffff', outline='#333333', width=2)

        # Grain direction indicator
        if r.get('grain_match'):
            grain_color = '#c8b48a'
            grain_step  = 9
            if r.get('grain_direction') == 'horizontal':
                y = oy + grain_step
                while y < oy + spy:
                    self.canvas.create_line(ox + 1, y, ox + spx - 1, y,
                                            fill=grain_color, width=1)
                    y += grain_step
            else:
                x = ox + grain_step
                while x < ox + spx:
                    self.canvas.create_line(x, oy + 1, x, oy + spy - 1,
                                            fill=grain_color, width=1)
                    x += grain_step

        items = r['sheets'][idx]

        # Draw pieces
        for it in items:
            x0 = ox + it['x'] * scale
            y0 = oy + it['y'] * scale
            x1 = x0 + it['w'] * scale
            y1 = y0 + it['h'] * scale
            self.canvas.create_rectangle(x0, y0, x1, y1,
                                         fill=it['fill'], outline=it['outline'], width=1)
            pw, ph = x1 - x0, y1 - y0
            if pw > 22 and ph > 12:
                self.canvas.create_text(
                    (x0 + x1) / 2, (y0 + y1) / 2,
                    text=it['name'], fill='white',
                    font=('Segoe UI', 7), width=max(1, int(pw - 4)))
            if it.get('rotated') and pw > 16 and ph > 10:
                self.canvas.create_text(x1 - 4, y0 + 5, text='↺',
                                        fill='white', font=('Segoe UI', 7, 'bold'),
                                        anchor='e')

        # Right-edge scrap strip (based on max packed x)
        if items:
            max_x_px = ox + max(it['x'] + it['w'] for it in items) * scale
            if max_x_px < ox + spx - 2:
                self._scrap_strip(max_x_px, oy, ox + spx, oy + spy)

            # Bottom-edge scrap strip (based on max packed y)
            max_y_px = oy + max(it['y'] + it['h'] for it in items) * scale
            if max_y_px < oy + spy - 2:
                self._scrap_strip(ox, max_y_px, ox + spx, oy + spy)

        # Per-row right-edge scrap
        if items and kerf == 0:
            rows: dict[float, list] = {}
            for it in items:
                rows.setdefault(it['y'], []).append(it)
            for y_val, row_items in rows.items():
                row_right = max(it['x'] + it['w'] for it in row_items)
                row_h     = max(it['h'] for it in row_items)
                rx = ox + row_right * scale
                if rx < ox + spx - 2:
                    ry0 = oy + y_val * scale
                    ry1 = ry0 + row_h * scale
                    self._scrap_strip(rx, ry0, ox + spx, ry1)

        # Dimension label (top)
        font_sm = ('Segoe UI', 8)
        lc = '#555555'
        n  = len(items)
        util = sum(it['w'] * it['h'] for it in items) / (sw * sl) if items else 0
        self.canvas.create_text(ox + spx / 2, oy - 9,
                                text=f'{sw}"  ×  {sl}"', fill=lc, font=font_sm)
        self.canvas.create_text(ox + spx / 2, oy + spy + 11,
                                text=f'Pieces: {n}  |  Util: {util:.1%}',
                                fill=lc, font=font_sm)

    def _hatch(self, x0, y0, x1, y1, color, step=6):
        for c in range(int(x0 - y1), int(x1 - y0) + step, step):
            lx0 = max(x0, y0 + c)
            lx1 = min(x1, y1 + c)
            if lx0 < lx1:
                self.canvas.create_line(lx0, lx0 - c, lx1, lx1 - c,
                                        fill=color, width=1)

    def _scrap_strip(self, x0, y0, x1, y1):
        if x1 <= x0 or y1 <= y0:
            return
        self.canvas.create_rectangle(x0, y0, x1, y1,
                                     fill='#fff0b3', outline='#cc8800', width=1)
        self._hatch(x0 + 1, y0 + 1, x1 - 1, y1 - 1, '#cc8800')


if __name__ == '__main__':
    OptiCutApp().mainloop()
