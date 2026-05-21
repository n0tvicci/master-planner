# E-commerce AI Automation — System Design Spec

**Date:** 2026-05-22
**Project:** Digital Sorcery — E-commerce Automation as a Service
**Status:** Approved

---

## 1. Product Overview

An **Automation as a Service** web platform for e-commerce sellers. The platform provides three AI-powered products:

| Product | What it does |
|---|---|
| **AI Text Writer** | Generates SEO-optimized product titles, descriptions, and bullet points |
| **AI Image Generator** | Transforms a seller's raw product photo into a professional product image |
| **AI Video Generator** | Converts uploaded product images into a short product video clip |

**Business model:** The platform operator holds all AI provider API keys and charges clients by purchasing credit packs. Clients never manage API keys. All AI usage costs are covered by the platform and marked up 2–3× in credit pricing.

---

## 2. Target Users

- **Individual e-commerce sellers** — solo operators with a personal workspace
- **Businesses / agencies** — team workspaces with multiple members sharing a credit pool

Both user types are supported from day one. A personal workspace is auto-created on signup; team workspaces can be created and members invited at any time.

---

## 3. Architecture

### 3.1 Approach

**Modular Monolith + Job Queue**

A single Node.js/Express application organized into clean modules, backed by a Redis + BullMQ job queue for asynchronous AI processing. AI generation tasks (especially video, which can take 2–5 minutes) are handled as background jobs — the API returns a `job_id` immediately and the client receives results via WebSocket when the job completes.

This approach was chosen over a simple monolith (which would block HTTP threads on slow AI calls) and microservices (which would be over-engineered for the current team size and stage).

### 3.2 Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite (SPA) |
| Backend | Node.js + Express |
| Database | PostgreSQL |
| Job Queue | Redis + BullMQ |
| File Storage | Cloudflare R2 (S3-compatible) |
| Payments | Stripe |
| Real-time | WebSocket (Socket.io or ws) |

### 3.3 System Layers

```
┌─────────────────────────────────────────────────────────┐
│              React Vite SPA (Vercel)                    │
│  Auth · Workspaces · Text · Image · Video · Billing     │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS / WebSocket
┌────────────────────▼────────────────────────────────────┐
│           Node.js / Express API (Railway)                │
│  ┌──────────┐ ┌────────────┐ ┌─────────┐ ┌──────────┐  │
│  │  auth    │ │ workspaces │ │ billing │ │  jobs    │  │
│  └──────────┘ └────────────┘ └─────────┘ └──────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │ Enqueue + deduct credits atomically
┌────────────────────▼────────────────────────────────────┐
│        Redis + BullMQ (Railway)                         │
│   text-queue    image-queue    video-queue              │
└──────┬──────────────┬────────────────┬──────────────────┘
       │              │                │
┌──────▼───┐   ┌──────▼───┐   ┌───────▼──┐
│  Text    │   │  Image   │   │  Video   │
│  Worker  │   │  Worker  │   │  Worker  │
└──────┬───┘   └──────┬───┘   └───────┬──┘
       └──────────────┴────────────────┘
                       │ Provider Adapter
┌──────────────────────▼──────────────────────────────────┐
│                  AI Providers (platform keys)            │
│  OpenAI · Anthropic · Stability AI · Runway · Kling     │
└─────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  PostgreSQL · Redis · Cloudflare R2                     │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Multi-Tenancy & Auth

### 4.1 Core Entities

**User**
- `id` (uuid), `email` (unique), `password_hash`, `created_at`
- One user can belong to many workspaces

**Workspace**
- `id` (uuid), `name`, `slug` (unique), `type` (personal | team)
- `credit_balance` (integer, denormalized cache), `stripe_customer_id`
- Credits and billing live on the workspace, not the user
- `credit_balance` is updated atomically on every ledger write (fast reads). The `credit_ledger` table is the source of truth — `credit_balance` must always equal `SUM(credit_ledger.amount)` for the workspace
- Personal workspace auto-created on signup

**WorkspaceMember** (join table)
- `user_id`, `workspace_id`, `role` (owner | admin | member), `joined_at`

### 4.2 Roles (RBAC)

| Permission | Owner | Admin | Member |
|---|---|---|---|
| All product access | ✓ | ✓ | ✓ |
| View credit balance | ✓ | ✓ | ✓ |
| Buy credit packs | ✓ | ✓ | ✗ |
| Invite members | ✓ | ✓ | ✗ |
| Remove members | ✓ | ✓ | ✗ |
| Delete workspace | ✓ | ✗ | ✗ |

### 4.3 Auth Flow

1. User signs up → personal workspace auto-created → JWT issued containing `user_id` + `active_workspace_id`
2. JWT stored in an **httpOnly cookie** (never in localStorage — prevents XSS token theft)
3. Every API request resolves user + workspace + role in a single DB query via JWT middleware
4. Workspace switch → new JWT issued with updated `workspace_id`
5. Team invites: signed token (48h expiry) sent by Owner/Admin → invitee clicks link → joins as Member

---

## 5. Credit System & Billing

### 5.1 Credit Pack Pricing (tunable)

| Pack | Price | Credits | Notes |
|---|---|---|---|
| Starter | $10 | 500 cr | Base pack |
| Growth | $25 | 1,500 cr | +20% bonus |
| Pro | $50 | 3,500 cr | +40% bonus |

Credit pack definitions are stored in the database — new packs can be added without code changes.

### 5.2 Per-Job Credit Cost

| Job Type | Credits | Approx. AI Cost | Approx. Markup |
|---|---|---|---|
| Text (title + description) | 10 cr | ~$0.01 | ~2× |
| Image (1 image) | 20 cr | ~$0.04 | ~2.5× |
| Video (short clip) | 100 cr | ~$0.25 | ~2× |

Costs are approximate and should be re-tuned against actual provider invoices.

### 5.3 Credit Ledger Schema

The `credit_ledger` table is **append-only** — rows are never updated, only inserted. The workspace balance is always `SUM(amount)` for the workspace.

```
credit_ledger
├── id              uuid PK
├── workspace_id    FK → workspace
├── user_id         FK → user (who triggered)
├── type            purchase | consumption | refund
├── amount          integer (+/-)
├── job_id          FK → job (nullable)
├── stripe_payment_id  nullable
└── created_at      timestamp
```

### 5.4 Purchase Flow

1. Owner/Admin selects a credit pack → Stripe Checkout session created server-side
2. Stripe fires `checkout.session.completed` webhook → credits inserted into ledger
3. Credits are never added on redirect (redirects can be faked)

### 5.5 Consumption Rule

Credits are deducted and the job enqueued in a **single DB transaction**. If either operation fails, both roll back. No double-spend, no free jobs.

If a job fails after credits are deducted, a refund entry is automatically inserted into the ledger.

---

## 6. AI Automation Pipeline

### 6.1 Job Lifecycle (all products)

1. Client submits form + optional uploads → API validates, deducts credits + enqueues atomically → returns `job_id` immediately
2. BullMQ worker picks up job → status → `processing` → provider adapter calls active AI provider
3. **Success:** result stored → status → `completed` → client notified via WebSocket
4. **Failure:** BullMQ retries 3× with exponential backoff → if exhausted → status `failed` → credits auto-refunded → client notified

**Job statuses:** `queued` → `processing` → `completed` | `failed`

### 6.2 Jobs Table Schema

```
jobs
├── id               uuid PK
├── workspace_id     FK
├── user_id          FK
├── type             text | image | video
├── status           queued | processing | completed | failed
├── input_payload    jsonb
├── result_payload   jsonb (nullable)
├── provider_used    string
├── credits_charged  integer
├── error_message    text (nullable)
├── created_at       timestamp
└── completed_at     timestamp (nullable)
```

### 6.3 Per-Product Inputs & Outputs

**Text Writer**

| | |
|---|---|
| Input | Product name, basic product details, marketplace (Shopify / Amazon / Shopee) |
| Output | SEO title (≤80 chars), product description (HTML-ready), 5 bullet points |
| Note | Marketplace selection shapes tone, length, and format rules (e.g. Amazon title limits) |

**Image Generator**

| | |
|---|---|
| Input | Raw product image (upload), style (studio / lifestyle / minimalist), background color or scene, aspect ratio (1:1 / 4:3 / 16:9) |
| Output | Professional product image, signed download URL (R2/S3) |
| Note | Image-to-image transformation — no prompt engineering required from the seller |

**Video Generator**

| | |
|---|---|
| Input | Product images (1–5 uploads), motion style (rotate / zoom / showcase), duration (3s / 5s / 10s), target platform (TikTok / Reels / YouTube) |
| Output | Product video clip, signed download URL (R2/S3) |
| Note | Platform selection automatically sets aspect ratio and output format |

### 6.4 Provider Adapter Pattern

All three workers call a shared `AIProvider` interface, never the provider SDK directly:

```ts
interface AIProvider {
  generate(payload: JobPayload): Promise<GenerationResult>
}
```

Active provider per product is set via environment variables:
- `ACTIVE_TEXT_PROVIDER=openai` (or `anthropic`)
- `ACTIVE_IMAGE_PROVIDER=dalle3` (or `stability`, `ideogram`)
- `ACTIVE_VIDEO_PROVIDER=runway` (or `kling`, `pika`)

Swapping providers requires no code changes — only a config update and redeploy.

**Supported providers:**

| Product | Providers |
|---|---|
| Text | OpenAI GPT-4o, Anthropic Claude |
| Image | OpenAI DALL-E 3, Stability AI, Ideogram |
| Video | Runway ML, Kling AI, Pika Labs |

---

## 7. Deployment

### 7.1 Phase 1 — Demo (now)

| Service | Platform | Notes |
|---|---|---|
| React SPA | Vercel | Free tier, auto-deploys from git |
| Express API | Railway | ~$5/mo hobby tier |
| PostgreSQL | Railway | Managed, same project |
| Redis | Railway | Managed, same project |
| File storage | Cloudflare R2 | S3-compatible, free egress |
| Payments | Stripe | Test mode for demo |

**Estimated cost: ~$5–15/mo**

### 7.2 Phase 2 — AWS Production

| Demo Service | AWS Equivalent | Migration Effort |
|---|---|---|
| Vercel | CloudFront + S3 | Easy — build and upload |
| Railway API | ECS Fargate + ALB | Medium — Dockerize app |
| Railway Workers | ECS Fargate (separate service) | Easy — same Docker image |
| Railway Redis | ElastiCache | Easy — update `REDIS_URL` |
| Railway PostgreSQL | RDS PostgreSQL (Multi-AZ) | Easy — pg_dump + restore |
| Cloudflare R2 | AWS S3 | Easy — same SDK, update env vars |
| Env vars | AWS Secrets Manager | Easy — inject via ECS task definition |

**Estimated cost: ~$80–150/mo at small scale**

The only Medium-effort migration step is containerizing the Express app with Docker. All other steps are connection string or environment variable swaps. No code rewrites are required.

### 7.3 AWS Architecture (Phase 2)

```
Internet
    │
CloudFront CDN
    │
    ├── React SPA (S3)
    │
    └── ALB (Application Load Balancer)
            │
        ECS Fargate
            ├── API containers (auto-scale)
            └── Worker containers (text / image / video — scale independently)
                        │
              ┌─────────┴─────────┐
          ElastiCache         RDS PostgreSQL
          (Redis)             (Multi-AZ)
                        │
                    AWS S3
                    AWS Secrets Manager
```

---

## 8. Security Considerations

- **httpOnly cookies** for JWT storage — prevents XSS token theft
- **Stripe webhook signature verification** — all webhook events verified before processing
- **Atomic credit transactions** — deduction and job enqueue in a single DB transaction
- **Signed URLs for asset delivery** — generated files are private; short-lived signed URLs for download
- **AI provider keys in Secrets Manager** — never in code or environment files in production
- **RBAC enforced server-side** — role checked on every API route, not just in the frontend
- **Input validation** — all job inputs validated before credit deduction or queue enqueue

---

## 9. Non-Goals (Out of Scope for V1)

- BYOK (Bring Your Own Key) mode — may be added later for enterprise clients
- Subscription tiers — credit packs only for V1
- Bulk job processing / CSV upload
- Custom AI model fine-tuning
- Mobile app
- Analytics dashboard for platform operator (added later)
