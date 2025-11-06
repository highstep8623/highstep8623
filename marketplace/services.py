import calendar
import datetime as dt
from typing import Dict, List, Optional
from dataclasses import asdict

from . import auth, database
from .tiers import ACCEPTED_QUOTE_FEE_PERCENTAGE, CONTRACTOR_TIERS, HOMEOWNER_TIERS


class MarketplaceError(Exception):
    """Domain specific exception for business rule violations."""


def _now() -> dt.datetime:
    return dt.datetime.utcnow()


def _month_start(date: Optional[dt.datetime] = None) -> dt.datetime:
    date = date or _now()
    return dt.datetime(date.year, date.month, 1)


def get_user(user_id: int) -> Optional[Dict]:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def register_homeowner(email: str, password: str, profile: Dict) -> Dict:
    tier = HOMEOWNER_TIERS["basic"]
    try:
        user_id = auth.create_user(email, password, "homeowner", tier.slug)
    except Exception as exc:  # sqlite3.IntegrityError but keep generic w/out import
        raise MarketplaceError("Email already registered") from exc
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO homeowner_profiles (user_id, full_name, phone, location, bio) VALUES (?, ?, ?, ?, ?)",
        (
            user_id,
            profile.get("full_name"),
            profile.get("phone"),
            profile.get("location"),
            profile.get("bio"),
        ),
    )
    conn.commit()
    token = auth.generate_token(user_id, "homeowner")
    return {"user_id": user_id, "token": token, "tier": tier.slug}


def register_contractor(email: str, password: str, profile: Dict) -> Dict:
    tier = CONTRACTOR_TIERS["starter"]
    try:
        user_id = auth.create_user(email, password, "contractor", tier.slug)
    except Exception as exc:
        raise MarketplaceError("Email already registered") from exc
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO contractor_profiles
        (user_id, business_name, license_number, insurance_info, service_areas, specialties)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            profile.get("business_name"),
            profile.get("license_number"),
            profile.get("insurance_info"),
            ",".join(profile.get("service_areas", [])),
            ",".join(profile.get("specialties", [])),
        ),
    )
    conn.commit()
    token = auth.generate_token(user_id, "contractor")
    return {"user_id": user_id, "token": token, "tier": tier.slug}


def authenticate(email: str, password: str) -> Dict:
    user = auth.authenticate(email, password)
    if not user:
        raise MarketplaceError("Invalid credentials")
    token = auth.generate_token(user["id"], user["role"])
    return {"token": token, "user_id": user["id"], "role": user["role"], "tier": user["tier"]}


def _homeowner_tier(user_id: int):
    user = get_user(user_id)
    return HOMEOWNER_TIERS[user["tier"]]


def _contractor_tier(user_id: int):
    user = get_user(user_id)
    return CONTRACTOR_TIERS[user["tier"]]


def list_projects_for_homeowner(user_id: int) -> List[Dict]:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM projects WHERE homeowner_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def _count_active_projects(user_id: int) -> int:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM projects WHERE homeowner_id = ? AND status IN ('open', 'in_progress')",
        (user_id,),
    )
    return cursor.fetchone()[0]


def create_project(homeowner_id: int, payload: Dict) -> Dict:
    tier = _homeowner_tier(homeowner_id)
    active_projects = _count_active_projects(homeowner_id)
    if active_projects >= tier.max_active_projects:
        raise MarketplaceError(
            "Upgrade required to post more active projects. Current tier limit reached."
        )
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO projects
        (homeowner_id, title, project_type, description, budget_min, budget_max, desired_start_date, location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            homeowner_id,
            payload["title"],
            payload.get("project_type", "General"),
            payload.get("description", ""),
            payload.get("budget_min"),
            payload.get("budget_max"),
            payload.get("desired_start_date"),
            payload.get("location"),
        ),
    )
    project_id = cursor.lastrowid
    for url in payload.get("photos", [])[:10]:
        cursor.execute(
            "INSERT INTO project_photos (project_id, url) VALUES (?, ?)",
            (project_id, url),
        )
    conn.commit()
    return get_project(project_id)


def get_project(project_id: int) -> Optional[Dict]:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project_row = cursor.fetchone()
    if not project_row:
        return None
    cursor.execute("SELECT url FROM project_photos WHERE project_id = ?", (project_id,))
    photos = [row["url"] for row in cursor.fetchall()]
    result = dict(project_row)
    result["photos"] = photos
    return result


def list_open_projects_for_contractor(contractor_id: int) -> List[Dict]:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.*, hp.full_name as homeowner_name
        FROM projects p
        JOIN homeowner_profiles hp ON p.homeowner_id = hp.user_id
        WHERE p.status = 'open'
        ORDER BY p.created_at DESC
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def _quotes_this_month(contractor_id: int) -> int:
    conn = database.get_connection()
    cursor = conn.cursor()
    month_start = _month_start().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "SELECT COUNT(*) FROM quotes WHERE contractor_id = ? AND submitted_at >= ?",
        (contractor_id, month_start),
    )
    return cursor.fetchone()[0]


def submit_quote(contractor_id: int, project_id: int, payload: Dict) -> Dict:
    tier = _contractor_tier(contractor_id)
    submitted = _quotes_this_month(contractor_id)
    limit = tier.max_quotes_per_month or tier.max_quotes_per_project
    if limit is not None and submitted >= limit:
        raise MarketplaceError("Monthly quote limit reached for your subscription tier.")
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, homeowner_id FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    if not project or project["status"] != "open":
        raise MarketplaceError("Project is no longer accepting quotes.")
    homeowner_tier = _homeowner_tier(project["homeowner_id"])
    cursor.execute("SELECT COUNT(*) FROM quotes WHERE project_id = ?", (project_id,))
    existing_quotes = cursor.fetchone()[0]
    quote_limit = homeowner_tier.max_quotes_per_project
    if quote_limit is not None and existing_quotes >= quote_limit:
        raise MarketplaceError("Homeowner quote limit reached for this project.")
    cursor.execute(
        """
        INSERT INTO quotes
        (project_id, contractor_id, amount, cost_breakdown, timeline, materials, payment_schedule)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            contractor_id,
            payload.get("amount", 0.0),
            payload.get("cost_breakdown"),
            payload.get("timeline"),
            payload.get("materials"),
            payload.get("payment_schedule"),
        ),
    )
    conn.commit()
    return get_quote(cursor.lastrowid)


def get_quote(quote_id: int) -> Optional[Dict]:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,))
    row = cursor.fetchone()
    return dict(row) if row else None




def list_quotes_for_contractor(contractor_id: int) -> List[Dict]:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT q.*, p.title as project_title
        FROM quotes q
        JOIN projects p ON q.project_id = p.id
        WHERE q.contractor_id = ?
        ORDER BY q.submitted_at DESC
        """,
        (contractor_id,),
    )
    return [dict(row) for row in cursor.fetchall()]

def list_quotes_for_project(project_id: int) -> List[Dict]:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT q.*, cp.business_name, cp.specialties
        FROM quotes q
        JOIN contractor_profiles cp ON q.contractor_id = cp.user_id
        WHERE q.project_id = ?
        ORDER BY q.submitted_at DESC
        """,
        (project_id,),
    )
    quotes = []
    for row in cursor.fetchall():
        record = dict(row)
        record["specialties"] = (record.get("specialties") or "").split(",") if record.get("specialties") else []
        quotes.append(record)
    return quotes


def accept_quote(homeowner_id: int, quote_id: int) -> Dict:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT q.*, p.homeowner_id FROM quotes q JOIN projects p ON q.project_id = p.id WHERE q.id = ?",
        (quote_id,),
    )
    quote = cursor.fetchone()
    if not quote:
        raise MarketplaceError("Quote not found")
    if quote["homeowner_id"] != homeowner_id:
        raise MarketplaceError("You cannot accept quotes for other homeowners")
    if quote["status"] == "accepted":
        return dict(quote)
    cursor.execute(
        "UPDATE quotes SET status = 'accepted', accepted_at = CURRENT_TIMESTAMP WHERE id = ?",
        (quote_id,),
    )
    cursor.execute(
        "UPDATE projects SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (quote["project_id"],),
    )
    fee = round(quote["amount"] * ACCEPTED_QUOTE_FEE_PERCENTAGE, 2)
    cursor.execute(
        "INSERT INTO invoices (user_id, quote_id, amount, category) VALUES (?, ?, ?, ?)",
        (quote["contractor_id"], quote_id, fee, "accepted_quote_fee"),
    )
    conn.commit()
    return get_quote(quote_id)


def decline_quote(homeowner_id: int, quote_id: int) -> Dict:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT q.*, p.homeowner_id FROM quotes q JOIN projects p ON q.project_id = p.id WHERE q.id = ?",
        (quote_id,),
    )
    quote = cursor.fetchone()
    if not quote:
        raise MarketplaceError("Quote not found")
    if quote["homeowner_id"] != homeowner_id:
        raise MarketplaceError("Unauthorized")
    cursor.execute("UPDATE quotes SET status = 'declined' WHERE id = ?", (quote_id,))
    conn.commit()
    return get_quote(quote_id)


def send_message(sender_id: int, recipient_id: int, project_id: int, body: str) -> Dict:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO messages (project_id, sender_id, recipient_id, body) VALUES (?, ?, ?, ?)
        """,
        (project_id, sender_id, recipient_id, body),
    )
    conn.commit()
    return dict(cursor.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone())


def list_messages(project_id: int, user_id: int) -> List[Dict]:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM messages
        WHERE project_id = ? AND (sender_id = ? OR recipient_id = ?)
        ORDER BY created_at ASC
        """,
        (project_id, user_id, user_id),
    )
    return [dict(row) for row in cursor.fetchall()]


def leave_review(homeowner_id: int, contractor_id: int, project_id: int, rating: int, comment: str) -> Dict:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status FROM projects WHERE id = ? AND homeowner_id = ?",
        (project_id, homeowner_id),
    )
    project = cursor.fetchone()
    if not project or project["status"] not in ("in_progress", "completed"):
        raise MarketplaceError("Project must be in progress or completed to leave a review.")
    cursor.execute(
        """
        INSERT INTO reviews (project_id, homeowner_id, contractor_id, rating, comment)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, homeowner_id, contractor_id, rating, comment),
    )
    conn.commit()
    return dict(cursor.execute("SELECT * FROM reviews WHERE id = ?", (cursor.lastrowid,)).fetchone())


def record_payment(invoice_id: int, amount: float, processor: str, reference: str) -> Dict:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO payments (invoice_id, amount, processor, transaction_reference, status)
        VALUES (?, ?, ?, ?, 'completed')
        """,
        (invoice_id, amount, processor, reference),
    )
    cursor.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
    conn.commit()
    return dict(cursor.execute("SELECT * FROM payments WHERE id = ?", (cursor.lastrowid,)).fetchone())


def list_contractor_profiles(filters: Optional[Dict] = None) -> List[Dict]:
    filters = filters or {}
    conn = database.get_connection()
    cursor = conn.cursor()
    query = "SELECT u.id as contractor_id, u.tier, cp.* FROM contractor_profiles cp JOIN users u ON cp.user_id = u.id"
    conditions = []
    params: List = []
    if filters.get("service_area"):
        conditions.append("cp.service_areas LIKE ?")
        params.append(f"%{filters['service_area']}%")
    if filters.get("specialty"):
        conditions.append("cp.specialties LIKE ?")
        params.append(f"%{filters['specialty']}%")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY cp.verification_badge DESC, u.tier DESC"
    cursor.execute(query, params)
    profiles = []
    for row in cursor.fetchall():
        record = dict(row)
        record["service_areas"] = (record.get("service_areas") or "").split(",") if record.get("service_areas") else []
        record["specialties"] = (record.get("specialties") or "").split(",") if record.get("specialties") else []
        tier = CONTRACTOR_TIERS.get(record["tier"])
        record["tier_details"] = asdict(tier) if tier else None
        profiles.append(record)
    return profiles


def dashboard_summary(user_id: int, role: str) -> Dict:
    conn = database.get_connection()
    cursor = conn.cursor()
    if role == "homeowner":
        cursor.execute(
            "SELECT COUNT(*) FROM projects WHERE homeowner_id = ? AND status = 'open'",
            (user_id,),
        )
        open_projects = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM projects WHERE homeowner_id = ? AND status = 'completed'",
            (user_id,),
        )
        completed = cursor.fetchone()[0]
        quotes = []
        for project in list_projects_for_homeowner(user_id):
            quotes.extend(list_quotes_for_project(project["id"]))
        return {
            "open_projects": open_projects,
            "completed_projects": completed,
            "quotes_received": len(quotes),
            "tier": get_user(user_id)["tier"],
        }
    cursor.execute(
        "SELECT COUNT(*) FROM quotes WHERE contractor_id = ? AND status = 'submitted'",
        (user_id,),
    )
    submitted = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM quotes WHERE contractor_id = ? AND status = 'accepted'",
        (user_id,),
    )
    accepted = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COUNT(*) FROM reviews WHERE contractor_id = ?",
        (user_id,),
    )
    reviews = cursor.fetchone()[0]
    return {
        "submitted_quotes": submitted,
        "accepted_quotes": accepted,
        "reviews": reviews,
        "tier": get_user(user_id)["tier"],
    }


def upgrade_subscription(user_id: int, role: str, new_tier: str, billing_cycle: str) -> Dict:
    conn = database.get_connection()
    cursor = conn.cursor()
    if role == "homeowner":
        if new_tier not in HOMEOWNER_TIERS:
            raise MarketplaceError("Unknown homeowner tier")
        plan = HOMEOWNER_TIERS[new_tier]
    elif role == "contractor":
        if new_tier not in CONTRACTOR_TIERS:
            raise MarketplaceError("Unknown contractor tier")
        plan = CONTRACTOR_TIERS[new_tier]
    else:
        raise MarketplaceError("Unsupported role")
    price = plan.price_monthly if billing_cycle == "monthly" else plan.price_annual
    cursor.execute("UPDATE users SET tier = ? WHERE id = ?", (plan.slug, user_id))
    cursor.execute(
        "INSERT INTO subscriptions (user_id, tier, billing_cycle, price) VALUES (?, ?, ?, ?)",
        (user_id, plan.slug, billing_cycle, price),
    )
    conn.commit()
    return {"tier": plan.slug, "price": price, "billing_cycle": billing_cycle}


def monthly_billing_overview(year: int, month: int) -> Dict:
    conn = database.get_connection()
    cursor = conn.cursor()
    month_start = dt.datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    month_end = dt.datetime(year, month, last_day, 23, 59, 59)
    cursor.execute(
        """
        SELECT COUNT(*) as invoices, SUM(amount) as total
        FROM invoices
        WHERE created_at BETWEEN ? AND ?
        """,
        (month_start.strftime("%Y-%m-%d %H:%M:%S"), month_end.strftime("%Y-%m-%d %H:%M:%S")),
    )
    invoice_row = cursor.fetchone()
    cursor.execute(
        """
        SELECT COUNT(*) as payments, SUM(amount) as paid
        FROM payments
        WHERE created_at BETWEEN ? AND ? AND status = 'completed'
        """,
        (month_start.strftime("%Y-%m-%d %H:%M:%S"), month_end.strftime("%Y-%m-%d %H:%M:%S")),
    )
    payment_row = cursor.fetchone()
    return {
        "invoice_count": invoice_row["invoices"] or 0,
        "invoice_total": invoice_row["total"] or 0.0,
        "payments": payment_row["payments"] or 0,
        "payments_total": payment_row["paid"] or 0.0,
    }


def admin_user_overview() -> Dict:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, COUNT(*) as count FROM users GROUP BY role"
    )
    counts = {row["role"]: row["count"] for row in cursor.fetchall()}
    cursor.execute(
        "SELECT tier, COUNT(*) as count FROM users GROUP BY tier"
    )
    tiers = {row["tier"]: row["count"] for row in cursor.fetchall()}
    return {"roles": counts, "tiers": tiers}

