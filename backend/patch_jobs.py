"""
Patch existing jobs with missing stage, salary, sector, founder info.
Run: python patch_jobs.py
"""

import asyncio
import httpx

BASE_URL      = "https://mitra-production-5d7d.up.railway.app"
ADMIN_KEY     = "8297713c6369687734581073585768662b35315030404a667a5449586a346a30"
FOUNDER_EMAIL = "shindeharshal338@gmail.com"

# Full PUT payloads for each job id (all fields required by JobIn)
PATCHES: list[tuple[int, dict]] = [

    # ── Founder-onboarded jobs (fix stack + salary + sector) ──────────────────

    (16, {
        "external_id":    "founder:264b3ec6-29a6-4159-a816-e48800a5c1f7",
        "title":          "Senior Backend Engineer",
        "company":        "Letter.ai",
        "stage":          "Series B",
        "sector":         "AI / SaaS",
        "location":       "Remote",
        "remote_policy":  "remote",
        "employment":     "full_time",
        "salary_min_lpa": 28,
        "salary_max_lpa": 45,
        "stack":          ["Python", "FastAPI", "LLMs", "PostgreSQL", "Redis"],
        "signals":        ["backend-heavy", "ai-first", "remote-first", "high-ownership"],
        "summary":        (
            "Letter.ai is building AI-native writing tools for enterprise teams. "
            "You'll own core backend services — APIs, data pipelines, and LLM integrations "
            "that power the product. End-to-end ownership from day one."
        ),
        "founder_name":   "Rohan Mehta",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),

    (15, {
        "external_id":    "founder:bf314cd5-08a3-4d07-9b20-43449241dda3",
        "title":          "ML Engineer",
        "company":        "Practical.ai",
        "stage":          "Series B",
        "sector":         "Artificial Intelligence",
        "location":       "Remote",
        "remote_policy":  "remote",
        "employment":     "full_time",
        "salary_min_lpa": 35,
        "salary_max_lpa": 58,
        "stack":          ["Python", "PyTorch", "MLflow", "FastAPI", "AWS", "LLMs"],
        "signals":        ["ml-engineering", "ai-first", "production-ml", "remote-first"],
        "summary":        (
            "Practical.ai builds ML tooling that helps engineering teams ship models faster "
            "with less operational overhead. You'll own the model pipeline end-to-end — "
            "from experimentation to production serving. High ownership, remote-first culture."
        ),
        "founder_name":   "Ananya Singh",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),

    (13, {
        "external_id":    "founder:30720a1c-1d10-42a9-90dd-e686105bb87b",
        "title":          "ML Engineer — Research",
        "company":        "Auren Labs",
        "stage":          "Pre-seed",
        "sector":         "AI Research",
        "location":       "Remote",
        "remote_policy":  "remote",
        "employment":     "full_time",
        "salary_min_lpa": 15,
        "salary_max_lpa": 28,
        "stack":          ["Python", "PyTorch", "Transformers", "CUDA", "HuggingFace"],
        "signals":        ["research-engineering", "ai-first", "frontier-models", "pre-seed"],
        "summary":        (
            "Auren Labs is a research-first AI startup working on next-generation language "
            "model architectures. You'll own the full pipeline from design to deployment — "
            "research implementation, training runs, and production serving. "
            "Ideal for someone who wants to do real research with real-world impact."
        ),
        "founder_name":   "Priya Rajan",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),

    # ── Original mock jobs (add stage + salary + sector + founder) ────────────

    (10, {
        "external_id":    "mtr-010",
        "title":          "Applied Scientist — Recommendations",
        "company":        "Velvet Retail",
        "stage":          "Series B",
        "sector":         "E-commerce",
        "location":       "Bengaluru",
        "remote_policy":  "hybrid",
        "employment":     "full_time",
        "salary_min_lpa": 32,
        "salary_max_lpa": 52,
        "stack":          ["Python", "PyTorch", "Spark", "Airflow", "Kafka"],
        "signals":        ["ml-engineering", "recommendations", "e-commerce", "high-scale"],
        "summary":        (
            "Velvet Retail is India's fastest-growing fashion marketplace — think curated "
            "discovery, not just search. You'll own ranking and personalisation for catalog "
            "and search, build A/B infrastructure, and run causal readouts that directly "
            "drive GMV. Real scale, real ML impact."
        ),
        "founder_name":   "Shruti Kapoor",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),

    (9, {
        "external_id":    "mtr-009",
        "title":          "Distributed Systems Engineer",
        "company":        "Quasar Streams",
        "stage":          "Series A",
        "sector":         "Infrastructure",
        "location":       "Remote",
        "remote_policy":  "remote",
        "employment":     "full_time",
        "salary_min_lpa": 35,
        "salary_max_lpa": 55,
        "stack":          ["Java", "Rust", "Kafka", "Elasticsearch", "Kubernetes"],
        "signals":        ["distributed-systems", "infra", "remote-first", "high-scale"],
        "summary":        (
            "Quasar Streams is building the next generation of real-time data infrastructure "
            "for enterprises. You'll work on high-throughput log ingestion with exactly-once "
            "guarantees and tame backpressure across regions. If you care deeply about "
            "correctness at scale, this is your role."
        ),
        "founder_name":   "Vikram Nair",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),

    (8, {
        "external_id":    "mtr-008",
        "title":          "Product Engineer — Growth",
        "company":        "OrbitRide",
        "stage":          "Series B",
        "sector":         "Mobility",
        "location":       "Dubai",
        "remote_policy":  "hybrid",
        "employment":     "full_time",
        "salary_min_lpa": 30,
        "salary_max_lpa": 48,
        "stack":          ["React", "TypeScript", "Node.js", "PostgreSQL", "Amplitude"],
        "signals":        ["fullstack", "growth-engineering", "mobility", "consumer"],
        "summary":        (
            "OrbitRide is the leading ride-hailing platform across the Gulf, expanding fast. "
            "You'll ship experiments across the onboarding and retention funnel, tighten "
            "analytics loops with data partners, and own features that move north-star metrics. "
            "Based in Dubai — relocation support provided."
        ),
        "founder_name":   "Khalid Al-Rashid",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),

    (6, {
        "external_id":    "mtr-006",
        "title":          "Mobile Engineer — Flutter",
        "company":        "CareLoop Health",
        "stage":          "Series A",
        "sector":         "Health Tech",
        "location":       "Bengaluru",
        "remote_policy":  "hybrid",
        "employment":     "full_time",
        "salary_min_lpa": 18,
        "salary_max_lpa": 30,
        "stack":          ["Flutter", "Dart", "Firebase", "REST", "BLoC"],
        "signals":        ["mobile", "health-tech", "consumer", "product-engineering"],
        "summary":        (
            "CareLoop is building patient-first apps that make chronic disease management "
            "feel less clinical and more human. You'll polish offline flows, build secure "
            "messaging between patients and care teams, and own accessibility across the "
            "app. Work that genuinely improves people's health outcomes."
        ),
        "founder_name":   "Dr. Meera Iyer",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),

    (5, {
        "external_id":    "mtr-005",
        "title":          "Senior Data Engineer",
        "company":        "Riverbend Analytics",
        "stage":          "Series A",
        "sector":         "Analytics / B2B SaaS",
        "location":       "Remote",
        "remote_policy":  "remote",
        "employment":     "full_time",
        "salary_min_lpa": 25,
        "salary_max_lpa": 42,
        "stack":          ["Python", "Spark", "dbt", "Snowflake", "Airflow"],
        "signals":        ["data-engineering", "analytics", "b2b-saas", "remote-first"],
        "summary":        (
            "Riverbend Analytics powers the data layer for mid-market SaaS companies — "
            "think Mixpanel-meets-warehouse for teams that outgrew spreadsheets. "
            "You'll build CDC pipelines and dimensional models that power leadership "
            "metrics and experimentation. High-ownership, remote-first, async culture."
        ),
        "founder_name":   "Arjun Tiwari",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),

    (4, {
        "external_id":    "mtr-004",
        "title":          "Lead Platform Engineer — Kubernetes",
        "company":        "Northwind Telemetry",
        "stage":          "Series B",
        "sector":         "Infrastructure / DevOps",
        "location":       "Remote",
        "remote_policy":  "remote",
        "employment":     "full_time",
        "salary_min_lpa": 35,
        "salary_max_lpa": 58,
        "stack":          ["Kubernetes", "Go", "Terraform", "GCP", "Prometheus"],
        "signals":        ["platform-engineering", "infra", "devops", "remote-first"],
        "summary":        (
            "Northwind Telemetry runs observability infrastructure for data-heavy enterprise "
            "workloads across Europe and India. You'll run multi-tenant Kubernetes fleets, "
            "harden CI/CD, and own on-call rotations. If you want to build the platform "
            "other engineers rely on, this is the role."
        ),
        "founder_name":   "Lars Eriksen",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),

    (12, {
        "external_id":    "mtr-012",
        "title":          "Developer Relations Engineer",
        "company":        "Helix CLI",
        "stage":          "Series A",
        "sector":         "Developer Tools",
        "location":       "Remote",
        "remote_policy":  "remote",
        "employment":     "full_time",
        "salary_min_lpa": 20,
        "salary_max_lpa": 35,
        "stack":          ["TypeScript", "Node.js", "Python", "SDK design", "Technical writing"],
        "signals":        ["devrel", "dev-tools", "remote-first", "community"],
        "summary":        (
            "Helix CLI is building the developer-first terminal toolkit that's replacing "
            "legacy shell scripts at fast-moving engineering teams. You'll build sample apps "
            "and tutorials, tighten the DX feedback loop with the OSS community, and be "
            "the first DevRel hire. High ownership, fully remote."
        ),
        "founder_name":   "Samuel Osei",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),

    (11, {
        "external_id":    "mtr-011",
        "title":          "Frontend Engineer — Design Systems",
        "company":        "PaperStudio",
        "stage":          "Seed",
        "sector":         "Design Tools",
        "location":       "Remote",
        "remote_policy":  "remote",
        "employment":     "contract",
        "salary_min_lpa": 16,
        "salary_max_lpa": 26,
        "stack":          ["React", "TypeScript", "Storybook", "CSS", "Web Accessibility"],
        "signals":        ["frontend", "design-systems", "remote-first", "contract"],
        "summary":        (
            "PaperStudio is building a multi-brand design system used across a portfolio of "
            "content and e-commerce sites. You'll own the component library and token system, "
            "partner with design on motion and accessibility, and set the standard for UI "
            "quality across teams. Contract role with strong renewal potential."
        ),
        "founder_name":   "Isabelle Chen",
        "founder_email":  FOUNDER_EMAIL,
        "founder_wa":     None,
    }),
]


async def patch() -> None:
    headers = {
        "X-Admin-Key": ADMIN_KEY,
        "Content-Type": "application/json",
    }
    updated = failed = 0

    async with httpx.AsyncClient(timeout=60) as client:
        for job_id, payload in PATCHES:
            try:
                r = await client.put(
                    f"{BASE_URL}/admin/jobs/{job_id}",
                    json=payload,
                    headers=headers,
                )
                if r.status_code in (200, 201):
                    print(f"OK   id={job_id}  {payload['title']} @ {payload['company']}")
                    updated += 1
                else:
                    print(f"ERR  id={job_id}  {payload['company']}  {r.status_code}  {r.text[:120]}")
                    failed += 1
            except Exception as exc:
                print(f"EXC  id={job_id}  {payload['company']}  {exc}")
                failed += 1

    print(f"\nDone — updated={updated}  failed={failed}")


if __name__ == "__main__":
    asyncio.run(patch())
