"""Script to randomly populate marital_status and dateofbirth for existing candidates.

Run: python update_random_demographics.py
Options can be configured at the top of the script or passed as command line args.
"""

import os
import random
import sys
from datetime import datetime, timedelta
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Config
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "cvextraction"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "admin123"),
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": os.getenv("DB_PORT", "5433"),
}

# Configuration
DRY_RUN = False  # Set to True to preview updates without writing to database
MARITAL_STATUS_OPTIONS = ["Lajang", "Menikah", "Cerai"]  # Indonesian marital statuses

# Realistic birth year range for candidates (e.g., ages 21 to 46 in 2026)
START_BIRTH_YEAR = 1980
END_BIRTH_YEAR = 2005


def generate_random_date_of_birth(start_year: int, end_year: int) -> datetime:
    """Generate a random birthdate between January 1st of start_year and December 31st of end_year."""
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days)
    return random_date


def run_update():
    print("=" * 60)
    print("      RANDOM CANDIDATE DEMOGRAPHICS GENERATOR      ")
    print("=" * 60)
    print(f"Database     : {DB_CONFIG['dbname']} on {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Dry Run Mode : {'[ENABLED] (No changes will be saved)' if DRY_RUN else '[DISABLED] (Changes WILL be saved)'}")
    print(f"Age Range    : {START_BIRTH_YEAR} to {END_BIRTH_YEAR} (approx. {2026 - END_BIRTH_YEAR} - {2026 - START_BIRTH_YEAR} years old)")
    print(f"Statuses     : {', '.join(MARITAL_STATUS_OPTIONS)}")
    print("=" * 60 + "\n")

    try:
        # Establish connection
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Fetch all candidates
        cur.execute("SELECT requireid, firstname, lastname, marital_status, dateofbirth FROM require WHERE is_delete = FALSE ORDER BY requireid")
        candidates = cur.fetchall()

        if not candidates:
            print("[WARNING] No active candidates found in 'require' table.")
            cur.close()
            conn.close()
            return

        total_candidates = len(candidates)
        print(f"[INFO] Found {total_candidates} active candidates to process.\n")

        status_counts = {status: 0 for status in MARITAL_STATUS_OPTIONS}
        updated_count = 0
        
        print(f"{'ID':<6} | {'Candidate Name':<25} | {'Old Status -> New Status':<35} | {'Old DOB -> New DOB'}")
        print("-" * 100)

        for cid, first, last, old_status, old_dob in candidates:
            name = f"{first or ''} {last or ''}".strip()
            
            # Generate random status & DOB
            new_status = random.choice(MARITAL_STATUS_OPTIONS)
            new_dob = generate_random_date_of_birth(START_BIRTH_YEAR, END_BIRTH_YEAR)
            
            # Keep count of generated statuses
            status_counts[new_status] += 1
            
            # Format old info for printing
            old_status_str = old_status if old_status else "NULL"
            old_dob_str = old_dob.strftime("%Y-%m-%d") if old_dob else "NULL"
            new_dob_str = new_dob.strftime("%Y-%m-%d")

            print(f"{cid:<6} | {name:<25} | {old_status_str:<6} -> {new_status:<26} | {old_dob_str:<10} -> {new_dob_str}")

            if not DRY_RUN:
                cur.execute(
                    """
                    UPDATE require 
                    SET marital_status = %s, dateofbirth = %s 
                    WHERE requireid = %s
                    """,
                    (new_status, new_dob, cid)
                )
            
            updated_count += 1

        # Summary
        print("-" * 100)
        print("\nUPDATE SUMMARY REPORT:")
        print(f"  - Total Candidates Processed : {updated_count}")
        print("  - Marital Status Distribution:")
        for status, count in status_counts.items():
            percentage = (count / updated_count * 100) if updated_count > 0 else 0
            print(f"    * {status:<10}: {count} candidates ({percentage:.1f}%)")

        if DRY_RUN:
            print("\n[SUCCESS] Dry run completed successfully. No changes were committed to the database.")
            cur.close()
            conn.close()
        else:
            conn.commit()
            cur.close()
            conn.close()
            print("\n[SUCCESS] Database updated successfully! All changes have been committed.")

    except psycopg2.OperationalError as e:
        print(f"\n[ERROR] Database Connection Error: Could not connect to PostgreSQL server.")
        print(f"Details: {e}")
        print("\nPlease make sure Docker container is running and port 5433 is accessible.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if user wants dry-run from args
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["--dry-run", "dry-run", "dry"]:
        DRY_RUN = True
    elif len(sys.argv) > 1 and sys.argv[1].lower() in ["--apply", "apply", "run"]:
        DRY_RUN = False
        
    run_update()
