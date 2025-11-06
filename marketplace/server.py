import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import auth, database, services
from .router import Router, error_response, json_response, parse_json_body

STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend"
router = Router()

def require_auth(headers):
    auth_header = headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    return auth.decode_token(token)

def register_routes():
    router.add("POST", "/api/auth/homeowner/register", handle_homeowner_register)
    router.add("POST", "/api/auth/contractor/register", handle_contractor_register)
    router.add("POST", "/api/auth/login", handle_login)
    router.add("GET", "/api/homeowner/projects", handle_homeowner_projects)
    router.add("POST", "/api/homeowner/projects", handle_homeowner_create_project)
    router.add("GET", "/api/homeowner/quotes", handle_homeowner_quotes)
    router.add("POST", "/api/homeowner/quotes/accept", handle_homeowner_accept_quote)
    router.add("POST", "/api/homeowner/quotes/decline", handle_homeowner_decline_quote)
    router.add("POST", "/api/homeowner/reviews", handle_homeowner_review)
    router.add("GET", "/api/homeowner/messages", handle_messages)
    router.add("POST", "/api/homeowner/messages", handle_send_message)
    router.add("GET", "/api/homeowner/dashboard", handle_dashboard)
    router.add("GET", "/api/contractor/projects", handle_contractor_projects)
    router.add("POST", "/api/contractor/quotes", handle_contractor_quote)
    router.add("GET", "/api/contractor/dashboard", handle_dashboard)
    router.add("GET", "/api/contractor/messages", handle_messages)
    router.add("POST", "/api/contractor/messages", handle_send_message)
    router.add("GET", "/api/contractor/quotes", handle_contractor_quotes)
    router.add("GET", "/api/contractors", handle_list_contractors)
    router.add("POST", "/api/subscriptions/upgrade", handle_upgrade_subscription)
    router.add("POST", "/api/payments", handle_record_payment)
    router.add("GET", "/api/admin/overview", handle_admin_overview)

def build_context(headers, query, user):
    return {"headers": headers, "query": query, "user": user}

# Handlers

def handle_homeowner_register(body, context):
    try:
        profile = body.get("profile", {})
        result = services.register_homeowner(body["email"], body["password"], profile)
        return HTTPStatus.CREATED, result
    except (KeyError, services.MarketplaceError) as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}

def handle_contractor_register(body, context):
    try:
        profile = body.get("profile", {})
        result = services.register_contractor(body["email"], body["password"], profile)
        return HTTPStatus.CREATED, result
    except (KeyError, services.MarketplaceError) as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}

def handle_login(body, context):
    try:
        result = services.authenticate(body["email"], body["password"])
        return HTTPStatus.OK, result
    except (KeyError, services.MarketplaceError) as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def _require_user(context, expected_role=None):
    user = context.get("user")
    if not user:
        raise PermissionError("Authentication required")
    if expected_role and user.get("role") != expected_role:
        raise PermissionError("Insufficient permissions")
    return user

def handle_homeowner_projects(body, context):
    try:
        user = _require_user(context, "homeowner")
        projects = services.list_projects_for_homeowner(user["sub"])
        return HTTPStatus.OK, {"projects": projects}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_homeowner_create_project(body, context):
    try:
        user = _require_user(context, "homeowner")
        project = services.create_project(user["sub"], body)
        return HTTPStatus.CREATED, project
    except services.MarketplaceError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_homeowner_quotes(body, context):
    try:
        user = _require_user(context, "homeowner")
        project_id = int(context["query"].get("project_id", [0])[0])
        quotes = services.list_quotes_for_project(project_id)
        return HTTPStatus.OK, {"quotes": quotes}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_homeowner_accept_quote(body, context):
    try:
        user = _require_user(context, "homeowner")
        quote = services.accept_quote(user["sub"], body["quote_id"])
        return HTTPStatus.OK, quote
    except (KeyError, services.MarketplaceError) as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_homeowner_decline_quote(body, context):
    try:
        user = _require_user(context, "homeowner")
        quote = services.decline_quote(user["sub"], body["quote_id"])
        return HTTPStatus.OK, quote
    except (KeyError, services.MarketplaceError) as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_homeowner_review(body, context):
    try:
        user = _require_user(context, "homeowner")
        review = services.leave_review(
            homeowner_id=user["sub"],
            contractor_id=body["contractor_id"],
            project_id=body["project_id"],
            rating=body["rating"],
            comment=body.get("comment", ""),
        )
        return HTTPStatus.CREATED, review
    except (KeyError, services.MarketplaceError) as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_messages(body, context):
    try:
        user = _require_user(context)
        project_id = int(context["query"].get("project_id", [0])[0])
        messages = services.list_messages(project_id, user["sub"])
        return HTTPStatus.OK, {"messages": messages}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_send_message(body, context):
    try:
        user = _require_user(context)
        message = services.send_message(
            sender_id=user["sub"],
            recipient_id=body["recipient_id"],
            project_id=body["project_id"],
            body=body["body"],
        )
        return HTTPStatus.CREATED, message
    except (KeyError, services.MarketplaceError) as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_dashboard(body, context):
    try:
        user = _require_user(context)
        summary = services.dashboard_summary(user["sub"], user["role"])
        return HTTPStatus.OK, summary
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_contractor_projects(body, context):
    try:
        user = _require_user(context, "contractor")
        projects = services.list_open_projects_for_contractor(user["sub"])
        return HTTPStatus.OK, {"projects": projects}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_contractor_quote(body, context):
    try:
        user = _require_user(context, "contractor")
        quote = services.submit_quote(user["sub"], body["project_id"], body)
        return HTTPStatus.CREATED, quote
    except (KeyError, services.MarketplaceError) as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_contractor_quotes(body, context):
    try:
        user = _require_user(context, "contractor")
        query = context["query"]
        project_values = query.get("project_id")
        if project_values:
            project_id = int(project_values[0])
            quotes = services.list_quotes_for_project(project_id)
        else:
            quotes = services.list_quotes_for_contractor(user["sub"])
        return HTTPStatus.OK, {"quotes": quotes}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_list_contractors(body, context):
    filters = {key: value[0] for key, value in context["query"].items()}
    profiles = services.list_contractor_profiles(filters)
    return HTTPStatus.OK, {"contractors": profiles}

def handle_upgrade_subscription(body, context):
    try:
        user = _require_user(context)
        result = services.upgrade_subscription(
            user_id=user["sub"],
            role=user["role"],
            new_tier=body["tier"],
            billing_cycle=body.get("billing_cycle", "monthly"),
        )
        return HTTPStatus.OK, result
    except (KeyError, services.MarketplaceError) as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_record_payment(body, context):
    try:
        user = _require_user(context)
        payment = services.record_payment(
            invoice_id=body["invoice_id"],
            amount=body["amount"],
            processor=body.get("processor", "stripe"),
            reference=body.get("reference", "manual"),
        )
        return HTTPStatus.CREATED, payment
    except (KeyError, services.MarketplaceError) as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

def handle_admin_overview(body, context):
    try:
        user = _require_user(context, "admin")
        overview = services.admin_user_overview()
        return HTTPStatus.OK, overview
    except PermissionError as exc:
        return HTTPStatus.UNAUTHORIZED, {"error": str(exc)}

class MarketplaceRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        handler = router.resolve("GET", parsed.path)
        headers = {k: v for k, v in self.headers.items()}
        user = require_auth(headers)
        if handler:
            status, payload = handler({}, build_context(headers, parse_qs(parsed.query), user))
            status, body, resp_headers = json_response(status, payload)
            self.send_response(status)
            for key, value in resp_headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/" or parsed.path.startswith("/app"):
            self.serve_static("index.html")
            return
        static_file = STATIC_DIR / parsed.path.lstrip("/")
        if static_file.exists() and static_file.is_file():
            self.serve_static(parsed.path.lstrip("/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length)
        parsed = urlparse(self.path)
        handler = router.resolve("POST", parsed.path)
        headers = {k: v for k, v in self.headers.items()}
        user = require_auth(headers)
        if not handler:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return
        try:
            payload = parse_json_body(body_bytes)
        except json.JSONDecodeError:
            status, body, resp_headers = error_response("Invalid JSON")
            self.send_response(status)
            for key, value in resp_headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)
            return
        status_code, data = handler(payload, build_context(headers, parse_qs(parsed.query), user))
        status, body, resp_headers = json_response(status_code, data)
        self.send_response(status)
        for key, value in resp_headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, relative_path: str):
        target = STATIC_DIR / relative_path
        if not target.exists():
            target = STATIC_DIR / "index.html"
        mime, _ = mimetypes.guess_type(str(target))
        mime = mime or "text/html"
        content = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, fmt, *args):
        return  # suppress default logging


def run(port: int = 8000):
    database.initialize_database()
    register_routes()
    server = ThreadingHTTPServer(("0.0.0.0", port), MarketplaceRequestHandler)
    print(f"Marketplace server running on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()

