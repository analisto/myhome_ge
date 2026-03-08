"""
Business analytics charts for myhome.ge dataset.
Outputs all charts to charts/ directory.

Usage:
    python scripts/generate_charts.py
"""

import csv
import collections
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

csv.field_size_limit(10_000_000)

DATA_FILE = Path(__file__).parent.parent / "data" / "data_clean.csv"
CHARTS_DIR = Path(__file__).parent.parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

# ── Style ──────────────────────────────────────────────────────────────────────
BRAND_BLUE   = "#1A56DB"
BRAND_GREEN  = "#057A55"
BRAND_ORANGE = "#FF5A1F"
BRAND_GRAY   = "#6B7280"
BRAND_PURPLE = "#7E3AF2"
PALETTE = [BRAND_BLUE, BRAND_GREEN, BRAND_ORANGE, BRAND_GRAY, BRAND_PURPLE,
           "#E3A008", "#C81E1E", "#0E9F6E"]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.alpha": 0.35,
    "figure.dpi": 150,
})

DEAL_LABEL = {"1": "For Sale", "2": "For Rent", "7": "Daily Rent"}
RE_LABEL   = {"1": "Apartment", "2": "House", "3": "Commercial",
              "4": "Land", "5": "New Development", "6": "Hotel/Hostel"}
SELLER_LABEL = {"agent": "Agency", "broker": "Broker",
                "physical": "Private Owner", "developer": "Developer"}

# ── Data loading pass ──────────────────────────────────────────────────────────
print("Loading data…", flush=True)

city_deal        = collections.defaultdict(collections.Counter)
re_type_counts   = collections.Counter()
seller_deal      = collections.defaultdict(collections.Counter)
vip_counts       = collections.Counter()

tbilisi_dist_sale_sqm   = collections.defaultdict(list)
tbilisi_dist_rent_total = collections.defaultdict(list)
tbilisi_sale_rooms      = collections.defaultdict(list)
tbilisi_rent_rooms      = collections.defaultdict(list)
tbilisi_sale_bands      = collections.Counter()
tbilisi_rent_bands      = collections.Counter()

batumi_dist_rent = collections.defaultdict(list)

with DATA_FILE.open(encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    for row in reader:
        city  = row["city_name"]
        deal  = row["deal_type_id"]
        re    = row["real_estate_type_id"]
        dist  = row["district_name"]
        seller = row["user_type_type"]
        room  = row["room"]

        city_deal[city][deal] += 1
        re_type_counts[RE_LABEL.get(re, re)] += 1
        seller_deal[SELLER_LABEL.get(seller, seller)][deal] += 1

        vip = ("Super VIP" if row["is_super_vip"] == "True"
               else "VIP+" if row["is_vip_plus"] == "True"
               else "VIP"  if row["is_vip"]      == "True"
               else "Standard")
        vip_counts[vip] += 1

        try:
            usd_total = float(row["usd_total"])
            usd_sqm   = float(row["usd_per_sqm"])
            area      = float(row["area"])
        except (ValueError, TypeError):
            usd_total = usd_sqm = area = None

        # Tbilisi apartments
        if city == "თბილისი" and re == "1" and dist:
            if deal == "1" and usd_sqm and 5 < usd_sqm < 10_000 and usd_total and 1_000 < usd_total < 5_000_000:
                tbilisi_dist_sale_sqm[dist].append(usd_sqm)
                if usd_total:
                    if usd_total < 50_000:            tbilisi_sale_bands["<$50k"] += 1
                    elif usd_total < 100_000:         tbilisi_sale_bands["$50k–100k"] += 1
                    elif usd_total < 200_000:         tbilisi_sale_bands["$100k–200k"] += 1
                    elif usd_total < 500_000:         tbilisi_sale_bands["$200k–500k"] += 1
                    else:                             tbilisi_sale_bands[">$500k"] += 1
                if room.isdigit() and 1 <= int(room) <= 5:
                    tbilisi_sale_rooms[int(room)].append(usd_total)

            elif deal == "2" and usd_total and 50 < usd_total < 20_000:
                tbilisi_dist_rent_total[dist].append(usd_total)
                if usd_total < 300:             tbilisi_rent_bands["<$300"] += 1
                elif usd_total < 500:           tbilisi_rent_bands["$300–500"] += 1
                elif usd_total < 800:           tbilisi_rent_bands["$500–800"] += 1
                elif usd_total < 1_500:         tbilisi_rent_bands["$800–1,500"] += 1
                else:                           tbilisi_rent_bands[">$1,500"] += 1
                if room.isdigit() and 1 <= int(room) <= 5:
                    tbilisi_rent_rooms[int(room)].append(usd_total)

        # Batumi apartments rent
        if city == "ბათუმი" and re == "1" and deal == "2" and dist and usd_total and 50 < usd_total < 10_000:
            batumi_dist_rent[dist].append(usd_total)

print("Done loading. Generating charts…", flush=True)


def median(lst):
    s = sorted(lst)
    return s[len(s) // 2]


def save(fig, name):
    path = CHARTS_DIR / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {name}")


# ── Chart 1: Market Share by City ─────────────────────────────────────────────
top_cities_raw = sorted(city_deal.items(), key=lambda x: -sum(x[1].values()))[:9]
top_cities_raw = [(c, v) for c, v in top_cities_raw if c]  # drop blank
city_labels_en = {
    "თბილისი": "Tbilisi", "ბათუმი": "Batumi",
    "მცხეთის მუნიციპალიტეტი": "Mtskheta Municipality",
    "ქუთაისი": "Kutaisi", "ბაკურიანი": "Bakuriani",
    "რუსთავი": "Rustavi", "მცხეთა": "Mtskheta",
    "თელავი": "Telavi", "გარდაბნის მუნიციპალიტეტი": "Gardabani",
}
cities  = [city_labels_en.get(c, c) for c, _ in top_cities_raw]
totals  = [sum(v.values()) for _, v in top_cities_raw]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(cities, totals, color=BRAND_BLUE, width=0.6)
ax.bar_label(bars, labels=[f"{v:,}" for v in totals], padding=4, fontsize=9)
ax.set_title("Total Active Listings by City", fontsize=14, fontweight="bold", pad=12)
ax.set_ylabel("Number of Listings")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
plt.xticks(rotation=20, ha="right")
save(fig, "01_listings_by_city.png")

# ── Chart 2: Deal Type Mix by Top City ────────────────────────────────────────
top5 = [(city_labels_en.get(c, c), v) for c, v in top_cities_raw[:6] if c]
labels  = [c for c, _ in top5]
sales   = [v["1"] for _, v in top5]
rents   = [v["2"] for _, v in top5]
daily   = [v["7"] for _, v in top5]

x = np.arange(len(labels))
w = 0.25
fig, ax = plt.subplots(figsize=(11, 5))
ax.bar(x - w, sales, w, label="For Sale",   color=BRAND_BLUE)
ax.bar(x,     rents, w, label="For Rent",   color=BRAND_GREEN)
ax.bar(x + w, daily, w, label="Daily Rent", color=BRAND_ORANGE)
ax.set_xticks(x); ax.set_xticklabels(labels, rotation=15, ha="right")
ax.set_title("Sale vs. Rent vs. Daily — Top Cities", fontsize=14, fontweight="bold", pad=12)
ax.set_ylabel("Number of Listings")
ax.legend()
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
save(fig, "02_deal_type_by_city.png")

# ── Chart 3: Listings by Property Type ────────────────────────────────────────
re_sorted = sorted(re_type_counts.items(), key=lambda x: -x[1])
re_names  = [r[0] for r in re_sorted]
re_vals   = [r[1] for r in re_sorted]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(re_names, re_vals, color=PALETTE[:len(re_names)], width=0.6)
ax.bar_label(bars, labels=[f"{v:,}" for v in re_vals], padding=4, fontsize=9)
ax.set_title("Listings by Property Type", fontsize=14, fontweight="bold", pad=12)
ax.set_ylabel("Number of Listings")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
plt.xticks(rotation=15, ha="right")
save(fig, "03_listings_by_property_type.png")

# ── Chart 4: Tbilisi — Median Sale Price per sqm by District ──────────────────
dist_sale_med = {
    d: median(v) for d, v in tbilisi_dist_sale_sqm.items() if len(v) >= 200
}
dist_labels_en = {
    "ვაკე-საბურთალო": "Vake-Saburtalo", "ძველი თბილისი": "Old Tbilisi",
    "გლდანი-ნაძალადევი": "Gldani-Nadzaladevi", "ისანი-სამგორი": "Isani-Samgori",
    "დიდუბე-ჩუღურეთი": "Didube-Chughureti", "თბილისის შემოგარენი": "Tbilisi Outskirts",
}
ds_labels = [dist_labels_en.get(d, d) for d in sorted(dist_sale_med, key=lambda d: -dist_sale_med[d])]
ds_vals   = [dist_sale_med[d] for d in sorted(dist_sale_med, key=lambda d: -dist_sale_med[d])]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(ds_labels, ds_vals, color=BRAND_BLUE, width=0.6)
ax.bar_label(bars, labels=[f"${v:,.0f}" for v in ds_vals], padding=4, fontsize=9)
ax.set_title("Tbilisi — Median Apartment Sale Price per m²  (USD)", fontsize=14, fontweight="bold", pad=12)
ax.set_ylabel("USD per m²")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${int(x):,}"))
plt.xticks(rotation=15, ha="right")
save(fig, "04_tbilisi_sale_price_per_sqm_by_district.png")

# ── Chart 5: Tbilisi — Median Monthly Rent by District ───────────────────────
dist_rent_med = {
    d: median(v) for d, v in tbilisi_dist_rent_total.items() if len(v) >= 200
}
dr_sorted = sorted(dist_rent_med.items(), key=lambda x: -x[1])
dr_labels = [dist_labels_en.get(d, d) for d, _ in dr_sorted]
dr_vals   = [v for _, v in dr_sorted]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(dr_labels, dr_vals, color=BRAND_GREEN, width=0.6)
ax.bar_label(bars, labels=[f"${v:,.0f}" for v in dr_vals], padding=4, fontsize=9)
ax.set_title("Tbilisi — Median Monthly Rent by District  (USD)", fontsize=14, fontweight="bold", pad=12)
ax.set_ylabel("USD / month")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${int(x):,}"))
plt.xticks(rotation=15, ha="right")
save(fig, "05_tbilisi_rent_by_district.png")

# ── Chart 6: Tbilisi — Median Sale Price by Number of Bedrooms ───────────────
rooms_sale_med = {r: median(v) for r, v in tbilisi_sale_rooms.items()}
rs_labels = [f"{r} Bed" for r in sorted(rooms_sale_med)]
rs_vals   = [rooms_sale_med[r] for r in sorted(rooms_sale_med)]

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(rs_labels, rs_vals, color=BRAND_BLUE, width=0.5)
ax.bar_label(bars, labels=[f"${v:,.0f}" for v in rs_vals], padding=4, fontsize=9)
ax.set_title("Tbilisi Apartments — Median Sale Price by Bedroom Count  (USD)", fontsize=13, fontweight="bold", pad=12)
ax.set_ylabel("USD")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${int(x):,}"))
save(fig, "06_tbilisi_sale_price_by_rooms.png")

# ── Chart 7: Tbilisi — Median Monthly Rent by Number of Bedrooms ─────────────
rooms_rent_med = {r: median(v) for r, v in tbilisi_rent_rooms.items()}
rr_labels = [f"{r} Bed" for r in sorted(rooms_rent_med)]
rr_vals   = [rooms_rent_med[r] for r in sorted(rooms_rent_med)]

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(rr_labels, rr_vals, color=BRAND_GREEN, width=0.5)
ax.bar_label(bars, labels=[f"${v:,.0f}" for v in rr_vals], padding=4, fontsize=9)
ax.set_title("Tbilisi Apartments — Median Monthly Rent by Bedroom Count  (USD)", fontsize=13, fontweight="bold", pad=12)
ax.set_ylabel("USD / month")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${int(x):,}"))
save(fig, "07_tbilisi_rent_by_rooms.png")

# ── Chart 8: Tbilisi — Sale Price Distribution ────────────────────────────────
band_order = ["<$50k", "$50k–100k", "$100k–200k", "$200k–500k", ">$500k"]
band_vals  = [tbilisi_sale_bands.get(b, 0) for b in band_order]

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(band_order, band_vals, color=BRAND_BLUE, width=0.6)
ax.bar_label(bars, labels=[f"{v:,}" for v in band_vals], padding=4, fontsize=9)
ax.set_title("Tbilisi Apartments — Sale Price Distribution", fontsize=14, fontweight="bold", pad=12)
ax.set_ylabel("Number of Listings")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
save(fig, "08_tbilisi_sale_price_distribution.png")

# ── Chart 9: Tbilisi — Rent Price Distribution ───────────────────────────────
rent_band_order = ["<$300", "$300–500", "$500–800", "$800–1,500", ">$1,500"]
rent_band_vals  = [tbilisi_rent_bands.get(b, 0) for b in rent_band_order]

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(rent_band_order, rent_band_vals, color=BRAND_GREEN, width=0.6)
ax.bar_label(bars, labels=[f"{v:,}" for v in rent_band_vals], padding=4, fontsize=9)
ax.set_title("Tbilisi Apartments — Monthly Rent Distribution", fontsize=14, fontweight="bold", pad=12)
ax.set_ylabel("Number of Listings")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
save(fig, "09_tbilisi_rent_distribution.png")

# ── Chart 10: Seller Type Mix ─────────────────────────────────────────────────
seller_order = ["Agency", "Broker", "Private Owner", "Developer"]
s_sale  = [seller_deal[s]["1"] for s in seller_order]
s_rent  = [seller_deal[s]["2"] for s in seller_order]
s_daily = [seller_deal[s]["7"] for s in seller_order]

x = np.arange(len(seller_order))
w = 0.25
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(x - w, s_sale,  w, label="For Sale",   color=BRAND_BLUE)
ax.bar(x,     s_rent,  w, label="For Rent",   color=BRAND_GREEN)
ax.bar(x + w, s_daily, w, label="Daily Rent", color=BRAND_ORANGE)
ax.set_xticks(x); ax.set_xticklabels(seller_order)
ax.set_title("Listings by Seller Type and Deal Category", fontsize=14, fontweight="bold", pad=12)
ax.set_ylabel("Number of Listings")
ax.legend()
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
save(fig, "10_seller_type_by_deal.png")

# ── Chart 11: Batumi — Median Monthly Rent by District ───────────────────────
batumi_dist_labels_en = {
    "ძველი ბათუმის უბანი": "Old Batumi",
    "რუსთაველის უბანი": "Rustaveli",
    "ბაგრატიონის უბანი": "Bagrationi",
    "აეროპორტის უბანი": "Airport District",
    "ხიმშიაშვილის უბანი": "Khimshiashvili",
    "ჯავახიშვილის უბანი": "Javakhishvili",
    "აღმაშენებლის უბანი": "Aghmashenebeli",
    "თამარის დასახლება": "Tamari Settlement",
}
bat_med = {d: median(v) for d, v in batumi_dist_rent.items() if len(v) >= 30 and d}
bat_sorted = sorted(bat_med.items(), key=lambda x: -x[1])
bat_labels = [batumi_dist_labels_en.get(d, d) for d, _ in bat_sorted]
bat_vals   = [v for _, v in bat_sorted]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(bat_labels, bat_vals, color=BRAND_ORANGE, width=0.6)
ax.bar_label(bars, labels=[f"${v:,.0f}" for v in bat_vals], padding=4, fontsize=9)
ax.set_title("Batumi — Median Monthly Rent by District  (USD)", fontsize=14, fontweight="bold", pad=12)
ax.set_ylabel("USD / month")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${int(x):,}"))
plt.xticks(rotation=15, ha="right")
save(fig, "11_batumi_rent_by_district.png")

# ── Chart 12: Rental Yield Estimate by Tbilisi District ──────────────────────
# Gross yield = (median annual rent) / (median sale price per sqm * median area)
# Use avg apartment size ~67 sqm as proxy
AVG_AREA = 67
yields = {}
for d in dist_sale_med:
    en = dist_labels_en.get(d, d)
    if d in dist_rent_med:
        annual_rent  = dist_rent_med[d] * 12
        implied_price = dist_sale_med[d] * AVG_AREA
        yields[en] = round(annual_rent / implied_price * 100, 2)

yield_sorted = sorted(yields.items(), key=lambda x: -x[1])
y_labels = [y[0] for y in yield_sorted]
y_vals   = [y[1] for y in yield_sorted]

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(y_labels, y_vals, color=BRAND_PURPLE, width=0.6)
ax.bar_label(bars, labels=[f"{v:.1f}%" for v in y_vals], padding=4, fontsize=9)
ax.set_title("Tbilisi Districts — Estimated Gross Rental Yield  (%)", fontsize=14, fontweight="bold", pad=12)
ax.set_ylabel("Annual Gross Yield (%)")
ax.axhline(y=sum(y_vals)/len(y_vals), color="red", linestyle="--", alpha=0.6, label=f"Average: {sum(y_vals)/len(y_vals):.1f}%")
ax.legend()
plt.xticks(rotation=15, ha="right")
save(fig, "12_tbilisi_rental_yield_by_district.png")

print(f"\nAll charts saved to {CHARTS_DIR}")
