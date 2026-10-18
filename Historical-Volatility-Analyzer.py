#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محاسبه نوسان تاریخی (Historical Volatility) از فایل اکسل قیمت‌ها

نصب نیازمندی‌ها:
    pip install pandas numpy openpyxl xlrd

اجرا:
    python historical_volatility.py                 # باز شدن پنجره انتخاب فایل
    python historical_volatility.py data.xls        # مسیر فایل
    python historical_volatility.py data.xls --days 365 --trading-days 252

فرمت مورد انتظار فایل (خروجی معمول TSETMC / نرم‌افزارهای تحلیل):
    ستون تاریخ (شمسی مثل 14050725 یا میلادی) + ستون قیمت پایانی (مثلاً «پایانی» یا Close)
"""
import argparse
import math
import sys

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# تبدیل تاریخ شمسی به میلادی (بدون نیاز به کتابخانه خارجی)
# ----------------------------------------------------------------------
def jalali_to_gregorian(jy: int, jm: int, jd: int):
    jy += 1595
    days = (-355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4
            + jd + (jm - 1) * 31 if jm < 7 else
            -355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4
            + jd + ((jm - 7) * 30 + 186))
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    month_len = [0, 31, 29 if (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0 else 28,
                 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 13 and gd > month_len[gm]:
        gd -= month_len[gm]
        gm += 1
    return gy, gm, gd


def parse_date(value):
    """تاریخ شمسی (۸ رقمی) یا میلادی را به Timestamp تبدیل می‌کند."""
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value)
    s = str(value).strip().replace("/", "").replace("-", "")
    s = s.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    if s.endswith(".0"):
        s = s[:-2]
    if len(s) != 8 or not s.isdigit():
        return pd.NaT
    y, m, d = int(s[:4]), int(s[4:6]), int(s[6:])
    try:
        if y < 1700:  # شمسی
            y, m, d = jalali_to_gregorian(y, m, d)
        return pd.Timestamp(y, m, d)
    except ValueError:
        return pd.NaT


# ----------------------------------------------------------------------
# خواندن فایل و تشخیص ستون‌ها
# ----------------------------------------------------------------------
DATE_HINTS = ("dtyyyymmdd", "date", "تاریخ")
PRICE_HINTS = ("پایانی", "close", "last", "adj", "قیمت")


def read_table(path: str) -> pd.DataFrame:
    if path.lower().endswith((".csv", ".txt")):
        return pd.read_csv(path)
    return pd.read_excel(path)  # .xls نیاز به xlrd دارد، .xlsx به openpyxl


def find_column(df: pd.DataFrame, hints, forbidden=()):
    for col in df.columns:
        name = str(col).strip().lower()
        if any(h in name for h in hints) and not any(f in name for f in forbidden):
            return col
    return None


def load_prices(path: str, date_col=None, price_col=None) -> pd.Series:
    df = read_table(path)
    date_col = date_col or find_column(df, DATE_HINTS)
    price_col = price_col or find_column(df, PRICE_HINTS)
    if date_col is None or price_col is None:
        sys.exit(f"ستون تاریخ/قیمت پیدا نشد. ستون‌های فایل: {list(df.columns)}\n"
                 "با --date-col و --price-col نام ستون‌ها را مشخص کنید.")
    out = pd.DataFrame({
        "date": df[date_col].map(parse_date),
        "price": pd.to_numeric(df[price_col], errors="coerce"),
    }).dropna()
    out = out[out["price"] > 0]
    out = out.drop_duplicates("date", keep="last").sort_values("date")
    if out.empty:
        sys.exit("هیچ ردیف معتبری در فایل پیدا نشد.")
    return out.set_index("date")["price"]


# ----------------------------------------------------------------------
# محاسبه نوسان
# ----------------------------------------------------------------------
def historical_volatility(prices: pd.Series, window_days: int = 365,
                          trading_days: int | None = None) -> dict:
    end = prices.index.max()
    start = end - pd.Timedelta(days=window_days)
    p = prices[prices.index >= start]
    if len(p) < 3:
        sys.exit("داده‌ی کافی در بازه‌ی انتخابی وجود ندارد.")

    log_ret = np.log(p / p.shift(1)).dropna()          # بازده لگاریتمی روزانه
    daily_sigma = log_ret.std(ddof=1)                    # انحراف معیار نمونه
    n = len(log_ret)
    ann_factor = trading_days if trading_days else n     # پیش‌فرض: تعداد روزهای معاملاتی واقعی بازه
    annual_sigma = daily_sigma * math.sqrt(ann_factor)

    return {
        "start": p.index.min(), "end": p.index.max(),
        "n_prices": len(p), "n_returns": n,
        "daily": daily_sigma, "annual": annual_sigma,
        "ann_factor": ann_factor,
        "mean_daily": log_ret.mean(),
        "max_up": log_ret.max(), "max_down": log_ret.min(),
        "first_price": p.iloc[0], "last_price": p.iloc[-1],
    }


def pick_file_dialog() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="فایل اکسل قیمت‌ها را انتخاب کنید",
            filetypes=[("Excel / CSV", "*.xls *.xlsx *.csv"), ("All", "*.*")])
        root.destroy()
        if path:
            return path
    except Exception:
        pass
    return input("مسیر فایل اکسل را وارد کنید: ").strip().strip('"')


def main():
    ap = argparse.ArgumentParser(description="محاسبه نوسان تاریخی از فایل اکسل")
    ap.add_argument("file", nargs="?", help="مسیر فایل .xls / .xlsx / .csv")
    ap.add_argument("--days", type=int, default=365, help="طول بازه به روز تقویمی (پیش‌فرض ۳۶۵)")
    ap.add_argument("--trading-days", type=int, default=None,
                    help="تعداد روز معاملاتی برای سالانه‌سازی (پیش‌فرض: تعداد واقعی روزهای معاملاتی بازه)")
    ap.add_argument("--date-col", default=None, help="نام ستون تاریخ")
    ap.add_argument("--price-col", default=None, help="نام ستون قیمت")
    args = ap.parse_args()

    path = args.file or pick_file_dialog()
    prices = load_prices(path, args.date_col, args.price_col)
    r = historical_volatility(prices, args.days, args.trading_days)

    print("=" * 52)
    print(f"ّFile: {path}")
    print(f"Gain: {r['start']:%Y-%m-%d} تا {r['end']:%Y-%m-%d} "
          f"({r['n_prices']} Price، {r['n_returns']} Gain)")
    print(f"Beginning Price → End: {r['first_price']:,.0f} → {r['last_price']:,.0f}")
    print("-" * 52)
    print(f"Daily Volatility (σ Daily):   {r['daily'] * 100:.3f}%")
    print(f"Annual Volatility (√{r['ann_factor']} × σ):  {r['annual'] * 100:.2f}%")
    print(f"Max. Daily Return: {r['max_up'] * 100:+.2f}%   Min: {r['max_down'] * 100:+.2f}%")
    print("=" * 52)


if __name__ == "__main__":
    main()