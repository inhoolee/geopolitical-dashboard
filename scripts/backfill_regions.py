"""Backfill region_code in dim_country and fact_incident."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.db import get_connection

# Comprehensive ISO3 → region_code mapping for countries missing assignment
_REGION_UPDATES: dict[str, str] = {
    # EU / Eurasia
    "ALB": "EU_EUR", "AND": "EU_EUR", "AUT": "EU_EUR", "BEL": "EU_EUR",
    "BGR": "EU_EUR", "BIH": "EU_EUR", "CHE": "EU_EUR", "CYP": "EU_EUR",
    "CZE": "EU_EUR", "DNK": "EU_EUR", "EST": "EU_EUR", "ESP": "EU_EUR",
    "FRO": "EU_EUR", "GGY": "EU_EUR", "GIB": "EU_EUR", "GRC": "EU_EUR",
    "GRL": "EU_EUR", "HRV": "EU_EUR", "HUN": "EU_EUR", "IMN": "EU_EUR",
    "IRL": "EU_EUR", "ISL": "EU_EUR", "ITA": "EU_EUR", "JEY": "EU_EUR",
    "KGZ": "EU_EUR", "LIE": "EU_EUR", "LTU": "EU_EUR", "LUX": "EU_EUR",
    "LVA": "EU_EUR", "MCO": "EU_EUR", "MKD": "EU_EUR", "MLT": "EU_EUR",
    "MNE": "EU_EUR", "NLD": "EU_EUR", "PRT": "EU_EUR", "ROU": "EU_EUR",
    "SJM": "EU_EUR", "SMR": "EU_EUR", "SVK": "EU_EUR", "SVN": "EU_EUR",
    "TJK": "EU_EUR", "TKM": "EU_EUR", "VAT": "EU_EUR",
    "ALA": "EU_EUR",  # Åland Islands
    # Americas
    "ABW": "AME", "AIA": "AME", "ATG": "AME", "BES": "AME", "BHS": "AME",
    "BLM": "AME", "BLZ": "AME", "BMU": "AME", "BRB": "AME", "CRI": "AME",
    "CUW": "AME", "CYM": "AME", "DMA": "AME", "DOM": "AME", "FLK": "AME",
    "GLP": "AME", "GRD": "AME", "GUF": "AME", "GUM": "AME", "GUY": "AME",
    "JAM": "AME", "KNA": "AME", "LCA": "AME", "MAF": "AME", "MNP": "AME",
    "MSR": "AME", "MTQ": "AME", "PAN": "AME", "PRI": "AME", "PRY": "AME",
    "SPM": "AME", "SUR": "AME", "SXM": "AME", "TCA": "AME", "TTO": "AME",
    "UMI": "AME", "URY": "AME", "VCT": "AME", "VGB": "AME", "VIR": "AME",
    # Sub-Saharan Africa
    "AGO": "SSA", "BDI": "SSA", "BEN": "SSA", "BTN": "SCA",
    "BWA": "SSA", "CIV": "SSA", "COM": "SSA", "CPV": "SSA",
    "ERI": "SSA", "GAB": "SSA", "GHA": "SSA", "GMB": "SSA",
    "GNQ": "SSA", "LSO": "SSA", "LBR": "SSA", "MDG": "SSA",
    "MRT": "SSA", "MUS": "SSA", "MWI": "SSA", "MYT": "SSA",
    "NAM": "SSA", "REU": "SSA", "SEN": "SSA", "SHN": "SSA",
    "SLE": "SSA", "STP": "SSA", "SUR": "AME",  # Suriname already AME
    "SWZ": "SSA", "SYC": "SSA", "TGO": "SSA", "ZMB": "SSA",
    # MENA
    "DJI": "MENA", "ESH": "MENA", "MDV": "SCA",  # Maldives → SCA
    # South & Central Asia
    "BTN": "SCA", "KHM": "EAP", "KGZ": "EU_EUR",  # Kyrgyzstan → EU_EUR (Central Asia)
    # East Asia & Pacific
    "ASM": "EAP", "BRN": "EAP", "CCK": "EAP", "COK": "EAP",
    "CXR": "EAP", "FJI": "EAP", "FSM": "EAP", "HKG": "EAP",
    "IOT": "EAP", "KHM": "EAP", "KIR": "EAP", "LAO": "EAP",
    "MAC": "EAP", "MDV": "SCA", "MHL": "EAP", "MNG": "EAP",
    "NCL": "EAP", "NFK": "EAP", "NIU": "EAP", "NRU": "EAP",
    "PCN": "EAP", "PLW": "EAP", "PYF": "EAP", "SLB": "EAP",
    "TKL": "EAP", "TLS": "EAP", "TON": "EAP", "TUV": "EAP",
    "VUT": "EAP", "WLF": "EAP", "WSM": "EAP",
    # Global / unassigned territories
    "ATA": "GLO", "ATF": "GLO", "BVT": "GLO",
    "HMD": "GLO", "SGS": "GLO",
}

# Some keys appear in both AME and SSA above — fix Suriname (already handles via order,
# but let's ensure correct final value by being explicit):
_REGION_UPDATES["SUR"] = "AME"
_REGION_UPDATES["BTN"] = "SCA"
_REGION_UPDATES["MDV"] = "SCA"
_REGION_UPDATES["KGZ"] = "EU_EUR"  # Central Asia → EU_EUR per project convention


def main():
    conn = get_connection()

    # 1. Update dim_country
    updates = [(v, k) for k, v in _REGION_UPDATES.items()]
    conn.executemany(
        "UPDATE dim_country SET region_code = ? WHERE iso3 = ? AND region_code IS NULL",
        updates,
    )
    conn.commit()

    n = conn.execute("SELECT COUNT(*) FROM dim_country WHERE region_code IS NULL").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM dim_country").fetchone()[0]
    print(f"dim_country: {total - n}/{total} have region_code ({n} still NULL)")

    # 2. Backfill fact_incident.region_code from dim_country
    conn.execute("""
        UPDATE fact_incident
        SET region_code = (
            SELECT region_code FROM dim_country
            WHERE iso3 = fact_incident.country_iso3
        )
        WHERE region_code IS NULL
    """)
    conn.commit()

    ri = conn.execute(
        "SELECT COUNT(*) FROM fact_incident WHERE region_code IS NOT NULL"
    ).fetchone()[0]
    total_fi = conn.execute("SELECT COUNT(*) FROM fact_incident").fetchone()[0]
    print(f"fact_incident: {ri}/{total_fi} have region_code")

    # 3. Verify views work (they recompute on query)
    rw = conn.execute("SELECT COUNT(*) FROM country_week_agg").fetchone()[0]
    rm = conn.execute("SELECT COUNT(*) FROM country_month_agg").fetchone()[0]
    print(f"country_week_agg (view): {rw} rows | country_month_agg (view): {rm} rows")
    print("Done.")


if __name__ == "__main__":
    main()
