import json, os, sys, requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_jobs.json"

INCLUDE_KEYWORDS = [
    "devops", "systems integration", "build and release", "release engineer",
    "cloud operations", "cloud ops", "devops support", "environment management",
    "ci/cd", "deployment engineer"
]
EXCLUDE_KEYWORDS = [
    "architect", "principal", "director", "staff", "manager", "head of",
    "distinguished", "vp ", "lead "
]
CITIES = ["chennai", "bengaluru", "bangalore", "hyderabad"]

SMARTRECRUITERS_SLUGS = ["NielsenIQ", "BoschGroup", "Visa"]
GREENHOUSE_SLUGS = ["thoughtworks", "epamsystems"]
LEVER_SLUGS = ["xebia"]
# (display name, full host, tenant, site id) - host/site ids are best guesses;
# check the Actions log for "ERROR Workday" lines and correct any that fail.
WORKDAY_TARGETS = [
    ("Trimble", "trimble.wd1.myworkdayjobs.com", "trimble", "TrimbleCareers"),
    ("Kyndryl", "kyndryl.wd5.myworkdayjobs.com", "kyndryl", "KyndrylProfessionalCareers"),
    ("DXC", "dxctechnology.wd1.myworkdayjobs.com", "dxctechnology", "DXCJobs"),
    ("Cognizant", "cognizant.wd1.myworkdayjobs.com", "cognizant", "CognizantCareers"),
]


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def send_telegram(msg):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "disable_web_page_preview": True},
        timeout=15,
    )
    if not r.ok:
        print(f"ERROR Telegram {r.status_code}: {r.text}")
    return r.ok


def is_match(title, location):
    t, l = title.lower(), location.lower()
    if any(bad in t for bad in EXCLUDE_KEYWORDS):
        return False
    return any(k in t for k in INCLUDE_KEYWORDS) and any(c in l for c in CITIES)


def fetch_all():
    results = []

    for slug in SMARTRECRUITERS_SLUGS:
        try:
            data = requests.get(
                f"https://api.smartrecruiters.com/v1/companies/{slug}/postings",
                params={"q": "DevOps", "limit": 100}, timeout=15,
            ).json()
            for j in data.get("content", []):
                city = j.get("location", {}).get("city", "")
                if is_match(j.get("name", ""), city):
                    results.append((
                        f"SR-{slug}-{j['id']}",
                        f"{slug}: {j['name']} ({city})",
                        f"https://jobs.smartrecruiters.com/{slug}/{j['id']}",
                    ))
        except Exception as e:
            print(f"ERROR SmartRecruiters {slug}: {e}")

    for slug in GREENHOUSE_SLUGS:
        try:
            data = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=15
            ).json()
            for j in data.get("jobs", []):
                loc = j.get("location", {}).get("name", "")
                if is_match(j.get("title", ""), loc):
                    results.append((
                        f"GH-{slug}-{j['id']}",
                        f"{slug.title()}: {j['title']} ({loc})",
                        j["absolute_url"],
                    ))
        except Exception as e:
            print(f"ERROR Greenhouse {slug}: {e}")

    for slug in LEVER_SLUGS:
        try:
            data = requests.get(
                f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=15
            ).json()
            for j in data:
                loc = j.get("categories", {}).get("location", "") or ""
                if is_match(j.get("text", ""), loc):
                    results.append((
                        f"LV-{slug}-{j['id']}",
                        f"{slug.title()}: {j['text']} ({loc})",
                        j["hostedUrl"],
                    ))
        except Exception as e:
            print(f"ERROR Lever {slug}: {e}")

    for name, host, tenant, site_id in WORKDAY_TARGETS:
        try:
            for term in ["DevOps", "Release", "Cloud Operations"]:
                res = requests.post(
                    f"https://{host}/wday/cxs/{tenant}/{site_id}/jobs",
                    json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": term},
                    timeout=15,
                ).json()
                for j in res.get("jobPostings", []):
                    loc = j.get("locationsText", "")
                    if is_match(j.get("title", ""), loc):
                        path = j.get("externalPath", "")
                        results.append((
                            f"WD-{name}-{path}",
                            f"{name}: {j['title']} ({loc})",
                            f"https://{host}/en-US/{site_id}{path}",
                        ))
        except Exception as e:
            print(f"ERROR Workday {name}: {e}")

    return results


def main():
    if "--test" in sys.argv or os.environ.get("TEST_TELEGRAM") == "true":
        ok = send_telegram("✅ Job watcher test: Telegram is connected.")
        print("Test message sent." if ok else "Test message FAILED.")
        return

    seen = load_seen()
    jobs = fetch_all()
    print(f"Matched {len(jobs)} jobs; {len([j for j in jobs if j[0] not in seen])} new.")
    for job_id, label, link in jobs:
        if job_id not in seen:
            if send_telegram(f"🚨 NEW PRACTICAL DEVOPS ROLE:\n{label}\nApply: {link}"):
                seen.add(job_id)  # only mark seen if the alert actually went out
    save_seen(seen)


if __name__ == "__main__":
    main()
