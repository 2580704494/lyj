import calendar
import csv
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path


YEAR = 2021
RAIN_DAY_MM = Decimal("0.1")
SOURCE = Path(__file__).with_name("daily_HKO_RF_2021.csv")


def load_daily_records(path):
    records = {}
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = csv.reader(source)
        # 官方文件先放两行标题，第三行是字段名。
        next(rows)
        next(rows)
        next(rows)
        for row in rows:
            if not row:
                break
            year, month, day, value, completeness = row
            observed_on = date(int(year), int(month), int(day))
            if observed_on.year != YEAR or observed_on in records:
                raise ValueError(f"年份不符或日期重复：{observed_on}")
            if completeness != "C" or value in {"", "***"}:
                records[observed_on] = None
            elif value == "Trace":
                records[observed_on] = value
            else:
                amount = Decimal(value)
                if not amount.is_finite() or amount < 0:
                    raise ValueError(f"降雨量无效：{observed_on} {value}")
                records[observed_on] = amount
    return records


def summarize(daily_values):
    observed = [value for value in daily_values if value is not None]
    numeric = [value for value in observed if isinstance(value, Decimal)]
    rain_days = sum(value >= RAIN_DAY_MM for value in numeric)
    share = f"{Decimal(100 * rain_days) / len(observed):.1f}" if observed else ""
    return (
        len(daily_values),
        len(observed),
        len(daily_values) - len(observed),
        rain_days,
        observed.count("Trace"),
        share,
        f"{sum(numeric, Decimal(0)):.1f}" if observed else "",
    )


def main():
    records = load_daily_records(SOURCE)
    header = (
        "period", "calendar_days", "observed_days", "missing_days", "rain_days",
        "trace_days", "rain_day_pct", "numeric_rainfall_mm",
    )
    output = csv.writer(sys.stdout, lineterminator="\n")
    output.writerow(header)
    annual = []
    for month in range(1, 13):
        last_day = calendar.monthrange(YEAR, month)[1]
        days = [records.get(date(YEAR, month, day)) for day in range(1, last_day + 1)]
        annual.extend(days)
        output.writerow((f"{YEAR}-{month:02d}", *summarize(days)))
    output.writerow((str(YEAR), *summarize(annual)))


if __name__ == "__main__":
    main()

