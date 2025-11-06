from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Tier:
    slug: str
    name: str
    price_monthly: float
    price_annual: float
    max_active_projects: int
    max_quotes_per_project: int | None
    features: List[str]
    priority_search: bool = False
    project_management_tools: bool = False
    premium_support: bool = False
    max_quotes_per_month: int | None = None


HOMEOWNER_TIERS: Dict[str, Tier] = {
    "basic": Tier(
        slug="basic",
        name="Basic",
        price_monthly=0.0,
        price_annual=0.0,
        max_active_projects=1,
        max_quotes_per_project=3,
        max_quotes_per_month=3,
        features=[
            "Post one active project",
            "Receive up to three quotes",
            "Basic messaging",
            "Leave reviews after completion",
        ],
    ),
    "plus": Tier(
        slug="plus",
        name="Plus",
        price_monthly=19.0,
        price_annual=199.0,
        max_active_projects=3,
        max_quotes_per_project=None,
        max_quotes_per_month=None,
        priority_search=True,
        project_management_tools=True,
        premium_support=True,
        features=[
            "Up to three active projects",
            "Unlimited quotes",
            "Budget tracking and photo uploads",
            "Priority placement in contractor search",
        ],
    ),
    "pro": Tier(
        slug="pro",
        name="Pro",
        price_monthly=39.0,
        price_annual=399.0,
        max_active_projects=10,
        max_quotes_per_project=None,
        max_quotes_per_month=None,
        priority_search=True,
        project_management_tools=True,
        premium_support=True,
        features=[
            "Ten active projects",
            "Advanced contractor filtering",
            "Milestone management",
            "Premium support",
        ],
    ),
    "premium": Tier(
        slug="premium",
        name="Premium",
        price_monthly=89.0,
        price_annual=899.0,
        max_active_projects=50,
        max_quotes_per_project=None,
        max_quotes_per_month=None,
        priority_search=True,
        project_management_tools=True,
        premium_support=True,
        features=[
            "Dedicated project concierge",
            "Extended warranty options",
            "Unlimited messaging history",
            "Comprehensive analytics",
        ],
    ),
}


CONTRACTOR_TIERS: Dict[str, Tier] = {
    "starter": Tier(
        slug="starter",
        name="Starter",
        price_monthly=49.0,
        price_annual=499.0,
        max_active_projects=10,
        max_quotes_per_project=15,
        max_quotes_per_month=15,
        features=[
            "Limited monthly bids",
            "Basic analytics",
            "Standard listing",
        ],
    ),
    "growth": Tier(
        slug="growth",
        name="Growth",
        price_monthly=99.0,
        price_annual=999.0,
        max_active_projects=30,
        max_quotes_per_project=50,
        priority_search=True,
        max_quotes_per_month=50,
        project_management_tools=True,
        premium_support=True,
        features=[
            "Featured placement in search",
            "More monthly bids",
            "Lead management tools",
        ],
    ),
    "elite": Tier(
        slug="elite",
        name="Elite",
        price_monthly=199.0,
        price_annual=1999.0,
        max_active_projects=100,
        max_quotes_per_project=500,
        priority_search=True,
        max_quotes_per_month=500,
        project_management_tools=True,
        premium_support=True,
        features=[
            "Unlimited bids",
            "Conversion analytics",
            "Priority onboarding & support",
        ],
    ),
}


ACCEPTED_QUOTE_FEE_PERCENTAGE = 0.03
