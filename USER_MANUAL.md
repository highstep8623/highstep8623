# RenovaHub User Manual

This guide explains how homeowners and contractors can make the most of the RenovaHub marketplace.

## 1. Getting Started

### Account Creation
1. Visit `http://localhost:8000` (or your deployed domain).
2. Use the **Register** panel to create an account as a homeowner or contractor.
3. After registering, you are automatically logged in and redirected to your dashboard.
4. Existing users can sign in via the **Login** panel.

### Email Verification
The current implementation auto-verifies accounts. In production, integrate a transactional email service (e.g., SendGrid) and trigger verification messages using the data stored in `users.is_verified`.

## 2. Homeowner Experience

### Posting a Project
1. Navigate to the **Homeowner Dashboard**.
2. Complete the **Post a Project** form with title, description, budget, timeline, and location.
3. Submit to publish the project. Basic tier users can only maintain one active project at a time.
4. Upload URLs to project photos by extending the payload (UI stores up to 10 links).

### Managing Quotes
- View submitted quotes by selecting **View Quotes** on a project.
- Each quote displays contractor details, pricing, and notes.
- Choose **Accept** to move forward. The system marks the project as `in_progress`, stores the acceptance timestamp, and generates a contractor invoice for the acceptance fee.
- Choose **Decline** to notify the contractor and keep the project open.

### Messaging & Reviews
- Use the **Messages** panel (coming from API) to view project conversations. Contractors and homeowners can exchange updates, files, and clarifications.
- After a project is `in_progress` or `completed`, leave a review highlighting quality, communication, and timeliness.

### Upgrading Plans
- Navigate to the account dropdown (UI hook) or call `POST /api/subscriptions/upgrade` with your new tier and billing cycle.
- Upgrades immediately adjust project/quote limits and create a subscription record for billing.

## 3. Contractor Experience

### Completing Onboarding
1. Register as a contractor and supply business name, service areas, and specialties.
2. Add licence or insurance documentation by extending the profile payload in future iterations.
3. Verified contractors receive a badge shown in homeowner search results.

### Bidding on Projects
- From the **Available Projects** list, click **Submit Quote**.
- Provide a numeric amount, short scope summary, and timeline. Tier limits apply per calendar month.
- Monitor the **Submitted Quotes** section for status changes (submitted, accepted, declined).
- When a quote is accepted, an invoice is generated for the acceptance fee percentage.

### Analytics & Reviews
- The contractor dashboard summarises submitted/accepted quotes and aggregate reviews.
- Use reviews to improve service quality; high-rated contractors are prioritised in homeowner searches.

### Subscription Upgrades
- Call `POST /api/subscriptions/upgrade` with `tier` (`starter`, `growth`, `elite`) and `billing_cycle` (`monthly` or `annual`).
- Plan changes adjust quote allowances and visibility features instantly.

## 4. Messaging & Notifications

- Messaging endpoints (`/api/homeowner/messages`, `/api/contractor/messages`) return ordered conversation threads.
- Integrate email/SMS notifications by consuming the same endpoints and hooking into an external provider.

## 5. Payments

- Accepted quotes create `invoices` with category `accepted_quote_fee`. Use `POST /api/payments` to mark them as paid via Stripe/PayPal webhooks.
- Subscription purchases also generate invoices and can be tracked via the same endpoint.
- Escrow releases and milestone payments can extend the schema by referencing project milestones.

## 6. Admin Operations

- Admin users (role `admin`) can call `GET /api/admin/overview` to review user mix and tier adoption.
- Extend the admin experience by creating additional endpoints for dispute management, refunds, or verification workflows.

## 7. Tips & Best Practices

- Maintain accurate profiles to improve matching quality.
- Upload before/after photos using hosted image URLs to showcase workmanship.
- Respond to messages quickly; response time influences ranking in search results.
- Encourage satisfied homeowners to leave reviews to build trust.

## 8. Support

Contact support by sending an email to `support@renovahub.example` (placeholder). Provide project ID, user email, and a detailed description for faster assistance.
