"""Country name / ISO-2 / ISO-3 lookup utilities using pycountry."""

import logging
from functools import lru_cache

import pycountry

logger = logging.getLogger(__name__)

# Manual overrides for names not matched by pycountry
_OVERRIDES: dict[str, str] = {
    "russia": "RUS",
    "iran": "IRN",
    "syria": "SYR",
    "venezuela": "VEN",
    "south korea": "KOR",
    "north korea": "PRK",
    "dprk": "PRK",
    "democratic republic of congo": "COD",
    "dr congo": "COD",
    "drc": "COD",
    "ivory coast": "CIV",
    "cote d'ivoire": "CIV",
    "taiwan": "TWN",
    "palestine": "PSE",
    "west bank and gaza": "PSE",
    "eu": "EUU",
    "european union": "EUU",
    "nato": "NAT",
    "un": "UNO",
    "united nations": "UNO",
    # UCDP-specific country name variants
    "bosnia-herzegovina": "BIH",
    "bosnia and herzegovina": "BIH",
    "south vietnam": "VNM",
    "north vietnam": "VNM",
    "democratic republic of vietnam": "VNM",
    "republic of vietnam": "VNM",
    "burma/myanmar": "MMR",
    "dr congo (zaire)": "COD",
    "republic of congo": "COG",
    "trinidad and tobago": "TTO",
    "united arab emirates": "ARE",
    "south sudan": "SSD",
    "central african republic": "CAF",
    "cape verde": "CPV",
    "guinea-bissau": "GNB",
    "sao tome and principe": "STP",
    "equatorial guinea": "GNQ",
    "western sahara": "ESH",
    "turkey": "TUR",
    "bailiwick of jersey": "JEY",
    "bailiwick of guernsey": "GGY",
    "caribbean netherlands": "BES",
    "akrotiri and dhekelia": "CYP",
    "czech republic": "CZE",
    "czechoslovakia": "CZE",
    "east timor": "TLS",
    "timor-leste": "TLS",
    "micronesia": "FSM",
}


@lru_cache(maxsize=512)
def name_to_iso3(name: str) -> str | None:
    """Resolve a country name string to ISO 3166-1 alpha-3."""
    if not name:
        return None
    key = name.strip().lower()
    if key in _OVERRIDES:
        return _OVERRIDES[key]
    # Try exact lookup
    try:
        country = pycountry.countries.lookup(name)
        return country.alpha_3
    except LookupError:
        pass
    # Try fuzzy search
    try:
        results = pycountry.countries.search_fuzzy(name)
        if results:
            return results[0].alpha_3
    except LookupError:
        pass
    logger.debug("Could not resolve ISO3 for: %s", name)
    return None


@lru_cache(maxsize=256)
def iso2_to_iso3(iso2: str) -> str | None:
    """Convert ISO 3166-1 alpha-2 to alpha-3."""
    try:
        country = pycountry.countries.get(alpha_2=iso2.upper())
        return country.alpha_3 if country else None
    except Exception:
        return None


# WB uses alpha-2 but returns some non-standard codes
_WB_SPECIAL: dict[str, str] = {
    "KV": "XKX",  # Kosovo
    "XK": "XKX",
}


def wb_code_to_iso3(wb_code: str) -> str | None:
    """Resolve a World Bank country code to ISO3."""
    if not wb_code:
        return None
    if wb_code in _WB_SPECIAL:
        return _WB_SPECIAL[wb_code]
    return iso2_to_iso3(wb_code)


def iso3_to_name(iso3: str) -> str | None:
    """Resolve ISO3 to English country name."""
    try:
        country = pycountry.countries.get(alpha_3=iso3.upper())
        return country.name if country else None
    except Exception:
        return None
