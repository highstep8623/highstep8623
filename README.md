# RenovaHub Marketplace

RenovaHub is a two-sided marketplace that connects homeowners with vetted contractors for home improvement projects. The platform includes tiered subscription models, in-app messaging, escrow-ready payment tracking, analytics dashboards, and a responsive single-page experience optimised for mobile devices.

## Features

### Homeowners
- Email-based account registration and authentication.
- Tiered access levels (Basic, Plus, Pro, Premium) with project and quote limits.
- Guided project posting workflow with budget, timeline, and photo support.
- Dashboard highlighting project status, quotes, invoices, and upgrade options.
- Quote acceptance flow that triggers escrow-ready invoices and contractor fees.
- Ratings and reviews for completed projects.

### Contractors
- Business onboarding with license, insurance, and speciality capture.
- Subscription tiers (Starter, Growth, Elite) controlling bidding volume and visibility.
- Lead discovery with filters by service area and speciality.
- Quote composer supporting pricing, timeline, and payment schedule metadata.
- Analytics dashboard for conversion rate, response time, and reviews.
- Pay-per-accepted-quote invoicing in addition to recurring subscriptions.

### Platform
- JWT-style token authentication implemented with standard library tools.
- SQLite data layer with referential integrity and transactional helpers.
- REST-style JSON API served by a lightweight WSGI-compatible HTTP server.
- Responsive frontend (Vanilla JS + CSS) providing dashboards for both personas.
- Admin overview endpoints for monitoring user mix and revenue metrics.
- Unit tests covering the core business rules for tiers, quoting, and billing.

## Getting Started

1. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. **Install standard library requirements:** No third-party dependencies are required.
3. **Run the automated tests:**
   ```bash
   python -m unittest discover
   ```
4. **Start the development server:**
   ```bash
   python -m marketplace.server
   ```
5. **Open the web client:** visit [http://localhost:8000](http://localhost:8000) in your browser.

The server persists data to `marketplace/marketplace.db`. Delete this file to reset the environment.

## Project Structure

```
marketplace/
  __init__.py
  auth.py
  database.py
  router.py
  server.py
  services.py
  tiers.py
frontend/
  index.html
  styles.css
  app.js
tests/
  test_services.py
```

## Deployment

Refer to [DEPLOYMENT.md](DEPLOYMENT.md) for a complete guide covering environment variables, database migrations, and process management. The application is designed to run on any WSGI-friendly platform such as Heroku, Render, or AWS EC2.

## User Manual

See [USER_MANUAL.md](USER_MANUAL.md) for homeowner and contractor walkthroughs, including onboarding checklists and messaging best practices.
