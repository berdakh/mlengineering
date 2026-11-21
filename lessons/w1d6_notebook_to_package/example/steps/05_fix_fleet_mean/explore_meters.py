"""Quick look at the meter readings (was: meters_quicklook.ipynb)."""
from meterkit import daily_totals, load_readings, mean_kwh, peak_days


def main():
    readings = load_readings("meters.csv")
    daily = daily_totals(readings)
    m2 = readings[readings.meter_id == "M2"]
    print(m2.kwh.describe().round(3).to_string())
    print("fleet mean kwh per reading: %.3f" % mean_kwh(readings))
    print(peak_days(daily).to_string(index=False))


if __name__ == "__main__":
    main()
