"""Generates the S&P 500 seed from arkad's CIK list and a local EDGAR bulk dump.

Reads 100 CIKs from arkad's `SP500_CIKS` constant. For each CIK it reads the EDGAR
`submissions` and `companyfacts` files and writes the same data to `fixtures/sp500.cypher` and
`fixtures/sp500.sql`. It then derives the rows that the three filing questions must return for
these companies, straight from the EDGAR files, and merges them into each `expected.json`.

Run it from the repo root:

    uv run python scripts/generate_sp500_seed.py --arkad ../arkad --edgar ../data
"""

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
QUERIES = ROOT / "queries"

COMPANY_COUNT = 100
YEAR = 2024
REGULAR_FORMS = ("10-K", "10-Q")

SOURCE = "SEC-EDGAR"
VERIFIABILITY = "Verified"

ARKAD_CIK_FILE = "sec/tests/pipeline_coverage/constants.rs"
"""File in arkad that holds the `SP500_CIKS` and `MUST_PASS_CIKS` constants."""

ALWAYS_INCLUDED = (
    "320193",  # Apple
    "789019",  # Microsoft
    "1067983",  # Berkshire Hathaway
    "1652044",  # Alphabet
    "1045810",  # NVIDIA
    "1326801",  # Meta Platforms
    "200406",  # Johnson & Johnson
    "19617",  # JPMorgan Chase, a known gap in arkad: no `OperatingIncomeLoss`
    "34088",  # Exxon Mobil, a known gap in arkad: no `OperatingIncomeLoss`
    "1018724",  # Amazon, a known gap in arkad: no bare `Liabilities`
)
"""arkad's must-pass companies and its three known gaps. The rest is an even sample."""

CONCEPT_TAGS: dict[str, tuple[str, ...]] = {
    "Assets": ("Assets",),
    "Liabilities": ("Liabilities",),
    "Equity": (
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ),
    "Revenue": (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ),
    "NetIncome": ("NetIncomeLoss",),
}
"""US GAAP tags per concept, in arkad's order. The first tag is `Exact`, the rest `Synonym`."""

EXCHANGE_MICS: dict[str, tuple[str, str]] = {
    "NYSE": ("XNYS", "New York Stock Exchange"),
    "Nasdaq": ("XNAS", "Nasdaq"),
    "CBOE": ("BATS", "Cboe BZX U.S. Equities Exchange"),
}
"""EDGAR exchange names mapped to ISO 10383 MIC and name. `OTC` is no exchange, so it is absent."""

EDGAR_COUNTRIES: dict[str, str] = {
    "A1": "CA",
    "L2": "IE",
    "U0": "SG",
    "V8": "CH",
    "X0": "GB",
}
"""EDGAR location codes outside the US, mapped to ISO 3166 alpha-2."""


@dataclass(frozen=True)
class Listing:
    """A ticker of a company on one exchange.

    Attributes:
        mic: The ISO 10383 code of the exchange.
        ticker: The ticker symbol.
    """

    mic: str
    ticker: str


@dataclass(frozen=True)
class Filing:
    """A 10-K or 10-Q with a period end in the seed year.

    Attributes:
        accession: The EDGAR accession number.
        form: The form type, `10-K` or `10-Q`.
        filed_date: The date the SEC received the filing.
        period_end: The last day of the reported period.
        period_key: The key of the `Period` node the filing covers.
        concepts: The concepts the filing reports, mapped to the confidence of the match.
    """

    accession: str
    form: str
    filed_date: str
    period_end: str
    period_key: str
    concepts: dict[str, str]


@dataclass(frozen=True)
class Company:
    """An SEC filer with the data the seed holds for it.

    Attributes:
        cik: The CIK, padded with zeros to 10 digits.
        name: The registered name in EDGAR.
        country: The ISO 3166 alpha-2 code of the business address.
        first_filed: The date of the oldest filing in EDGAR.
        sic: The SIC code and its description.
        listings: The tickers per exchange.
        filings: The filings of the seed year.
    """

    cik: str
    name: str
    country: str
    first_filed: str
    sic: tuple[str, str]
    listings: tuple[Listing, ...]
    filings: tuple[Filing, ...]

    @property
    def company_id(self) -> str:
        """Returns the company id. EDGAR gives no LEI, so the CIK is the fallback."""
        return f"CIK:{self.cik}"


def main() -> None:
    """Reads the sources, then writes both seed files and the expected rows."""
    args = parse_args()
    companies = [read_company(cik, args.edgar) for cik in select_ciks(args.arkad)]
    (FIXTURES / "sp500.cypher").write_text(cypher_seed(companies, args.as_of))
    (FIXTURES / "sp500.sql").write_text(sql_seed(companies, args.as_of))
    write_expected_rows(companies)
    filing_count = sum(len(company.filings) for company in companies)
    print(f"Wrote {len(companies)} companies and {filing_count} filings.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arkad", type=Path, default=ROOT.parent / "arkad", help="arkad clone")
    parser.add_argument(
        "--edgar",
        type=Path,
        default=ROOT.parent / "data",
        help="folder with the EDGAR `submissions` and `companyfacts` bulk files",
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date(2025, 12, 4),
        help="date of the EDGAR dump, used as `as_of` and `observed_at` of each claim",
    )
    return parser.parse_args()


def select_ciks(arkad: Path) -> list[str]:
    """Returns the CIKs of the seed: the always-included ones, then an even sample of the rest."""
    source = (arkad / ARKAD_CIK_FILE).read_text()
    block = source[source.index("SP500_CIKS") :]
    listed: list[str] = re.findall(r'^\s+"(\d+)",', block, flags=re.MULTILINE)
    candidates = [cik for cik in listed if cik != "9999999999" and cik not in ALWAYS_INCLUDED]
    sample_size = COMPANY_COUNT - len(ALWAYS_INCLUDED)
    step = len(candidates) / sample_size
    sample = [candidates[int(index * step)] for index in range(sample_size)]
    return [*ALWAYS_INCLUDED, *sample]


def read_company(cik: str, edgar: Path) -> Company:
    padded_cik = cik.zfill(10)
    submissions = json.loads((edgar / "submissions" / f"CIK{padded_cik}.json").read_text())
    facts = json.loads((edgar / "companyfacts" / f"CIK{padded_cik}.json").read_text())
    reported_tags = tags_by_filing(facts)
    filings = [
        filing
        for page in filing_pages(submissions, edgar)
        for filing in filings_of_year(page, reported_tags)
    ]
    listings = sorted(
        {
            Listing(mic=EXCHANGE_MICS[exchange][0], ticker=ticker)
            for ticker, exchange in zip(
                submissions["tickers"], submissions["exchanges"], strict=True
            )
            if exchange in EXCHANGE_MICS
        },
        key=lambda listing: (listing.mic, listing.ticker),
    )
    return Company(
        cik=padded_cik,
        name=submissions["name"],
        country=country(submissions),
        first_filed=first_filed(submissions),
        sic=(submissions["sic"], submissions["sicDescription"]),
        listings=tuple(listings),
        filings=tuple(sorted(filings, key=lambda filing: filing.period_end)),
    )


def filing_pages(submissions: dict[str, Any], edgar: Path) -> list[dict[str, list[str]]]:
    """Returns the filing lists of a company that can hold a filing of the seed year.

    EDGAR keeps the newest 1000 filings in the main file and moves older ones to extra files. A
    bank files thousands of prospectuses per year, so its 10-Qs sit in the extra files.
    """
    pages = [submissions["filings"]["recent"]]
    for older in submissions["filings"].get("files", []):
        if older["filingTo"] >= f"{YEAR}-01-01":
            pages.append(json.loads((edgar / "submissions" / older["name"]).read_text()))
    return pages


def filings_of_year(
    page: dict[str, list[str]], reported_tags: dict[tuple[str, str], set[str]]
) -> list[Filing]:
    return [
        Filing(
            accession=accession,
            form=form,
            filed_date=filed_date,
            period_end=period_end,
            period_key=period_key(form, period_end),
            concepts=resolved_concepts(reported_tags.get((accession, period_end), set())),
        )
        for accession, form, filed_date, period_end in zip(
            page["accessionNumber"],
            page["form"],
            page["filingDate"],
            page["reportDate"],
            strict=True,
        )
        if form in REGULAR_FORMS and period_end.startswith(str(YEAR))
    ]


def tags_by_filing(facts: dict[str, Any]) -> dict[tuple[str, str], set[str]]:
    """Returns the US GAAP tags per filing and period end.

    A filing also repeats the values of earlier periods for comparison. Only a value for the
    period end of the filing itself counts as reported.
    """
    tags: dict[tuple[str, str], set[str]] = {}
    for tag, fact in facts["facts"].get("us-gaap", {}).items():
        for values in fact["units"].values():
            for value in values:
                tags.setdefault((value["accn"], value["end"]), set()).add(tag)
    return tags


def resolved_concepts(tags: set[str]) -> dict[str, str]:
    concepts: dict[str, str] = {}
    for concept, candidates in CONCEPT_TAGS.items():
        for position, tag in enumerate(candidates):
            if tag in tags:
                concepts[concept] = "Exact" if position == 0 else "Synonym"
                break
    return concepts


def period_key(form: str, period_end: str) -> str:
    """Returns the calendar period that holds the period end of the filing.

    The `Period` nodes are calendar periods. A fiscal year that ends in September maps to the
    fiscal year of that calendar year, and its quarters map to the calendar quarter they end in.
    """
    if form == "10-K":
        return f"FY{YEAR}"
    quarter = (date.fromisoformat(period_end).month - 1) // 3 + 1
    return f"Q{quarter}-{YEAR}"


def country(submissions: dict[str, Any]) -> str:
    address = submissions["addresses"]["business"]
    code = (
        address.get("stateOrCountry")
        or address.get("countryCode")
        or submissions["stateOfIncorporation"]
    )
    # EDGAR codes a US state as two letters and every other location as a letter and a digit.
    return "US" if code.isalpha() else EDGAR_COUNTRIES[code]


def first_filed(submissions: dict[str, Any]) -> str:
    dates = list(submissions["filings"]["recent"]["filingDate"])
    dates += [older["filingFrom"] for older in submissions["filings"].get("files", [])]
    return min(dates)


def quoted(value: str, escape: str) -> str:
    return "'" + value.replace("'", escape) + "'"


def cypher_map(row: dict[str, str]) -> str:
    return "{" + ", ".join(f"{key}: {quoted(value, "\\'")}" for key, value in row.items()) + "}"


def cypher_rows(rows: list[dict[str, str]]) -> str:
    return "UNWIND [\n" + ",\n".join(f"  {cypher_map(row)}" for row in rows) + "\n] AS row\n"


def cypher_seed(companies: list[Company], as_of: date) -> str:
    envelope = (
        f"source: '{SOURCE}', as_of: date('{as_of}'), observed_at: date('{as_of}'), "
        f"verifiability: '{VERIFIABILITY}'"
    )
    statements = [
        "// S&P 500 seed. Real data from SEC EDGAR. fixtures/sp500.sql holds the same data.\n"
        "// Generated by scripts/generate_sp500_seed.py. Do not edit this file by hand.\n"
        "// Load fixtures/seed.cypher first: it creates the periods, concepts, and form types.\n",
        cypher_rows(
            [
                {
                    "id": company.company_id,
                    "name": company.name,
                    "country": company.country,
                    "cik": company.cik,
                    "first": company.first_filed,
                }
                for company in companies
            ]
        )
        + "MATCH (r:Regulator {code: 'SEC'})\n"
        "CREATE (c:Company {company_id: row.id, name: row.name, country: row.country,"
        " status: 'active'})\n"
        "CREATE (i:Identifier {scheme: 'CIK', value: row.cik})\n"
        "CREATE (c)-[:HAS_IDENTIFIER {since: date(row.first), status: 'active',"
        " primary: true}]->(i)\n"
        "CREATE (c)-[:FILES_WITH {first_filed: date(row.first)}]->(r);\n",
        cypher_rows([{"mic": mic, "name": name} for mic, name in exchanges(companies)])
        + "MERGE (e:Exchange {mic: row.mic})\nON CREATE SET e.name = row.name;\n",
        cypher_rows([{"code": code, "name": name} for code, name in industries(companies)])
        + "MERGE (i:Industry {scheme: 'SIC', code: row.code})\nON CREATE SET i.name = row.name;\n",
        cypher_rows(
            [
                {"company": company.company_id, "mic": listing.mic, "ticker": listing.ticker}
                for company in companies
                for listing in company.listings
            ]
        )
        + "MATCH (c:Company {company_id: row.company}), (e:Exchange {mic: row.mic})\n"
        f"CREATE (c)-[:LISTED_ON {{ticker: row.ticker, {envelope}}}]->(e);\n",
        cypher_rows(
            [{"company": company.company_id, "code": company.sic[0]} for company in companies]
        )
        + "MATCH (c:Company {company_id: row.company}),"
        " (i:Industry {scheme: 'SIC', code: row.code})\n"
        f"CREATE (c)-[:IN_INDUSTRY {{{envelope}}}]->(i);\n",
        cypher_rows(
            [
                {
                    "company": company.company_id,
                    "id": filing.accession,
                    "form": filing.form,
                    "period": filing.period_key,
                    "filed": filing.filed_date,
                    "end": filing.period_end,
                }
                for company in companies
                for filing in company.filings
            ]
        )
        + "MATCH (c:Company {company_id: row.company}),\n"
        "      (r:Regulator {code: 'SEC'}),\n"
        "      (t:FormType {regulator: 'SEC', code: row.form}),\n"
        "      (p:Period {key: row.period})\n"
        "CREATE (f:Filing {regulator: 'SEC', native_id: row.id, form: row.form,\n"
        "                  filed_date: date(row.filed), period_end: date(row.end)})\n"
        "CREATE (c)-[:HAS_FILING]->(f)\n"
        "CREATE (f)-[:FILED_UNDER]->(r)\n"
        "CREATE (f)-[:OF_FORM]->(t)\n"
        "CREATE (f)-[:COVERS_PERIOD]->(p);\n",
        cypher_rows(
            [
                {"id": filing.accession, "element": concept, "confidence": confidence}
                for company in companies
                for filing in company.filings
                for concept, confidence in filing.concepts.items()
            ]
        )
        + "MATCH (f:Filing {regulator: 'SEC', native_id: row.id}),"
        " (k:Concept {element: row.element})\n"
        "CREATE (f)-[:REPORTS_CONCEPT {confidence: row.confidence}]->(k);\n",
    ]
    return "\n".join(statements)


def sql_insert(table: str, columns: str, rows: Sequence[tuple[str, ...]], suffix: str = "") -> str:
    values = ",\n".join(
        "    (" + ", ".join(quoted(value, "''") for value in row) + ")" for row in rows
    )
    return f"INSERT INTO {table} ({columns}) VALUES\n{values}{suffix};\n"


def sql_seed(companies: list[Company], as_of: date) -> str:
    envelope = (SOURCE, str(as_of), str(as_of), VERIFIABILITY)
    filings = [(company, filing) for company in companies for filing in company.filings]
    statements = [
        "-- S&P 500 seed. Real data from SEC EDGAR. fixtures/sp500.cypher holds the same data.\n"
        "-- Generated by scripts/generate_sp500_seed.py. Do not edit this file by hand.\n"
        "-- Load fixtures/seed.sql first: it creates the periods, concepts, and form types.\n",
        sql_insert(
            "company",
            "company_id, name, country, status",
            [
                (company.company_id, company.name, company.country, "active")
                for company in companies
            ],
        ),
        sql_insert("identifier", "scheme, value", [("CIK", company.cik) for company in companies]),
        sql_insert(
            "has_identifier",
            "company_id, scheme, value, since, status, is_primary",
            [
                (company.company_id, "CIK", company.cik, company.first_filed, "active", "true")
                for company in companies
            ],
        ),
        sql_insert(
            "files_with",
            "company_id, regulator, first_filed",
            [(company.company_id, "SEC", company.first_filed) for company in companies],
        ),
        sql_insert("exchange", "mic, name", exchanges(companies), " ON CONFLICT DO NOTHING"),
        sql_insert(
            "industry",
            "scheme, code, name",
            [("SIC", code, name) for code, name in industries(companies)],
            " ON CONFLICT DO NOTHING",
        ),
        sql_insert(
            "listed_on",
            "company_id, mic, ticker, source, as_of, observed_at, verifiability",
            [
                (company.company_id, listing.mic, listing.ticker, *envelope)
                for company in companies
                for listing in company.listings
            ],
        ),
        sql_insert(
            "in_industry",
            "company_id, scheme, code, source, as_of, observed_at, verifiability",
            [(company.company_id, "SIC", company.sic[0], *envelope) for company in companies],
        ),
        sql_insert(
            "filing",
            "regulator, native_id, form, filed_date, period_end",
            [
                ("SEC", filing.accession, filing.form, filing.filed_date, filing.period_end)
                for _, filing in filings
            ],
        ),
        sql_insert(
            "has_filing",
            "company_id, regulator, native_id",
            [(company.company_id, "SEC", filing.accession) for company, filing in filings],
        ),
        sql_insert(
            "covers_period",
            "regulator, native_id, period_key",
            [("SEC", filing.accession, filing.period_key) for _, filing in filings],
        ),
        sql_insert(
            "reports_concept",
            "regulator, native_id, element, confidence",
            [
                ("SEC", filing.accession, concept, confidence)
                for _, filing in filings
                for concept, confidence in filing.concepts.items()
            ],
        ),
    ]
    return "\n".join(statements)


def exchanges(companies: list[Company]) -> list[tuple[str, str]]:
    used = {listing.mic for company in companies for listing in company.listings}
    return sorted((mic, name) for mic, name in EXCHANGE_MICS.values() if mic in used)


def industries(companies: list[Company]) -> list[tuple[str, str]]:
    return sorted({company.sic for company in companies})


def write_expected_rows(companies: list[Company]) -> None:
    """Merges the rows for the S&P 500 companies into the expected rows of the filing questions.

    The rows come from the EDGAR data in memory, not from a query on a store. Rows for the
    hand-written seed stay as they are.
    """
    company_ids = {company.company_id for company in companies}
    accessions = {filing.accession for company in companies for filing in company.filings}
    covered = {
        company.company_id: {filing.period_key for filing in company.filings}
        for company in companies
    }
    reports = [f"Q1-{YEAR}", f"Q2-{YEAR}", f"Q3-{YEAR}", f"FY{YEAR}"]

    merge_expected(
        "missing_q3_2024",
        "company_id",
        company_ids,
        [
            {"company_id": company_id}
            for company_id, keys in covered.items()
            if f"Q3-{YEAR}" not in keys
        ],
    )
    merge_expected(
        "incomplete_fy2024",
        "company_id",
        company_ids,
        [
            {"company_id": company_id, "missing_period": key}
            for company_id, keys in covered.items()
            for key in reports
            if key not in keys
        ],
    )
    merge_expected(
        "filing_missing_concepts",
        "native_id",
        accessions,
        [
            {"native_id": filing.accession, "element": concept}
            for company in companies
            for filing in company.filings
            for concept in CONCEPT_TAGS
            if concept not in filing.concepts
        ],
    )


def merge_expected(
    query: str, key: str, generated_keys: set[str], rows: list[dict[str, str]]
) -> None:
    path = QUERIES / query / "expected.json"
    kept = [row for row in json.loads(path.read_text()) if row[key] not in generated_keys]
    merged = kept + sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))
    lines = ",\n".join(f"  {json.dumps(row)}" for row in merged)
    path.write_text(f"[\n{lines}\n]\n")


if __name__ == "__main__":
    main()
