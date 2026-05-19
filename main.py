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

import json
import math
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

_HERE = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent

MODELS = {
    'Model A': {'fractional_openings': 1,       'doors_per_frame': 1},
    'Model Z': {'fractional_openings': 1/2,     'doors_per_frame': 2},
    'Model B': {'fractional_openings': 1/2,     'doors_per_frame': 2},
    'Model C': {'fractional_openings': 1/3,     'doors_per_frame': 3},
    'Model D': {'fractional_openings': 1/4,     'doors_per_frame': 4},
    'Model E': {'fractional_openings': 1/5,     'doors_per_frame': 5},
    'Model F': {'fractional_openings': 1/6,     'doors_per_frame': 6},
}

STOCK_SIZES = {
    '4x8  (48" × 96")':   (48,  96),
    '5x8  (60" × 96")':   (60,  96),
    '4x10 (48" × 120")':  (48,  120),
    '5x10 (60" × 120")':  (60,  120),
    '4x12 (48" × 144")':  (48,  144),
    '5x12 (60" × 144")':  (60,  144),
    'Custom':              None,
}

FWL_LIST = [1/15, 1/12, 1/10, 1/9, 1/8, 1/7, 1/6, 1/5, 1/4, 1/3, 1/2, 1]
FHL_LIST = [1/4, 1/3, 1/2, 1]

FRACTION_LABELS = {
    1/15: '1/15', 1/12: '1/12', 1/10: '1/10', 1/9: '1/9',
    1/8:  '1/8',  1/7:  '1/7',  1/6:  '1/6',  1/5: '1/5',
    1/4:  '1/4',  1/3:  '1/3',  1/2:  '1/2',  1:   '1',
}

CANVAS_W = 320
CANVAS_H = 480
MARGIN   = 18


def find_frac(value, frac_list, stock_size):
    for frac in frac_list:
        if value <= stock_size * frac:
            return frac
    return frac_list[-1]


def calculate(model_type, locker_width, locker_height, qty_frames, stock_width, stock_length):
    model           = MODELS[model_type]
    frac_openings   = model['fractional_openings']
    doors_per_frame = model['doors_per_frame']

    sqf_stock    = (stock_width * stock_length) / 144
    fwl          = find_frac(locker_width,  FWL_LIST, stock_width)
    fhl          = find_frac(locker_height, FHL_LIST, stock_length)
    sqf_door     = sqf_stock * fwl * frac_openings * fhl
    qty_doors    = doors_per_frame * qty_frames
    total_sqf    = sqf_door * qty_doors
    total_sheets = math.ceil(total_sqf / sqf_stock)

    doors_across    = round(1 / fwl)
    doors_down      = round(1 / (fhl * frac_openings))
    doors_per_sheet = doors_across * doors_down
    door_w          = stock_width  * fwl
    door_h          = stock_length * fhl * frac_openings

    return {
        'sqf_stock':        sqf_stock,
        'fwl':              fwl,
        'fhl':              fhl,
        'sqf_door':         sqf_door,
        'qty_doors':        qty_doors,
        'total_sqf':        total_sqf,
        'total_sheets':     total_sheets,
        'doors_across':     doors_across,
        'doors_down':       doors_down,
        'doors_per_sheet':  doors_per_sheet,
        'door_w':           door_w,
        'door_h':           door_h,
        'stock_width':      stock_width,
        'stock_length':     stock_length,
    }


class OptiCutApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('OptiCut')
        self.resizable(False, False)
        self.iconbitmap(str(_HERE / 'saw-blade.ico'))
        self._result = None
        self._sheet_index = 0
        self._build_ui()

    def _build_ui(self):
        self._build_menu()
        pad = {'padx': 10, 'pady': 5}

        # ── left column: config + button + output ──────────────────────────
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky='ns')

        cfg = ttk.LabelFrame(left, text='Configuration')
        cfg.grid(row=0, column=0, sticky='ew', **pad)

        # Locker Dimensions
        dim = ttk.LabelFrame(cfg, text='Locker Dimensions')
        dim.grid(row=0, column=0, sticky='n', **pad)

        ttk.Label(dim, text='Model Type').grid(row=0, column=0, sticky='w', **pad)
        self.model_var = tk.StringVar(value='Model A')
        ttk.Combobox(dim, textvariable=self.model_var, values=list(MODELS.keys()),
                     state='readonly', width=12).grid(row=0, column=1, **pad)

        ttk.Label(dim, text='Locker Width (in)').grid(row=1, column=0, sticky='w', **pad)
        self.width_var = tk.DoubleVar(value=9.0)
        ttk.Entry(dim, textvariable=self.width_var, width=12).grid(row=1, column=1, **pad)

        ttk.Label(dim, text='Locker Height (in)').grid(row=2, column=0, sticky='w', **pad)
        self.height_var = tk.DoubleVar(value=96.0)
        ttk.Entry(dim, textvariable=self.height_var, width=12).grid(row=2, column=1, **pad)

        # Quantities
        qty = ttk.LabelFrame(cfg, text='Quantities')
        qty.grid(row=0, column=1, sticky='n', **pad)

        ttk.Label(qty, text='Quantity Frames').grid(row=0, column=0, sticky='w', **pad)
        self.qty_frames_var = tk.IntVar(value=100)
        ttk.Entry(qty, textvariable=self.qty_frames_var, width=12).grid(row=0, column=1, **pad)

        ttk.Label(qty, text='Lockers per Frame').grid(row=1, column=0, sticky='w', **pad)
        self.lpf_label = ttk.Label(qty, text='1', width=12, relief='sunken', anchor='center')
        self.lpf_label.grid(row=1, column=1, **pad)

        # Material Stock Size
        stk = ttk.LabelFrame(cfg, text='Material Stock Size')
        stk.grid(row=0, column=2, sticky='n', **pad)

        ttk.Label(stk, text='Stock Size').grid(row=0, column=0, sticky='w', **pad)
        self.stock_size_var = tk.StringVar(value='5x8  (60" × 96")')
        self.stock_cb = ttk.Combobox(stk, textvariable=self.stock_size_var,
                                     values=list(STOCK_SIZES.keys()),
                                     state='readonly', width=18)
        self.stock_cb.grid(row=0, column=1, **pad)

        ttk.Label(stk, text='Width (in)').grid(row=1, column=0, sticky='w', **pad)
        self.stock_w_var = tk.DoubleVar(value=60.0)
        self.stock_w_entry = ttk.Entry(stk, textvariable=self.stock_w_var, width=12)
        self.stock_w_entry.grid(row=1, column=1, **pad)

        ttk.Label(stk, text='Length (in)').grid(row=2, column=0, sticky='w', **pad)
        self.stock_l_var = tk.DoubleVar(value=96.0)
        self.stock_l_entry = ttk.Entry(stk, textvariable=self.stock_l_var, width=12)
        self.stock_l_entry.grid(row=2, column=1, **pad)

        ttk.Button(left, text='Calculate', command=self.on_calculate).grid(
            row=1, column=0, pady=10)

        # Output
        out = ttk.LabelFrame(left, text='Output')
        out.grid(row=2, column=0, sticky='ew', **pad)

        output_rows = [
            ('Total Sheets',       'total_sheets', ''),
            ('Quantity Doors',     'qty_doors',    ''),
            ('Door SQF',           'sqf_door',     ' SQF'),
            ('Total SQF',          'total_sqf',    ' SQF'),
            ('Stock Sheet SQF',    'sqf_stock',    ' SQF'),
            ('Frac. Width Limit',  'fwl',          ''),
            ('Frac. Height Limit', 'fhl',          ''),
        ]
        self.result_vars  = {}
        self.result_units = {}
        for i, (label, key, unit) in enumerate(output_rows):
            ttk.Label(out, text=label).grid(row=i, column=0, sticky='w', **pad)
            var = tk.StringVar(value='—')
            ttk.Label(out, textvariable=var, width=20, relief='sunken', anchor='e').grid(
                row=i, column=1, **pad)
            self.result_vars[key]  = var
            self.result_units[key] = unit

        # ── right column: nesting visualisation ────────────────────────────
        viz = ttk.LabelFrame(self, text='Nesting Visualisation')
        viz.grid(row=0, column=1, sticky='ns', padx=(0, 10), pady=10)

        self.canvas = tk.Canvas(viz, width=CANVAS_W, height=CANVAS_H,
                                bg='#f0f0f0', relief='sunken', bd=1)
        self.canvas.grid(row=0, column=0, columnspan=3, padx=8, pady=(8, 4))

        nav = ttk.Frame(viz)
        nav.grid(row=1, column=0, columnspan=3, pady=(0, 8))

        self.btn_prev = ttk.Button(nav, text='◀', width=3, command=self._prev_sheet)
        self.btn_prev.grid(row=0, column=0, padx=4)

        self.sheet_label_var = tk.StringVar(value='—')
        ttk.Label(nav, textvariable=self.sheet_label_var, width=16,
                  anchor='center').grid(row=0, column=1, padx=4)

        self.btn_next = ttk.Button(nav, text='▶', width=3, command=self._next_sheet)
        self.btn_next.grid(row=0, column=2, padx=4)
        self._draw_placeholder()

        # traces
        self.model_var.trace_add('write', lambda *_: self._refresh_lpf())
        self.stock_size_var.trace_add('write', lambda *_: self._on_stock_size_change())
        self._refresh_lpf()
        self._on_stock_size_change()

    # ── menu ───────────────────────────────────────────────────────────────

    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='File', menu=file_menu)

        file_menu.add_command(label='Open...', accelerator='Ctrl+O', command=self._open)
        file_menu.add_command(label='Save...', accelerator='Ctrl+S', command=self._save, state='disabled')
        file_menu.add_separator()
        file_menu.add_command(label='About',                          command=self._show_about)
        file_menu.add_separator()
        file_menu.add_command(label='Exit',    accelerator='Alt+F4',  command=self.destroy)
        self._file_menu = file_menu

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
            'model':        self.model_var.get(),
            'width':        self.width_var.get(),
            'height':       self.height_var.get(),
            'qty_frames':   self.qty_frames_var.get(),
            'stock_size':   self.stock_size_var.get(),
            'stock_width':  self.stock_w_var.get(),
            'stock_length': self.stock_l_var.get(),
            'output': {
                k: var.get()
                for k, var in self.result_vars.items()
            } if self._result else {},
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
        _REQUIRED = {'model', 'width', 'height', 'qty_frames', 'stock_width', 'stock_length'}
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception:
            messagebox.showerror(
                'Invalid File',
                'This file could not be read.\n\nPlease open an OptiCut output file only (.json).'
            )
            return
        if not isinstance(data, dict) or not _REQUIRED.issubset(data):
            messagebox.showerror(
                'Invalid File',
                'This does not appear to be an OptiCut file.\n\nPlease open an OptiCut output file only (.json).'
            )
            return
        try:
            self.model_var.set(data.get('model',       'Model A'))
            self.width_var.set(data.get('width',       9.0))
            self.height_var.set(data.get('height',     96.0))
            self.qty_frames_var.set(data.get('qty_frames', 100))
            self.stock_size_var.set(data.get('stock_size', '5x8  (60" × 96")'))
            self.stock_w_var.set(data.get('stock_width',  60.0))
            self.stock_l_var.set(data.get('stock_length', 96.0))
            self.on_calculate()
        except Exception as e:
            messagebox.showerror('Open Error', str(e))

    def _show_about(self):
        win = tk.Toplevel(self)
        win.title('About OptiCut')
        win.resizable(False, False)
        win.grab_set()
        ttk.Label(win, text='OptiCut', font=('Segoe UI', 16, 'bold')).pack(pady=(20, 4))
        ttk.Label(win, text='Version 1.0.1').pack()
        ttk.Label(win, text='Locker door nesting calculator.').pack(pady=(8, 0))
        ttk.Label(win, text='Optimized for Hollman Inc. Lockers').pack(pady=(8, 0))
        ttk.Label(win, text='© 2026 - Northern Lights Studios').pack(pady=(4, 8))
        img_scale  = -16  # 1 = original | enlarge: 2, 3, 4 … | shrink: -2, -3, -4 …
        img = tk.PhotoImage(file=str(_HERE / 'NorthernLights SM.png'))
        if img_scale > 1:
            img = img.zoom(img_scale)
        elif img_scale < -1:
            img = img.subsample(-img_scale)
        img_label  = ttk.Label(win, image=img)
        img_label.image = img
        img_label.pack(pady=(0, 12))
        ttk.Button(win, text='OK', command=win.destroy).pack(pady=(0, 16))

    # ── helpers ────────────────────────────────────────────────────────────

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

    def _refresh_lpf(self):
        model = self.model_var.get()
        if model in MODELS:
            self.lpf_label.config(text=str(MODELS[model]['doors_per_frame']))

    # ── calculate ──────────────────────────────────────────────────────────

    def on_calculate(self):
        try:
            result = calculate(
                self.model_var.get(),
                self.width_var.get(),
                self.height_var.get(),
                self.qty_frames_var.get(),
                self.stock_w_var.get(),
                self.stock_l_var.get(),
            )
        except Exception as e:
            messagebox.showerror('Calculation Error', str(e))
            return

        self._result = result
        self._file_menu.entryconfig('Save...', state='normal')
        self._sheet_index = 0

        fmt = {
            'total_sheets': str(result['total_sheets']),
            'qty_doors':    str(result['qty_doors']),
            'sqf_door':     f"{result['sqf_door']:.4f}",
            'total_sqf':    f"{result['total_sqf']:.4f}",
            'sqf_stock':    f"{result['sqf_stock']:.4f}",
            'fwl':          self._frac_label(result['fwl']),
            'fhl':          self._frac_label(result['fhl']),
        }
        for key, var in self.result_vars.items():
            var.set(fmt[key] + self.result_units[key])

        self._draw_sheet()

    # ── nesting canvas ─────────────────────────────────────────────────────

    def _draw_placeholder(self):
        self.canvas.delete('all')
        self.canvas.create_text(CANVAS_W // 2, CANVAS_H // 2,
                                text='Run Calculate to see\nnesting layout',
                                fill='#aaaaaa', font=('Segoe UI', 11),
                                justify='center')
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
            return

        total        = r['total_sheets']
        idx          = max(0, min(self._sheet_index, total - 1))
        self._sheet_index = idx

        self.sheet_label_var.set(f'Sheet {idx + 1} of {total}')
        self.btn_prev.config(state='normal' if idx > 0         else 'disabled')
        self.btn_next.config(state='normal' if idx < total - 1 else 'disabled')

        self.canvas.delete('all')

        sw = r['stock_width']
        sl = r['stock_length']
        scale = min((CANVAS_W - 2 * MARGIN) / sw,
                    (CANVAS_H - 2 * MARGIN) / sl)

        # centre the sheet on the canvas
        sheet_px = sw * scale
        sheet_py = sl * scale
        ox = (CANVAS_W - sheet_px) / 2
        oy = (CANVAS_H - sheet_py) / 2

        # sheet background
        self.canvas.create_rectangle(ox, oy, ox + sheet_px, oy + sheet_py,
                                     fill='#ffffff', outline='#333333', width=2)

        # door grid for this sheet
        across = r['doors_across']
        down   = r['doors_down']
        dw_px  = r['door_w'] * scale
        dh_px  = r['door_h'] * scale

        first_door = idx * r['doors_per_sheet']
        qty_doors  = r['qty_doors']

        scrap_slots = 0

        for row in range(down):
            for col in range(across):
                door_num = first_door + row * across + col
                x0 = ox + col * dw_px
                y0 = oy + row * dh_px
                x1 = x0 + dw_px
                y1 = y0 + dh_px

                if door_num < qty_doors:
                    self.canvas.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                                                 fill='#4a90d9', outline='#1a5fa8', width=1)
                    if dw_px > 22 and dh_px > 14:
                        self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2,
                                                text=str(door_num + 1),
                                                fill='white', font=('Segoe UI', 8))
                else:
                    scrap_slots += 1
                    self.canvas.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                                                 fill='#fff0b3', outline='#cc8800', width=1)
                    # diagonal hatch lines
                    hstep = 6
                    rx0, ry0, rx1, ry1 = x0 + 2, y0 + 2, x1 - 2, y1 - 2
                    for c in range(int(rx0 - ry1), int(rx1 - ry0) + hstep, hstep):
                        lx0 = max(rx0, ry0 + c)
                        lx1 = min(rx1, ry1 + c)
                        if lx0 < lx1:
                            self.canvas.create_line(lx0, lx0 - c, lx1, lx1 - c,
                                                    fill='#cc8800', width=1)
                    if dw_px > 30 and dh_px > 16:
                        self.canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2,
                                                text='DROP', fill='#996600',
                                                font=('Segoe UI', 7, 'bold'))

        # scrap summary (only on sheets that have drop)
        label_color = '#555555'
        font_sm = ('Segoe UI', 8)
        if scrap_slots:
            scrap_sqf = scrap_slots * r['door_w'] * r['door_h'] / 144
            self.canvas.create_text(ox + sheet_px / 2, oy + sheet_py + 10,
                                    text=f'Drop: {scrap_slots} slot(s)  |  {scrap_sqf:.3f} SQF',
                                    fill='#996600', font=('Segoe UI', 8, 'bold'))

        # dimension labels
        self.canvas.create_text(ox + sheet_px / 2, oy - 6,
                                text=f'{sw}"', fill=label_color, font=font_sm)
        self.canvas.create_text(ox - 10, oy + sheet_py / 2,
                                text=f'{sl}"', fill=label_color, font=font_sm,
                                angle=90)

    @staticmethod
    def _frac_label(val):
        for k, v in FRACTION_LABELS.items():
            if abs(val - k) < 1e-9:
                return v
        return f'{val:.6f}'


if __name__ == '__main__':
    OptiCutApp().mainloop()
