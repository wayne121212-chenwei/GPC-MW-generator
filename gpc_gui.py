#!/usr/bin/env python3
"""Desktop GUI for GPC molecular weight calculator."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from gpc_calculator import (
    baseline_correct,
    calculate_mw_mn_pdi,
    clip_with_interpolation,
    read_csv_data,
)


class GPCApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("GPC 分子量計算器")
        self.geometry("640x420")
        self.resizable(False, False)

        self.data_path_var = tk.StringVar()
        self.formula_var = tk.StringVar(value="-0.45*t+12.3")
        self.range_start_var = tk.StringVar(value="19")
        self.range_end_var = tk.StringVar(value="31")
        self.time_col_var = tk.StringVar(value="time")
        self.intensity_col_var = tk.StringVar(value="intensity")

        self._build_ui()

    def _build_ui(self) -> None:
        padding = {"padx": 10, "pady": 6}

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(frm, text="CSV 檔案").grid(row=0, column=0, sticky="w", **padding)
        ttk.Entry(frm, textvariable=self.data_path_var, width=58).grid(
            row=0, column=1, sticky="w", **padding
        )
        ttk.Button(frm, text="選擇檔案", command=self._choose_file).grid(
            row=0, column=2, sticky="w", **padding
        )

        ttk.Label(frm, text="檢量線公式 (log10(M))").grid(
            row=1, column=0, sticky="w", **padding
        )
        ttk.Entry(frm, textvariable=self.formula_var, width=30).grid(
            row=1, column=1, sticky="w", **padding
        )

        ttk.Label(frm, text="積分起點 (min)").grid(row=2, column=0, sticky="w", **padding)
        ttk.Entry(frm, textvariable=self.range_start_var, width=12).grid(
            row=2, column=1, sticky="w", **padding
        )

        ttk.Label(frm, text="積分終點 (min)").grid(row=3, column=0, sticky="w", **padding)
        ttk.Entry(frm, textvariable=self.range_end_var, width=12).grid(
            row=3, column=1, sticky="w", **padding
        )

        ttk.Label(frm, text="時間欄位名稱").grid(row=4, column=0, sticky="w", **padding)
        ttk.Entry(frm, textvariable=self.time_col_var, width=20).grid(
            row=4, column=1, sticky="w", **padding
        )

        ttk.Label(frm, text="強度欄位名稱").grid(row=5, column=0, sticky="w", **padding)
        ttk.Entry(frm, textvariable=self.intensity_col_var, width=20).grid(
            row=5, column=1, sticky="w", **padding
        )

        ttk.Button(frm, text="開始計算", command=self._calculate).grid(
            row=6, column=1, sticky="w", **padding
        )

        ttk.Label(frm, text="計算結果").grid(row=7, column=0, sticky="nw", **padding)
        self.output = tk.Text(frm, width=72, height=10)
        self.output.grid(row=7, column=1, columnspan=2, sticky="w", **padding)

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="選擇 GPC CSV 檔",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self.data_path_var.set(path)

    def _calculate(self) -> None:
        try:
            start = float(self.range_start_var.get().strip())
            end = float(self.range_end_var.get().strip())
            data = read_csv_data(
                self.data_path_var.get().strip(),
                self.time_col_var.get().strip(),
                self.intensity_col_var.get().strip(),
            )
            clipped = clip_with_interpolation(data, start, end)
            corrected = baseline_correct(clipped)
            mw, mn, pdi = calculate_mw_mn_pdi(corrected, self.formula_var.get().strip())
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("計算失敗", str(exc))
            return

        self.output.delete("1.0", tk.END)
        self.output.insert(
            tk.END,
            f"Mw: {mw:.6g}\nMn: {mn:.6g}\nPDI: {pdi:.6g}\n",
        )


def main() -> None:
    app = GPCApp()
    app.mainloop()


if __name__ == "__main__":
    main()
