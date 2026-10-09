"""Generates the S&P 500 seed from arkad's CIK list and a local EDGAR bulk dump.

Reads 100 CIKs from arkad's `SP500_CIKS` constant. For each CIK it reads the EDGAR
`submissions` and `companyfacts` files and writes the same data to `fixtures/sp500.cypher` and
`fixtures/sp500.sql`. It then derives the rows that the filing questions must return for these
companies, straight from the EDGAR files, and merges them into each `expected.json`.

Each company gets its fiscal year 2024 as the SEC filings declare it. A filing states its fiscal
year and fiscal period, and its facts give the first and last day of that period.

Run it from the repo root:

    uv run python scripts/generate_sp500_seed.py --arkad ../arkad --edgar ../data
"""

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
QUERIES = ROOT / "queries"

COMPANY_COUNT = 100
FISCAL_YEAR = 2024
REGULAR_FORMS = ("10-K", "10-Q")

YEAR_LENGTH = range(350, 381)
"""Days in a fiscal year of 52 or 53 weeks, with some room."""

QUARTER_LENGTH = range(75, 106)
"""Days in a fiscal quarter of 12 to 14 weeks, with some room."""

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
    """A 10-K or 10-Q of fiscal year 2024.

    Attributes:
        accession: The EDGAR accession number.
        form: The form type, `10-K` or `10-Q`.
        filed_date: The date the SEC received the filing.
        period_end: The last day of the reported period.
        fiscal_year: The fiscal year the filing declares.
        fiscal_period: The fiscal period the filing declares: `FY`, `Q1`, `Q2`, or `Q3`.
        period_start: The first day of the reported period, from the facts. `None` if no fact
            gives a period of the expected length.
        concepts: The concepts the filing reports, mapped to the confidence of the match.
    """

    accession: str
    form: str
    filed_date: str
    period_end: str
    fiscal_year: int | None
    fiscal_period: str | None
    period_start: str | None
    concepts: dict[str, str]


@dataclass(frozen=True)
class FiscalQuarter:
    """A quarter of a fiscal year.

    Attributes:
        quarter: The number of the quarter, 1 to 4.
        start_date: The first day of the quarter.
        end_date: The last day of the quarter.
        filing: The 10-Q that reports on the quarter. `None` for the fourth quarter, and for a
            quarter whose 10-Q declares another fiscal period.
    """

    quarter: int
    start_date: str
    end_date: str
    filing: Filing | None

    @property
    def period_key(self) -> str:
        """Returns the key of the calendar quarter that holds the middle day of the quarter."""
        start = date.fromisoformat(self.start_date)
        middle = start + (date.fromisoformat(self.end_date) - start) / 2
        return f"Q{(middle.month - 1) // 3 + 1}-{middle.year}"


@dataclass(frozen=True)
class FiscalYear:
    """The fiscal year 2024 of a company, as its 10-K declares it.

    Attributes:
        start_date: The first day of the fiscal year.
        end_date: The last day of the fiscal year.
        filing: The 10-K that reports on the fiscal year.
        quarters: The four quarters, in order.
    """

    start_date: str
    end_date: str
    filing: Filing
    quarters: tuple[FiscalQuarter, ...]


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
        fiscal_year: The fiscal year 2024. `None` if no 10-K declares it.
        unresolved_filings: The filings that belong to the seed but report on no fiscal period
            of it. Such a filing declares another fiscal year than its dates say.
    """

    cik: str
    name: str
    country: str
    first_filed: str
    sic: tuple[str, str]
    listings: tuple[Listing, ...]
    fiscal_year: FiscalYear | None
    unresolved_filings: tuple[Filing, ...]

    @property
    def company_id(self) -> str:
        """Returns the company id. EDGAR gives no LEI, so the CIK is the fallback."""
        return f"CIK:{self.cik}"

    @property
    def resolved_filings(self) -> list[tuple[Filing, int | None]]:
        """Returns each filing that reports on a fiscal period, with its quarter or `None`."""
        if self.fiscal_year is None:
            return []
        quarterly = [
            (quarter.filing, quarter.quarter)
            for quarter in self.fiscal_year.quarters
            if quarter.filing is not None
        ]
        return [*quarterly, (self.fiscal_year.filing, None)]

    @property
    def filings(self) -> list[Filing]:
        """Returns all filings of the company in the seed."""
        return [*(filing for filing, _ in self.resolved_filings), *self.unresolved_filings]


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
    filings = read_filings(submissions, facts, edgar)
    fiscal_year = read_fiscal_year(filings)
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
        fiscal_year=fiscal_year,
        unresolved_filings=tuple(unresolved_filings(filings, fiscal_year)),
    )


def read_filings(submissions: dict[str, Any], facts: dict[str, Any], edgar: Path) -> list[Filing]:
    """Returns every 10-K and 10-Q of the company, with what its own facts declare."""
    tags: dict[tuple[str, str], set[str]] = {}
    focus: dict[tuple[str, str], tuple[int, str]] = {}
    starts: dict[tuple[str, str], set[str]] = {}
    for tag, fact in facts["facts"].get("us-gaap", {}).items():
        for values in fact["units"].values():
            for value in values:
                # A filing repeats the values of earlier periods for comparison. Only a value
                # for the period end of the filing itself describes the filing.
                key = (value["accn"], value["end"])
                tags.setdefault(key, set()).add(tag)
                if value.get("fy") and value.get("fp"):
                    focus[key] = (value["fy"], value["fp"])
                if "start" in value:
                    starts.setdefault(key, set()).add(value["start"])
    filings = []
    for page in filing_pages(submissions, edgar):
        for accession, form, filed_date, period_end in zip(
            page["accessionNumber"],
            page["form"],
            page["filingDate"],
            page["reportDate"],
            strict=True,
        ):
            if form not in REGULAR_FORMS:
                continue
            key = (accession, period_end)
            fiscal_year, fiscal_period = focus.get(key, (None, None))
            filings.append(
                Filing(
                    accession=accession,
                    form=form,
                    filed_date=filed_date,
                    period_end=period_end,
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                    period_start=period_start(
                        starts.get(key, set()),
                        period_end,
                        YEAR_LENGTH if form == "10-K" else QUARTER_LENGTH,
                    ),
                    concepts=resolved_concepts(tags.get(key, set())),
                )
            )
    return filings


def period_start(starts: set[str], period_end: str, length: range) -> str | None:
    """Returns the start date that gives a period of the expected length, if exactly one does.

    A 10-Q of the third quarter holds facts for three months and for nine months. Only the
    start of the three months is the start of the quarter.
    """
    end = date.fromisoformat(period_end)
    fitting = [start for start in starts if (end - date.fromisoformat(start)).days + 1 in length]
    return fitting[0] if len(fitting) == 1 else None


def read_fiscal_year(filings: list[Filing]) -> FiscalYear | None:
    """Builds the fiscal year 2024 from the filings that declare it.

    The 10-K gives the year. Each 10-Q gives one of the first three quarters. The fourth quarter
    has no filing of its own: it runs from the day after the third quarter to the end of the year.
    If a 10-Q is absent, its quarter fills the space between its neighbors.
    """
    declared = [filing for filing in filings if filing.fiscal_year == FISCAL_YEAR]
    annual = [filing for filing in declared if filing.form == "10-K" and filing.period_start]
    if len(annual) != 1 or annual[0].period_start is None:
        return None
    year_start, year_end = annual[0].period_start, annual[0].period_end
    quarterly = {
        int(filing.fiscal_period[1]): filing
        for filing in declared
        if filing.form == "10-Q"
        and filing.fiscal_period in ("Q1", "Q2", "Q3")
        and filing.period_start is not None
        and year_start <= filing.period_start < filing.period_end < year_end
    }
    quarters: list[FiscalQuarter] = []
    for number in (1, 2, 3, 4):
        filing = quarterly.get(number)
        following = quarterly.get(number + 1)
        if filing is not None and filing.period_start is not None:
            start, end = filing.period_start, filing.period_end
        else:
            start = next_day(quarters[-1].end_date) if quarters else year_start
            end = (
                previous_day(following.period_start)
                if following is not None and following.period_start is not None
                else year_end
            )
        quarters.append(
            FiscalQuarter(quarter=number, start_date=start, end_date=end, filing=filing)
        )
    return FiscalYear(
        start_date=year_start, end_date=year_end, filing=annual[0], quarters=tuple(quarters)
    )


def unresolved_filings(filings: list[Filing], fiscal_year: FiscalYear | None) -> list[Filing]:
    """Returns the filings that belong to fiscal year 2024 but report on no period of it.

    A filing belongs to the fiscal year if it declares the year, or if its period ends inside
    the year. It stays unresolved if the two disagree, or if the company has no fiscal year.
    """
    resolved = set()
    if fiscal_year is not None:
        resolved = {quarter.filing.accession for quarter in fiscal_year.quarters if quarter.filing}
        resolved.add(fiscal_year.filing.accession)
    return [
        filing
        for filing in filings
        if filing.accession not in resolved
        and (
            filing.fiscal_year == FISCAL_YEAR
            or (
                fiscal_year is not None
                and fiscal_year.start_date < filing.period_end <= fiscal_year.end_date
            )
        )
    ]


def next_day(day: str) -> str:
    return str(date.fromisoformat(day) + timedelta(days=1))


def previous_day(day: str) -> str:
    return str(date.fromisoformat(day) - timedelta(days=1))


def filing_pages(submissions: dict[str, Any], edgar: Path) -> list[dict[str, list[str]]]:
    """Returns the filing lists of a company that can hold a filing of the fiscal year.

    EDGAR keeps the newest 1000 filings in the main file and moves older ones to extra files. A
    bank files thousands of prospectuses per year, so its 10-Qs sit in the extra files.
    """
    pages = [submissions["filings"]["recent"]]
    for older in submissions["filings"].get("files", []):
        if older["filingTo"] >= f"{FISCAL_YEAR - 1}-01-01":
            pages.append(json.loads((edgar / "submissions" / older["name"]).read_text()))
    return pages


def resolved_concepts(tags: set[str]) -> dict[str, str]:
    concepts: dict[str, str] = {}
    for concept, candidates in CONCEPT_TAGS.items():
        for position, tag in enumerate(candidates):
            if tag in tags:
                concepts[concept] = "Exact" if position == 0 else "Synonym"
                break
    return concepts


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
    with_year = [(company, company.fiscal_year) for company in companies if company.fiscal_year]
    filing_create = (
        "CREATE (f:Filing {regulator: 'SEC', native_id: row.id, form: row.form,\n"
        "                  filed_date: date(row.filed), period_end: date(row.end)})\n"
        "CREATE (g)-[:HAS_FILING]->(f)\n"
        "CREATE (f)-[:OF_FORM]->(t)\n"
    )
    statements = [
        "// S&P 500 seed. Real data from SEC EDGAR. fixtures/sp500.sql holds the same data.\n"
        "// Generated by scripts/generate_sp500_seed.py. Do not edit this file by hand.\n"
        "// Load fixtures/seed.cypher first: it creates the regulator, concepts, and form types.\n",
        "// Ring 1: companies and identifiers\n"
        + cypher_rows(
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
        + "CREATE (c:Company {company_id: row.id, name: row.name, country: row.country,"
        " status: 'active'})\n"
        "CREATE (i:Identifier {scheme: 'CIK', value: row.cik})\n"
        "CREATE (c)-[:HAS_IDENTIFIER {since: date(row.first), status: 'active',"
        " primary: true}]->(i);\n",
        "// SEC adapter: registrants\n"
        + cypher_rows(
            [
                {
                    "company": company.company_id,
                    "cik": company.cik,
                    "name": company.name,
                    "first": company.first_filed,
                }
                for company in companies
            ]
        )
        + "MATCH (c:Company {company_id: row.company}), (r:Regulator {code: 'SEC'})\n"
        "CREATE (g:Registrant {regulator: 'SEC', native_id: row.cik, name: row.name})\n"
        "CREATE (c)-[:REGISTERED_AS]->(g)\n"
        "CREATE (g)-[:FILES_WITH {first_filed: date(row.first)}]->(r);\n",
        "// SEC adapter: fiscal years and quarters. `name` is the caption in the Neo4j Browser.\n"
        + cypher_rows(
            [
                {"cik": company.cik, "start": year.start_date, "end": year.end_date}
                for company, year in with_year
            ]
        )
        + "MATCH (g:Registrant {regulator: 'SEC', native_id: row.cik})\n"
        "CREATE (g)-[:HAS_FISCAL_YEAR]->(:FiscalYear {regulator: 'SEC', registrant: row.cik,\n"
        f"  fiscal_year: {FISCAL_YEAR}, start_date: date(row.start), end_date: date(row.end),\n"
        f"  name: 'FY{FISCAL_YEAR}'}});\n",
        cypher_rows(
            [
                {"key": key, "start": start, "end": end}
                for key, start, end in calendar_quarters(companies)
            ]
        )
        + "MERGE (p:Period {key: row.key})\n"
        "ON CREATE SET p.kind = 'quarter', p.start_date = date(row.start),"
        " p.end_date = date(row.end);\n",
        cypher_rows(
            [
                {
                    "cik": company.cik,
                    "quarter": str(quarter.quarter),
                    "start": quarter.start_date,
                    "end": quarter.end_date,
                    "period": quarter.period_key,
                }
                for company, year in with_year
                for quarter in year.quarters
            ]
        )
        + "MATCH (y:FiscalYear {regulator: 'SEC', registrant: row.cik,"
        f" fiscal_year: {FISCAL_YEAR}}}),\n"
        "      (p:Period {key: row.period})\n"
        "CREATE (y)-[:HAS_QUARTER]->(q:FiscalQuarter {regulator: 'SEC', registrant: row.cik,\n"
        f"  fiscal_year: {FISCAL_YEAR}, quarter: toInteger(row.quarter),\n"
        "  start_date: date(row.start), end_date: date(row.end), name: 'Q' + row.quarter})\n"
        "CREATE (q)-[:ALIGNS_WITH]->(p);\n",
        "// SEC adapter: filings. A 10-K reports on the fiscal year, a 10-Q on a quarter.\n"
        + cypher_rows(
            [
                filing_row(company, filing)
                for company in companies
                for filing, quarter in company.resolved_filings
                if quarter is None
            ]
        )
        + "MATCH (g:Registrant {regulator: 'SEC', native_id: row.cik}),\n"
        "      (t:FormType {regulator: 'SEC', code: row.form}),\n"
        f"      (y:FiscalYear {{regulator: 'SEC', registrant: row.cik, fiscal_year: {FISCAL_YEAR}}})\n"
        + filing_create
        + "CREATE (f)-[:REPORTS_ON]->(y);\n",
        cypher_rows(
            [
                filing_row(company, filing) | {"quarter": str(quarter)}
                for company in companies
                for filing, quarter in company.resolved_filings
                if quarter is not None
            ]
        )
        + "MATCH (g:Registrant {regulator: 'SEC', native_id: row.cik}),\n"
        "      (t:FormType {regulator: 'SEC', code: row.form}),\n"
        "      (q:FiscalQuarter {regulator: 'SEC', registrant: row.cik,"
        f" fiscal_year: {FISCAL_YEAR},\n"
        "                        quarter: toInteger(row.quarter)})\n"
        + filing_create
        + "CREATE (f)-[:REPORTS_ON]->(q);\n",
        "// Filings that declare another fiscal period than their dates say: no REPORTS_ON.\n"
        + cypher_rows(
            [
                filing_row(company, filing)
                for company in companies
                for filing in company.unresolved_filings
            ]
        )
        + "MATCH (g:Registrant {regulator: 'SEC', native_id: row.cik}),\n"
        "      (t:FormType {regulator: 'SEC', code: row.form})\n"
        + filing_create.rstrip("\n")
        + ";\n",
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
        "// Claim layer\n"
        + cypher_rows([{"mic": mic, "name": name} for mic, name in exchanges(companies)])
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
    ]
    return "\n".join(statements)


def filing_row(company: Company, filing: Filing) -> dict[str, str]:
    return {
        "cik": company.cik,
        "id": filing.accession,
        "form": filing.form,
        "filed": filing.filed_date,
        "end": filing.period_end,
    }


def sql_insert(
    table: str, columns: str, rows: Sequence[tuple[str | None, ...]], suffix: str = ""
) -> str:
    values = ",\n".join(
        "    (" + ", ".join("NULL" if value is None else quoted(value, "''") for value in row) + ")"
        for row in rows
    )
    return f"INSERT INTO {table} ({columns}) VALUES\n{values}{suffix};\n"


def sql_seed(companies: list[Company], as_of: date) -> str:
    envelope = (SOURCE, str(as_of), str(as_of), VERIFIABILITY)
    year = str(FISCAL_YEAR)
    with_year = [(company, company.fiscal_year) for company in companies if company.fiscal_year]
    filing_rows: list[tuple[str | None, ...]] = [
        (
            "SEC",
            filing.accession,
            company.cik,
            filing.form,
            filing.filed_date,
            filing.period_end,
            year,
            None if quarter is None else str(quarter),
        )
        for company in companies
        for filing, quarter in company.resolved_filings
    ]
    filing_rows += [
        (
            "SEC",
            filing.accession,
            company.cik,
            filing.form,
            filing.filed_date,
            filing.period_end,
            None,
            None,
        )
        for company in companies
        for filing in company.unresolved_filings
    ]
    statements = [
        "-- S&P 500 seed. Real data from SEC EDGAR. fixtures/sp500.cypher holds the same data.\n"
        "-- Generated by scripts/generate_sp500_seed.py. Do not edit this file by hand.\n"
        "-- Load fixtures/seed.sql first: it creates the regulator, concepts, and form types.\n",
        "-- Ring 1: companies and identifiers\n"
        + sql_insert(
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
        "-- SEC adapter: registrants\n"
        + sql_insert(
            "registrant",
            "regulator, native_id, company_id, name, first_filed",
            [
                ("SEC", company.cik, company.company_id, company.name, company.first_filed)
                for company in companies
            ],
        ),
        "-- SEC adapter: fiscal years and quarters\n"
        + sql_insert(
            "fiscal_year",
            "regulator, registrant, fiscal_year, start_date, end_date",
            [
                ("SEC", company.cik, year, fiscal_year.start_date, fiscal_year.end_date)
                for company, fiscal_year in with_year
            ],
        ),
        sql_insert(
            "period",
            "key, kind, start_date, end_date",
            [(key, "quarter", start, end) for key, start, end in calendar_quarters(companies)],
            " ON CONFLICT DO NOTHING",
        ),
        sql_insert(
            "fiscal_quarter",
            "regulator, registrant, fiscal_year, quarter, start_date, end_date, period_key",
            [
                (
                    "SEC",
                    company.cik,
                    year,
                    str(quarter.quarter),
                    quarter.start_date,
                    quarter.end_date,
                    quarter.period_key,
                )
                for company, fiscal_year in with_year
                for quarter in fiscal_year.quarters
            ],
        ),
        "-- SEC adapter: filings. A NULL fiscal_year marks a filing that declares another fiscal\n"
        "-- period than its dates say.\n"
        + sql_insert(
            "filing",
            "regulator, native_id, registrant, form, filed_date, period_end, fiscal_year, quarter",
            filing_rows,
        ),
        sql_insert(
            "reports_concept",
            "regulator, native_id, element, confidence",
            [
                ("SEC", filing.accession, concept, confidence)
                for company in companies
                for filing in company.filings
                for concept, confidence in filing.concepts.items()
            ],
        ),
        "-- Claim layer\n"
        + sql_insert("exchange", "mic, name", exchanges(companies), " ON CONFLICT DO NOTHING"),
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
    ]
    return "\n".join(statements)


def calendar_quarters(companies: list[Company]) -> list[tuple[str, str, str]]:
    """Returns key, start, and end of each calendar quarter that a fiscal quarter aligns with."""
    keys = {
        quarter.period_key
        for company in companies
        if company.fiscal_year
        for quarter in company.fiscal_year.quarters
    }
    quarters = []
    for key in sorted(keys, key=lambda key: (key[3:], key[:2])):
        number, year = int(key[1]), int(key[3:])
        start = date(year, 3 * number - 2, 1)
        end = date(year + number // 4, 3 * number % 12 + 1, 1) - timedelta(days=1)
        quarters.append((key, str(start), str(end)))
    return quarters


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
    ciks = {company.cik for company in companies}
    accessions = {filing.accession for company in companies for filing in company.filings}
    without_filing = [
        (company, quarter.quarter)
        for company in companies
        if company.fiscal_year
        for quarter in company.fiscal_year.quarters
        if quarter.quarter <= 3 and quarter.filing is None
    ]

    merge_expected(
        "missing_q3_2024",
        "company_id",
        company_ids,
        [{"company_id": company.company_id} for company, quarter in without_filing if quarter == 3],
    )
    merge_expected(
        "incomplete_fy2024",
        "company_id",
        company_ids,
        [
            {"company_id": company.company_id, "missing_period": f"Q{quarter}"}
            for company, quarter in without_filing
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
    merge_expected(
        "check_filing_has_period",
        "native_id",
        accessions,
        [
            {"native_id": filing.accession}
            for company in companies
            for filing in company.unresolved_filings
        ],
    )
    merge_expected(
        "check_fiscal_quarters",
        "registrant",
        ciks,
        [
            {"registrant": company.cik, "fiscal_year": FISCAL_YEAR, "quarter": quarter}
            for company in companies
            if company.fiscal_year
            for quarter in broken_quarters(company.fiscal_year)
        ],
    )


def broken_quarters(fiscal_year: FiscalYear) -> list[int]:
    """Returns the quarters that leave a gap or an overlap, or that do not end with the year."""
    broken = []
    expected_start = fiscal_year.start_date
    for quarter in fiscal_year.quarters:
        ends_late = quarter.quarter == 4 and quarter.end_date != fiscal_year.end_date
        if quarter.start_date != expected_start or ends_late:
            broken.append(quarter.quarter)
        expected_start = next_day(quarter.end_date)
    return broken


def merge_expected(
    query: str, key: str, generated_keys: set[str], rows: Sequence[dict[str, str | int]]
) -> None:
    path = QUERIES / query / "expected.json"
    kept = [row for row in json.loads(path.read_text()) if row[key] not in generated_keys]
    merged = kept + sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))
    lines = ",\n".join(f"  {json.dumps(row)}" for row in merged)
    path.write_text(f"[\n{lines}\n]\n" if merged else "[]\n")


if __name__ == "__main__":
    main()
