# Historical Volatility Calculator

A small Python tool that reads an Excel (or CSV) file of daily prices and computes the **historical volatility** over the most recent year of data.

It was built for price exports from Iranian market tools (TSETMC-style files with a Jalali `<DTYYYYMMDD>` date column and a `پایانی` close-price column), but it also works with any file that has a date column and a close-price column, including Gregorian dates.

## Features

- Reads `.xls`, `.xlsx` and `.csv` files
- Auto-detects the date and price columns (or lets you name them)
- Built-in Jalali (Persian) → Gregorian date conversion, with no extra dependency
- Uses the last 365 calendar days of data, counted back from the latest date in the file
- Reports daily and annualized volatility, plus the best and worst daily return
- Opens a file-picker window if you don't pass a file path

## Installation

Requires Python 3.10+.

```bash
pip install pandas numpy openpyxl xlrd
```

`xlrd` is only needed for legacy `.xls` files, and `openpyxl` for `.xlsx`.

## Usage

```bash
# Pick the file in a dialog window
python historical_volatility.py

# Pass the file directly
python historical_volatility.py prices.xls

# Custom window and annualization
python historical_volatility.py prices.xls --days 365 --trading-days 252

# Specify column names explicitly
python historical_volatility.py prices.xlsx --date-col "<DTYYYYMMDD>" --price-col "پایانی"
```

### Options

| Option | Default | Description |
|---|---|---|
| `file` | file dialog | Path to the `.xls` / `.xlsx` / `.csv` file |
| `--days` | `365` | Length of the look-back window, in calendar days |
| `--trading-days` | actual count | Number of trading days used to annualize. If omitted, the number of daily returns observed in the window is used |
| `--date-col` | auto | Name of the date column |
| `--price-col` | auto | Name of the close-price column |

### Input format

The file needs one date column and one price column, one row per trading day:

| `<TICKER>` | `<DTYYYYMMDD>` | `پایانی` | `<VOL>` | `<OPENINT>` |
|---|---|---|---|---|
| طلا-ت | 14050724 | 1829804.00 | 5237251 | 9583142942180.00 |

- **Date column:** matched by names containing `date`, `dtyyyymmdd` or `تاریخ`. Values are 8-digit dates (`YYYYMMDD`). Years below 1700 are treated as Jalali, otherwise Gregorian.
- **Price column:** matched by names containing `پایانی`, `close`, `last`, `adj` or `قیمت`.
- Rows with a missing date or a non-positive price are dropped, and duplicate dates keep the last row.

### Example output

```
====================================================
File: prices.xls
Period: 2025-10-18 to 2026-10-17 (240 prices, 239 returns)
First → last price: 775,713 → 1,822,945
----------------------------------------------------
Daily volatility (σ_daily):      2.528%
Annualized volatility (√239 × σ): 39.08%
Best daily return:  +7.38%
Worst daily return: -10.54%
====================================================
```

Volatility is the sample standard deviation of daily log returns. The annualized figure scales it by the square root of the number of trading days.

## Method

1. Keep the prices from the last `--days` calendar days, counted back from the most recent date in the file.
2. Compute daily log returns: `r_t = ln(P_t / P_{t-1})`.
3. Compute the daily volatility as the sample standard deviation of the returns (`ddof = 1`).
4. Annualize: `σ_annual = σ_daily × √N`, where `N` is `--trading-days`, or the number of returns in the window if not given.

Returns are computed between consecutive rows, so market holidays and weekends are not filled in. Each return is one trading-day move.

## Notes and limitations

- Volatility is computed from close prices only. Adjusted prices for splits or dividends should be supplied in the file if you need them.
- The result is a backward-looking estimate. It is not a forecast.
- The Jalali conversion is checked against known dates, for example 1 Farvardin 1400 = 2021-03-21 and 25 Mehr 1405 = 2026-10-17.

## License

Add the license of your choice (for example MIT) here.