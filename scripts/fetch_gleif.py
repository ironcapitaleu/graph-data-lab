"""Fetches the GLEIF record of each S&P 500 company of the seed.

GLEIF does not know the CIK, so no key connects an EDGAR company to its LEI record. The script
searches the GLEIF API by name. It accepts a record only if the name matches and a second,
independent fact matches too: the jurisdiction of incorporation or the headquarters. If no
record or more than one record passes, the company gets no LEI.

The result goes to `fixtures/gleif_records.json`. The seed generator reads that file, so it
needs no network.

Run it from the repo root:

    uv run python -m scripts.fetch_gleif --arkad ../arkad --edgar ../data
"""

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from scripts.generate_sp500_seed import EDGAR_COUNTRIES, FIXTURES, ROOT, select_ciks

API = "https://api.gleif.org/api/v1/lei-records"
OUTPUT = FIXTURES / "gleif_records.json"

SECONDS_BETWEEN_REQUESTS = 1.1
"""GLEIF allows 60 requests per minute."""

NAME_WORDS: dict[str, str] = {
    "INCORPORATED": "INC",
    "CORPORATION": "CORP",
    "COMPANY": "CO",
    "LIMITED": "LTD",
    "COMPANIES": "COS",
    "AND": "",
    "THE": "",
}
"""Words that EDGAR and GLEIF write in different ways, mapped to one form."""

LEGAL_SUFFIXES = frozenset({"", "INC", "CORP", "CO", "LTD", "COS", "PLC"})
"""Words that are left out of a search phrase."""

MAX_WORD_QUERIES = 3


def main() -> None:
    """Searches GLEIF for each company and writes the accepted records."""
    args = parse_args()
    matched: dict[str, dict[str, Any]] = {}
    unmatched: dict[str, str] = {}
    for cik in select_ciks(args.arkad):
        padded_cik = cik.zfill(10)
        path = args.edgar / "submissions" / f"CIK{padded_cik}.json"
        submissions = json.loads(path.read_text())
        accepted: list[dict[str, Any]] = []
        for query in search_queries(submissions["name"]):
            accepted = [
                evidence | record
                for record in search(query)
                if (evidence := match_evidence(submissions, record)) is not None
            ]
            time.sleep(SECONDS_BETWEEN_REQUESTS)
            if accepted:
                break
        if len(accepted) == 1:
            matched[padded_cik] = accepted[0]
        else:
            unmatched[padded_cik] = f"{submissions['name']}: {len(accepted)} records pass"
    result = {"source": API, "matched": matched, "unmatched": unmatched}
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Matched {len(matched)} companies, left {len(unmatched)} without an LEI.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arkad", type=Path, default=ROOT.parent / "arkad", help="arkad clone")
    parser.add_argument(
        "--edgar",
        type=Path,
        default=ROOT.parent / "data",
        help="folder with the EDGAR `submissions` bulk files",
    )
    return parser.parse_args()


def search_queries(edgar_name: str) -> list[str]:
    """Returns the phrases to search for, the most specific one first.

    GLEIF matches a phrase as written, so "MICROSOFT CORP" does not find "MICROSOFT
    CORPORATION". The first phrase is the name without its legal suffix. The next ones are its
    longest words, for a name that GLEIF writes with other punctuation or in another order.
    """
    words = [
        word
        for word in re.sub(
            r"[^A-Z0-9]+", " ", re.sub(r"/[A-Z]+/?", " ", edgar_name.upper())
        ).split()
        if NAME_WORDS.get(word, word) not in LEGAL_SUFFIXES
    ]
    by_length = sorted(set(words), key=lambda word: (-len(word), word))
    return list(dict.fromkeys([" ".join(words), *by_length[:MAX_WORD_QUERIES]]))


def search(phrase: str) -> list[dict[str, Any]]:
    """Returns the GLEIF records whose legal name holds the phrase."""
    query = urllib.parse.urlencode({"filter[entity.legalName]": phrase, "page[size]": "200"})
    request = urllib.request.Request(  # noqa: S310 - fixed https URL of the GLEIF API
        f"{API}?{query}", headers={"Accept": "application/vnd.api+json"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - see above
        return [record_of(item["attributes"]) for item in json.load(response)["data"]]


def record_of(attributes: dict[str, Any]) -> dict[str, Any]:
    entity, registration = attributes["entity"], attributes["registration"]
    headquarters = entity["headquartersAddress"]
    return {
        "lei": attributes["lei"],
        "legal_name": entity["legalName"]["name"],
        "other_names": [name["name"] for name in entity["otherNames"]],
        "jurisdiction": entity["jurisdiction"],
        "entity_status": entity["status"],
        "registration_status": registration["status"],
        "initial_registration": registration["initialRegistrationDate"][:10],
        "last_update": registration["lastUpdateDate"][:10],
        "next_renewal": registration["nextRenewalDate"][:10],
        "hq_city": headquarters["city"],
        "hq_postal_code": headquarters["postalCode"],
        "hq_country": headquarters["country"],
    }


def match_evidence(submissions: dict[str, Any], record: dict[str, Any]) -> dict[str, Any] | None:
    """Returns the facts on which the record matches the EDGAR company, or `None`.

    A match needs a valid LEI, an active entity, the same name, and one more fact that EDGAR and
    GLEIF hold independently of each other.
    """
    if not valid_lei(record["lei"]) or record["entity_status"] != "ACTIVE":
        return None
    edgar_words = name_words(submissions["name"])
    gleif_names = [record["legal_name"], *record["other_names"]]
    if all(name_words(name) != edgar_words for name in gleif_names):
        return None
    address = submissions["addresses"]["business"]
    evidence = ["name"]
    if record["jurisdiction"] == jurisdiction(submissions["stateOfIncorporation"]):
        evidence.append("jurisdiction")
    if postal_prefix(record["hq_postal_code"]) == postal_prefix(address.get("zipCode")):
        evidence.append("hq_postal_code")
    elif (record["hq_city"] or "").upper() == (address.get("city") or "").upper():
        evidence.append("hq_city")
    return {"matched_on": evidence} if len(evidence) > 1 else None


def name_words(name: str) -> frozenset[str]:
    """Returns the words of a company name in one form, without order.

    EDGAR writes "SCHWAB CHARLES CORP" and "KEYCORP /NEW/". GLEIF writes "THE CHARLES SCHWAB
    CORPORATION". Order, case, punctuation, and the form of the legal suffix carry no identity.
    """
    without_state = re.sub(r"/[A-Z]+/?", " ", name.upper())
    words = re.sub(r"[^A-Z0-9]+", " ", without_state).split()
    return frozenset(NAME_WORDS.get(word, word) for word in words) - {""}


def jurisdiction(edgar_code: str | None) -> str | None:
    """Returns the ISO 3166 code that GLEIF uses for an EDGAR state or country code."""
    if not edgar_code:
        return None
    return f"US-{edgar_code}" if edgar_code.isalpha() else EDGAR_COUNTRIES.get(edgar_code)


def postal_prefix(postal_code: str | None) -> str | None:
    return postal_code[:5] if postal_code else None


def valid_lei(lei: str) -> bool:
    """Checks the two check digits of an LEI: ISO 17442, MOD 97-10 of ISO 7064."""
    if not re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}", lei):
        return False
    return int("".join(str(int(character, 36)) for character in lei)) % 97 == 1


if __name__ == "__main__":
    main()
