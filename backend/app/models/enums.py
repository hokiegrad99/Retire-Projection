"""Closed enumerations shared by the database, API, and validation layer.

``db_enum`` builds a native PostgreSQL enum that stores each member's
*value* (the lowercase string), so the database, Pydantic JSON payloads,
and Python code all use one identical representation.
"""

from enum import Enum, StrEnum

from sqlalchemy import Enum as SAEnum


def db_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    """Native enum column type storing member values (e.g. ``'single'``)."""
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


class FilingStatus(StrEnum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"


class PersonRole(StrEnum):
    PRIMARY = "primary"
    SPOUSE_PARTNER = "spouse_partner"
    DEPENDENT = "dependent"


class AccountType(StrEnum):
    CHECKING = "checking"
    SAVINGS = "savings"
    TAXABLE_BROKERAGE = "taxable_brokerage"
    CD_MONEY_MARKET = "cd_money_market"
    TRADITIONAL_IRA = "traditional_ira"
    ROTH_IRA = "roth_ira"
    TRADITIONAL_401K = "traditional_401k"
    ROTH_401K = "roth_401k"
    TRADITIONAL_403B = "traditional_403b"
    ROTH_403B = "roth_403b"
    TRADITIONAL_457B = "traditional_457b"
    ROTH_457B = "roth_457b"
    HSA = "hsa"
    COLLEGE_529 = "college_529"
    INHERITED_RETIREMENT = "inherited_retirement"
    CASH_BALANCE_PLAN = "cash_balance_plan"
    DEFINED_BENEFIT_PENSION = "defined_benefit_pension"
    ANNUITY = "annuity"
    PRIMARY_RESIDENCE = "primary_residence"
    REAL_ESTATE = "real_estate"
    RENTAL_PROPERTY = "rental_property"
    BUSINESS_INTEREST = "business_interest"
    VEHICLE = "vehicle"
    OTHER = "other"


class TaxTreatment(StrEnum):
    """How withdrawals from the vehicle are taxed."""

    TAXABLE = "taxable"
    TAX_DEFERRED = "tax_deferred"
    TAX_FREE = "tax_free"
    TAX_EXEMPT = "tax_exempt"


class AssetClass(StrEnum):
    US_STOCK = "us_stock"
    INTERNATIONAL_STOCK = "international_stock"
    BONDS = "bonds"
    CASH = "cash"
    REAL_ESTATE = "real_estate"
    OTHER = "other"


class LiabilityType(StrEnum):
    MORTGAGE = "mortgage"
    HOME_EQUITY_LINE = "home_equity_line"
    AUTO = "auto"
    STUDENT = "student"
    CREDIT_CARD = "credit_card"
    OTHER = "other"


class IncomeType(StrEnum):
    SALARY = "salary"
    BONUS = "bonus"
    PART_TIME = "part_time"
    PENSION = "pension"
    SOCIAL_SECURITY = "social_security"
    ANNUITY = "annuity"
    RENTAL = "rental"
    BUSINESS = "business"
    DIVIDEND_INTEREST = "dividend_interest"
    WINDFALL = "windfall"
    OTHER = "other"


class PaymentFrequency(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ONE_TIME = "one_time"


class MoneyBasis(StrEnum):
    """Whether an amount is stated in nominal or today's-dollar terms."""

    NOMINAL = "nominal"
    TODAY_DOLLARS = "today_dollars"


class TaxClassification(StrEnum):
    ORDINARY = "ordinary"
    QUALIFIED_DIVIDENDS = "qualified_dividends"
    CAPITAL_GAINS = "capital_gains"
    TAX_EXEMPT = "tax_exempt"


class SurvivorTreatment(StrEnum):
    CONTINUE = "continue"
    STOP = "stop"
    REDUCE_BY_PERCENT = "reduce_by_percent"


class ExpenseClass(StrEnum):
    ESSENTIAL = "essential"
    DISCRETIONARY = "discretionary"
    OPTIONAL = "optional"


class ExpenseCategory(StrEnum):
    HOUSING = "housing"
    UTILITIES = "utilities"
    FOOD = "food"
    TRANSPORTATION = "transportation"
    TRAVEL = "travel"
    HOBBIES = "hobbies"
    HEALTHCARE = "healthcare"
    INSURANCE = "insurance"
    EDUCATION = "education"
    DEPENDENT_SUPPORT = "dependent_support"
    LONG_TERM_CARE = "long_term_care"
    CHARITABLE = "charitable"
    TAXES = "taxes"
    DEBT_PAYMENT = "debt_payment"
    OTHER = "other"


class SpendingPhase(StrEnum):
    PRE_RETIREMENT = "pre_retirement"
    POST_RETIREMENT = "post_retirement"
    ANY_TIME = "any_time"
