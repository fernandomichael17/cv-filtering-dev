"""Deep diagnostic: inspect all tags_jobs data and show what ISCO codes they map to."""
import asyncio
from collections import Counter
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.config import settings
from core.utils.taxonomy import TITLE_TO_ISCO

async def diagnose():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        # 1. Get ALL tags_jobs
        result = await session.execute(text("SELECT tags FROM tags_jobs WHERE tags IS NOT NULL"))
        rows = result.fetchall()
        
        print(f"=== Total tags_jobs records: {len(rows)} ===\n")
        
        categories = Counter()
        roles = Counter()
        isco_results = Counter()
        unknown_roles = []
        
        for row in rows:
            raw = row[0].strip()
            parts = [p.strip() for p in raw.split(",")]
            
            if len(parts) >= 2:
                category = parts[0]
                role = parts[1]
            elif len(parts) == 1:
                category = "N/A"
                role = parts[0]
            else:
                continue
            
            categories[category] += 1
            roles[role] += 1
            
            # Try ISCO lookup
            role_lower = role.lower()
            if role_lower in TITLE_TO_ISCO:
                isco_results["MATCH (exact)"] += 1
            else:
                # Try partial
                found = False
                for alias in TITLE_TO_ISCO:
                    if alias in role_lower or role_lower in alias:
                        found = True
                        break
                if found:
                    isco_results["MATCH (partial)"] += 1
                else:
                    isco_results["UNKNOWN"] += 1
                    unknown_roles.append(f"  [{category}] {role}")
        
        print("--- CATEGORIES (Tag 1) ---")
        for cat, count in categories.most_common():
            print(f"  {cat}: {count}")
        
        print(f"\n--- UNIQUE ROLES: {len(roles)} ---")
        print(f"--- Top 20 roles ---")
        for r, count in roles.most_common(20):
            r_lower = r.lower()
            isco = TITLE_TO_ISCO.get(r_lower, "???")
            print(f"  {r} (x{count}) -> ISCO: {isco}")
        
        print(f"\n--- ISCO MATCHING STATS ---")
        for k, v in isco_results.items():
            print(f"  {k}: {v}")
        
        print(f"\n--- ALL UNKNOWN ROLES ({len(unknown_roles)}) ---")
        for u in sorted(set(unknown_roles)):
            print(u)
        
        # 2. Also check the job posting
        result = await session.execute(text("SELECT id, title, tags FROM job_postings LIMIT 5"))
        jobs = result.fetchall()
        print(f"\n--- JOB POSTINGS ---")
        for job in jobs:
            print(f"  ID={job[0]}, Title='{job[1]}', Tags={job[2]}")

if __name__ == "__main__":
    asyncio.run(diagnose())
