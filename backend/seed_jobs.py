"""
Seed 12 realistic Indian startup jobs into the Mitra database.
Run: python seed_jobs.py
"""

import asyncio
import httpx

BASE_URL   = "https://mitra-production-5d7d.up.railway.app"
ADMIN_KEY  = "8297713c6369687734581073585768662b35315030404a667a5449586a346a30"
FOUNDER_EMAIL = "shindeharshal338@gmail.com"

JOBS = [
    {
        "external_id": "mtr-101",
        "title": "Senior Backend Engineer",
        "company": "Setu",
        "stage": "Series A",
        "sector": "Fintech",
        "location": "Bengaluru",
        "remote_policy": "hybrid",
        "employment": "full_time",
        "salary_min_lpa": 28,
        "salary_max_lpa": 45,
        "stack": ["Python", "FastAPI", "PostgreSQL", "Redis", "Kafka"],
        "signals": ["backend-heavy", "fintech", "api-first", "infra"],
        "summary": (
            "Setu is building financial infrastructure for India — the plumbing that lets banks, "
            "fintechs, and enterprises launch products in days, not months. You'll own core API "
            "services that process millions of transactions daily. High-trust, high-impact backend "
            "work at a company changing how money moves in India."
        ),
        "full_jd": (
            "Design and build APIs that banks and fintechs rely on for payments, collections, and "
            "account aggregation. Strong Python/FastAPI background required. Experience with "
            "high-throughput systems and financial data is a big plus."
        ),
        "founder_name": "Madhusudhan Khemka",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-102",
        "title": "ML Engineer — LLM Products",
        "company": "Krutrim",
        "stage": "Series A",
        "sector": "Artificial Intelligence",
        "location": "Bengaluru",
        "remote_policy": "onsite",
        "employment": "full_time",
        "salary_min_lpa": 38,
        "salary_max_lpa": 70,
        "stack": ["Python", "PyTorch", "LLMs", "CUDA", "vLLM", "Triton"],
        "signals": ["ai-first", "llm", "research-engineering", "frontier-models"],
        "summary": (
            "Krutrim is Ola's AI lab — India's first unicorn focused entirely on building LLMs for "
            "Indian languages and use cases. You'll work on model training, fine-tuning, and "
            "inference infrastructure for models that will power the next generation of Indian AI "
            "products. This is frontier work, not application development."
        ),
        "full_jd": (
            "Work on LLM pre-training, RLHF, and inference optimization. Own parts of the model "
            "pipeline end-to-end. Strong PyTorch required. Experience with distributed training or "
            "inference optimization (vLLM, TGI, Triton) is a strong signal."
        ),
        "founder_name": "Agit Khatri",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-103",
        "title": "Senior Software Engineer — Backend",
        "company": "Jar",
        "stage": "Series B",
        "sector": "Fintech",
        "location": "Bengaluru",
        "remote_policy": "hybrid",
        "employment": "full_time",
        "salary_min_lpa": 30,
        "salary_max_lpa": 50,
        "stack": ["Java", "Kotlin", "Spring Boot", "Kafka", "PostgreSQL", "Redis"],
        "signals": ["backend-heavy", "fintech", "high-scale", "consumer"],
        "summary": (
            "Jar is India's largest micro-savings app — 11M+ users save spare change daily. "
            "You'll work on the core savings and payments backend, handling real-time money "
            "movement for millions of transactions daily. The scale is real, the ownership is "
            "real, and the impact is immediate."
        ),
        "full_jd": (
            "Own services that handle real-time money movement for 11M+ users. Build and maintain "
            "payment integrations and savings infrastructure. Strong Java/Kotlin required. "
            "Experience with event-driven architectures (Kafka) and high-throughput systems a plus."
        ),
        "founder_name": "Nischay AG",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-104",
        "title": "Backend Engineer — Health Data Platform",
        "company": "Ultrahuman",
        "stage": "Series B",
        "sector": "Health Tech",
        "location": "Bengaluru",
        "remote_policy": "hybrid",
        "employment": "full_time",
        "salary_min_lpa": 25,
        "salary_max_lpa": 42,
        "stack": ["Go", "PostgreSQL", "TimescaleDB", "Redis", "Kubernetes"],
        "signals": ["backend-heavy", "health-data", "iot", "wearables"],
        "summary": (
            "Ultrahuman makes the world's most advanced health wearables — the Ring AIR and "
            "metabolic monitor. You'll build the backend that ingests and processes billions of "
            "health data points from wearables globally. If you want to work on data pipelines "
            "that actually matter to people's lives, this is it."
        ),
        "full_jd": (
            "Own the data ingestion pipeline from wearable devices, build APIs consumed by mobile "
            "apps, and design storage architecture for time-series health data. Strong Go "
            "experience preferred. TimescaleDB or InfluxDB experience is a bonus."
        ),
        "founder_name": "Mohit Kumar",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-105",
        "title": "Senior ML Engineer — Conversational AI",
        "company": "Observe.AI",
        "stage": "Series B",
        "sector": "AI / SaaS",
        "location": "Bengaluru",
        "remote_policy": "hybrid",
        "employment": "full_time",
        "salary_min_lpa": 42,
        "salary_max_lpa": 68,
        "stack": ["Python", "PyTorch", "Transformers", "spaCy", "FastAPI", "AWS"],
        "signals": ["nlp", "conversational-ai", "b2b-saas", "production-ml"],
        "summary": (
            "Observe.AI is the intelligence layer for contact centres — their AI listens to every "
            "customer call and surfaces insights that improve agent performance. You'll build NLP "
            "models running in production on millions of real calls. Ship models that people "
            "actually use at scale."
        ),
        "full_jd": (
            "Own model development and productionization for speech and text understanding. "
            "Strong Python and PyTorch required. Experience with transformers, fine-tuning, and "
            "production model serving is essential."
        ),
        "founder_name": "Swapnil Jain",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-106",
        "title": "AI Engineer — Product",
        "company": "Sprinto",
        "stage": "Series B",
        "sector": "B2B SaaS",
        "location": "Bengaluru",
        "remote_policy": "hybrid",
        "employment": "full_time",
        "salary_min_lpa": 30,
        "salary_max_lpa": 52,
        "stack": ["Python", "LangChain", "OpenAI", "FastAPI", "PostgreSQL", "React"],
        "signals": ["ai-first", "b2b-saas", "llm", "product-engineering"],
        "summary": (
            "Sprinto is the fastest-growing compliance automation platform globally — they help "
            "SaaS companies get SOC 2, ISO 27001, and GDPR compliant in weeks. You'll build AI "
            "features that make compliance feel effortless. Applied LLM work on a B2B product "
            "with real paying customers."
        ),
        "full_jd": (
            "Build LLM-powered features end-to-end — prompt engineering to API and UI. Strong "
            "Python required. Experience with LangChain, RAG, or OpenAI APIs is essential."
        ),
        "founder_name": "Raghu Nandan",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-107",
        "title": "Full Stack Engineer",
        "company": "DhiWise",
        "stage": "Series A",
        "sector": "Developer Tools",
        "location": "Remote",
        "remote_policy": "remote",
        "employment": "full_time",
        "salary_min_lpa": 18,
        "salary_max_lpa": 32,
        "stack": ["React", "TypeScript", "Node.js", "PostgreSQL", "GraphQL"],
        "signals": ["fullstack", "dev-tools", "remote-first", "product-engineering"],
        "summary": (
            "DhiWise is building an AI-powered platform that lets developers build "
            "production-ready apps 10x faster. You'll work on the core product that thousands "
            "of developers use daily. Remote-first, high ownership, and you'll ship features "
            "that developers will actually rave about."
        ),
        "full_jd": (
            "Own features end-to-end — from design to production. Strong React and Node.js "
            "required. Experience with developer tooling or code generation is a big plus."
        ),
        "founder_name": "Chintan Patel",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-108",
        "title": "Backend Engineer",
        "company": "Leap Finance",
        "stage": "Series B",
        "sector": "Fintech",
        "location": "Bengaluru",
        "remote_policy": "hybrid",
        "employment": "full_time",
        "salary_min_lpa": 22,
        "salary_max_lpa": 38,
        "stack": ["Node.js", "TypeScript", "PostgreSQL", "Redis", "AWS"],
        "signals": ["backend-heavy", "fintech", "edtech", "payments"],
        "summary": (
            "Leap Finance helps Indian students fund their global education — they've disbursed "
            "over $200M in student loans. You'll build the financial infrastructure that makes "
            "this happen: loan origination, disbursement, and repayment systems. High stakes, "
            "meaningful work."
        ),
        "full_jd": (
            "Build and own loan management systems, payment integrations, and financial APIs. "
            "Strong Node.js/TypeScript required. Experience with lending or payments is a plus."
        ),
        "founder_name": "Arnav Kumar",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-109",
        "title": "Data Engineer",
        "company": "Credgenics",
        "stage": "Series B",
        "sector": "Fintech",
        "location": "Delhi NCR",
        "remote_policy": "remote",
        "employment": "full_time",
        "salary_min_lpa": 25,
        "salary_max_lpa": 40,
        "stack": ["Python", "Apache Spark", "Airflow", "dbt", "Snowflake", "PostgreSQL"],
        "signals": ["data-engineering", "fintech", "analytics", "remote-friendly"],
        "summary": (
            "Credgenics is India's leading debt resolution platform — they help banks and NBFCs "
            "recover loans efficiently using AI. You'll build the data infrastructure powering "
            "their ML models and business analytics. Work on data problems that directly move "
            "money and business outcomes."
        ),
        "full_jd": (
            "Design ETL pipelines, build data models, and enable analytics for business and ML "
            "teams. Strong Python and Spark or Airflow required. dbt experience is a strong plus."
        ),
        "founder_name": "Rishabh Goel",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-110",
        "title": "Backend Engineer — Platform",
        "company": "Plum",
        "stage": "Series B",
        "sector": "Insurtech",
        "location": "Bengaluru",
        "remote_policy": "hybrid",
        "employment": "full_time",
        "salary_min_lpa": 24,
        "salary_max_lpa": 40,
        "stack": ["Python", "FastAPI", "PostgreSQL", "Redis", "Celery", "AWS"],
        "signals": ["backend-heavy", "insurtech", "fintech", "product-engineering"],
        "summary": (
            "Plum is reinventing group health insurance for startups and SMEs — covering 3,000+ "
            "companies including some of the best startups in India. You'll build the insurance "
            "platform handling policy management, claims, and insurer integrations. Meaningful "
            "work in a sector that's badly needed disruption."
        ),
        "full_jd": (
            "Own services for policy management, claims processing, and third-party integrations. "
            "Strong Python/FastAPI required. Experience with async task queues (Celery) and "
            "financial data is a bonus."
        ),
        "founder_name": "Saurabh Arora",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-111",
        "title": "Senior Frontend Engineer",
        "company": "Niyo",
        "stage": "Series C",
        "sector": "Fintech",
        "location": "Bengaluru",
        "remote_policy": "hybrid",
        "employment": "full_time",
        "salary_min_lpa": 28,
        "salary_max_lpa": 45,
        "stack": ["React", "TypeScript", "Next.js", "GraphQL", "Tailwind CSS"],
        "signals": ["frontend", "fintech", "consumer", "product-engineering"],
        "summary": (
            "Niyo is the banking app for India's workforce and global travellers — 4M+ users and "
            "one of the fastest-growing neo-banks in India. You'll own critical consumer-facing "
            "features used by millions. Build a financial product that people actually love using."
        ),
        "full_jd": (
            "Own high-impact features end-to-end, from design collaboration to production. "
            "Strong React and TypeScript required. Experience with financial products or consumer "
            "apps at scale is a plus."
        ),
        "founder_name": "Vinay Bagri",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
    {
        "external_id": "mtr-112",
        "title": "Founding Engineer",
        "company": "Fibe",
        "stage": "Series C",
        "sector": "Fintech",
        "location": "Mumbai",
        "remote_policy": "hybrid",
        "employment": "full_time",
        "salary_min_lpa": 35,
        "salary_max_lpa": 60,
        "stack": ["Python", "Django", "PostgreSQL", "Redis", "Kafka", "AWS"],
        "signals": ["backend-heavy", "fintech", "consumer-lending", "high-ownership"],
        "summary": (
            "Fibe has disbursed over ₹10,000 crore in personal loans and is one of India's "
            "fastest-growing consumer lending platforms. This is a Founding Engineer-level role — "
            "you'll own a significant domain end-to-end with direct access to the CTO. "
            "High impact, high ownership, and meaningful ESOPs."
        ),
        "full_jd": (
            "Take end-to-end ownership of a major product domain — loan origination, credit "
            "decisioning, or payment infrastructure. Work directly with the CTO and leadership. "
            "Strong Python/Django required. Experience in lending, credit, or payments highly valued."
        ),
        "founder_name": "Akash Mehta",
        "founder_email": FOUNDER_EMAIL,
        "founder_wa": None,
    },
]


async def seed() -> None:
    headers = {
        "X-Admin-Key": ADMIN_KEY,
        "Content-Type": "application/json",
    }
    created = skipped = failed = 0

    async with httpx.AsyncClient(timeout=60) as client:
        for job in JOBS:
            try:
                r = await client.post(
                    f"{BASE_URL}/admin/jobs",
                    json=job,
                    headers=headers,
                )
                if r.status_code in (200, 201):
                    data = r.json()
                    print(f"OK   {job['title']} @ {job['company']}  id={data.get('id')}")
                    created += 1
                elif r.status_code == 409:
                    print(f"SKIP {job['company']} already exists")
                    skipped += 1
                else:
                    print(f"ERR  {job['company']} {r.status_code}")
                    print(f"     {r.text}")
                    failed += 1
            except Exception as exc:
                print(f"EXC  {job['company']} {exc}")
                failed += 1

    print(f"\nDone — created={created}  skipped={skipped}  failed={failed}")


if __name__ == "__main__":
    asyncio.run(seed())
