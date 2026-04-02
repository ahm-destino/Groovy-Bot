# System Architecture - Grooovy Bot + Webapp Integration

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           END USERS                                 │
│                                                                     │
│  ┌──────────────────┐              ┌──────────────────┐           │
│  │  WhatsApp Users  │              │   Web Users      │           │
│  │  (Mobile/Desktop)│              │   (Browser)      │           │
│  └────────┬─────────┘              └────────┬─────────┘           │
└───────────┼──────────────────────────────────┼─────────────────────┘
            │                                  │
            │                                  │
┌───────────▼──────────────────────────────────▼─────────────────────┐
│                      PRESENTATION LAYER                             │
│                                                                     │
│  ┌──────────────────┐              ┌──────────────────┐           │
│  │  WhatsApp Cloud  │              │  Grooovy Webapp  │           │
│  │      API         │              │   (Netlify)      │           │
│  │                  │              │                  │           │
│  │  • Send/Receive  │              │  • React UI      │           │
│  │  • Interactive   │              │  • User Auth     │           │
│  │  • Media         │              │  • Event Mgmt    │           │
│  └────────┬─────────┘              └────────┬─────────┘           │
└───────────┼──────────────────────────────────┼─────────────────────┘
            │                                  │
            │ Webhooks                         │ Supabase Client
            │                                  │
┌───────────▼──────────────────────────────────▼─────────────────────┐
│                      APPLICATION LAYER                              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────┐         │
│  │           Grooovy WhatsApp Bot (FastAPI)             │         │
│  │                                                       │         │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │         │
│  │  │  Webhook    │  │  AI Engine  │  │  Services   │ │         │
│  │  │  Handler    │  │             │  │             │ │         │
│  │  │             │  │  • Claude   │  │  • Events   │ │         │
│  │  │  • Verify   │  │  • Intent   │  │  • Bookings │ │         │
│  │  │  • Route    │  │  • Entities │  │  • Payments │ │         │
│  │  │  • Process  │  │  • Context  │  │  • Tickets  │ │         │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │         │
│  │                                                       │         │
│  │  ┌─────────────────────────────────────────────────┐│         │
│  │  │         Background Jobs (Celery)                ││         │
│  │  │                                                  ││         │
│  │  │  • Cleanup expired bookings (5 min)            ││         │
│  │  │  • Process location reveals (hourly)           ││         │
│  │  │  • Send reminders (24hr, 1hr)                  ││         │
│  │  └─────────────────────────────────────────────────┘│         │
│  └──────────────────────────────────────────────────────┘         │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            │ Both connect to same DB
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                         DATA LAYER                                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              Supabase (PostgreSQL + PostGIS)                 │ │
│  │                                                               │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐│ │
│  │  │ Shared Tables  │  │ Shared Tables  │  │  Bot Tables    ││ │
│  │  │                │  │  (Extended)    │  │                ││ │
│  │  │  • users       │  │  • events      │  │  • conversations││ │
│  │  │  • bookings    │  │    + anonymous │  │  • message_logs││ │
│  │  │  • tickets     │  │  • bookings    │  │  • access_logs ││ │
│  │  │                │  │    + source    │  │                ││ │
│  │  └────────────────┘  └────────────────┘  └────────────────┘│ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                    EXTERNAL SERVICES                                │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │  Anthropic   │  │   Paystack   │  │  Cloudinary  │            │
│  │   (Claude)   │  │  (Payments)  │  │  (QR Codes)  │            │
│  │              │  │              │  │              │            │
│  │  • Intent    │  │  • Cards     │  │  • Upload    │            │
│  │  • NLU       │  │  • USSD      │  │  • Generate  │            │
│  │  • Context   │  │  • Transfer  │  │  • Store     │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow: WhatsApp Booking → Webapp Visibility

```
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: User Books via WhatsApp                                    │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
User: "Book 2 tickets for Davido concert"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ WhatsApp Cloud API → Bot Webhook                                   │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ AI Engine: Classify Intent = "book_ticket"                         │
│ Extract Entities: quantity=2, event="Davido concert"               │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Booking Service:                                                    │
│ 1. Create booking in database                                       │
│    - booking_source = 'whatsapp'                                    │
│    - phone = "+2348012345678"                                       │
│    - status = 'pending'                                             │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Payment Service:                                                    │
│ 1. Initialize Paystack transaction                                  │
│ 2. Send payment link via WhatsApp                                   │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
User completes payment on Paystack
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Paystack Webhook → Bot                                             │
│ Event: charge.success                                               │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Booking Service:                                                    │
│ 1. Update booking: status = 'confirmed'                             │
│ 2. Generate tickets (QR codes)                                      │
│ 3. Send tickets via WhatsApp                                        │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SHARED DATABASE (Supabase)                                         │
│                                                                     │
│ bookings table:                                                     │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ id: abc-123                                                   │  │
│ │ user_id: user-456                                             │  │
│ │ event_id: event-789                                           │  │
│ │ phone: "+2348012345678"                                       │  │
│ │ quantity: 2                                                   │  │
│ │ total_amount: 30000                                           │  │
│ │ status: 'confirmed'                                           │  │
│ │ booking_source: 'whatsapp' ← TAGGED AS WHATSAPP             │  │
│ │ payment_reference: 'GRV-ABC123'                               │  │
│ └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: User Logs into Webapp                                      │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
User opens webapp → Login → My Tickets
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Webapp Query:                                                       │
│ SELECT * FROM bookings WHERE user_id = 'user-456'                  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Webapp UI:                                                          │
│                                                                     │
│ My Tickets                                                          │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ Davido Live in Concert                                        │  │
│ │ 2 tickets • ₦30,000                                           │  │
│ │ 📱 WhatsApp ← BADGE SHOWS SOURCE                             │  │
│ │ [View Tickets] [Request Refund]                               │  │
│ └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
✅ User sees WhatsApp booking in webapp!
```

## Component Interaction: Event Creation

```
┌─────────────────────────────────────────────────────────────────────┐
│ Organizer: "Create event" (via WhatsApp)                           │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Bot: Multi-turn Conversation Flow                                  │
│                                                                     │
│ Step 1: Event name?                                                 │
│ Step 2: Category?                                                   │
│ Step 3: Date/time?                                                  │
│ Step 4: Location type? (public/secret)                             │
│ Step 5: Reveal timing?                                              │
│ Step 6: Address?                                                    │
│ Step 7: Entry code?                                                 │
│ Step 8: Capacity?                                                   │
│ Step 9: Price?                                                      │
│ Step 10: Description?                                               │
│ Step 11: Confirm?                                                   │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Event Creation Service:                                             │
│ 1. Create event in database                                         │
│    - created_via = 'whatsapp'                                       │
│    - is_anonymous = true                                            │
│    - secret_code = 'TECH2026'                                       │
│    - location_reveal_trigger = 'time_based'                         │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SHARED DATABASE                                                     │
│                                                                     │
│ events table:                                                       │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ id: event-789                                                 │  │
│ │ host_id: user-456                                             │  │
│ │ title: "Tech Founders Dinner"                                 │  │
│ │ is_anonymous: true                                            │  │
│ │ secret_code: "TECH2026"                                       │  │
│ │ location_reveal_hours_before: 1                               │  │
│ │ created_via: 'whatsapp' ← TAGGED AS WHATSAPP                │  │
│ └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Organizer logs into webapp                                          │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Webapp: My Events                                                   │
│                                                                     │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ Tech Founders Dinner                                          │  │
│ │ 🔒 Secret Event • 🤖 Created via WhatsApp                    │  │
│ │ Secret Code: TECH2026 [Copy]                                  │  │
│ │ Location reveals: 1hr before                                  │  │
│ │ Tickets sold: 15/50                                           │  │
│ │ [Edit] [View Analytics] [Broadcast Message]                   │  │
│ └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
✅ Organizer manages WhatsApp-created event in webapp!
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYERS                             │
└─────────────────────────────────────────────────────────────────────┘

Layer 1: Transport Security
├── WhatsApp: End-to-end encryption
├── Webapp: HTTPS/TLS
└── Database: SSL connections

Layer 2: Authentication
├── WhatsApp: Phone number verification (Meta)
├── Webapp: Email/password + JWT
└── Bot: Service role key (Supabase)

Layer 3: Authorization (Row Level Security)
├── Users can only see their own bookings
├── Organizers can only manage their own events
└── Bot bypasses RLS (service_role)

Layer 4: Data Validation
├── Webhook signature verification (WhatsApp, Paystack)
├── Input sanitization (SQL injection prevention)
└── Rate limiting (prevent abuse)

Layer 5: Payment Security
├── PCI DSS compliant (Paystack)
├── No card data stored
└── Webhook signature verification
```

## Scalability Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SCALING STRATEGY                               │
└─────────────────────────────────────────────────────────────────────┘

Current (0-10K users):
├── Single FastAPI instance
├── Supabase free tier
├── Redis single instance
└── Celery 1 worker

Phase 1 (10K-100K users):
├── Horizontal scaling (3-5 FastAPI instances)
├── Supabase Pro tier
├── Redis cluster
├── Celery 3-5 workers
└── Load balancer

Phase 2 (100K-1M users):
├── Auto-scaling (10+ instances)
├── Database read replicas
├── Redis Cluster
├── Celery auto-scaling
├── CDN for QR codes
└── Message queue (RabbitMQ)

Phase 3 (1M+ users):
├── Microservices architecture
├── Database sharding
├── Distributed caching
├── Event-driven architecture
└── Multi-region deployment
```

## Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MONITORING STACK                               │
└─────────────────────────────────────────────────────────────────────┘

Application Metrics:
├── Response time (target: <200ms)
├── Error rate (target: <1%)
├── Throughput (messages/sec)
└── AI classification accuracy

Business Metrics:
├── Active users (daily/monthly)
├── Bookings by source (webapp vs whatsapp)
├── Conversion rate (discovery → booking)
└── Revenue (GMV)

Infrastructure Metrics:
├── CPU/Memory usage
├── Database connections
├── Queue depth (Celery)
└── API rate limits

Alerts:
├── Error rate > 5%
├── Response time > 1s
├── Payment failures > 10%
└── Database connection errors
```

---

**Architecture Status**: ✅ Production Ready

**Last Updated**: February 2026