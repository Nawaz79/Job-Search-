import json, os, requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_jobs.json"

# Target practical, operational, and release-focused titles
INCLUDE_KEYWORDS = [
    "devops", "systems integration", "build and release", "release engineer",
    "cloud operations", "cloud ops", "devops support", "environment management",
    "ci/cd", "deployment engineer"
]

# Skip deep-architecture, principal, or heavy leadership loops
EXCLUDE_KEYWORDS = [
    "architect", "principal", "director", "staff", "manager", "head of",
    "distinguished", "vp ", "lead "
]

CITIES = ["chennai", "bengaluru", "bangalore", "hyderabad"]

# Official ATS company slugs (add 1 line per company)
SMARTRECRUITERS_SLUGS = ["NielsenIQ", "BoschGroup", "Visa"]
GREENHOUSE_SLUGS = ["thoughtworks", "epamsystems"]
LEVER_SLUGS = ["xebia"]
WORKDAY_TARGETS = [
    ("Trimble", "trimble", "TrimbleCareers", "https://myworkdayjobs.com"),
    ("Kyndryl", "kyndryl", "KyndrylCareers", "https://myworkdayjobs.com"),
    ("DXC", "dxc", "DXCJobs", "https://myworkdayjobs.com"),
    ("Cognizant", "cognizant", "CognizantCareers", "https://myworkdayjobs.com"),
]

def load_seen():
    return set(json.load(open(SEEN_FILE))) if os.path.exists(SEEN_FILE) else set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)

def send_telegram(msg):
    requests.post(
        f"https://telegram.org{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "disable_web_page_preview": True},
        timeout=15
    )

def is_match(title, location):
    t, l = title.lower(), location.lower()
    if any(bad in t for bad in EXCLUDE_KEYWORDS):
        return False
    return any(k in t for k in INCLUDE_KEYWORDS) and any(c in l for c in CITIES)

def fetch_all():
    results = []

    for slug in SMARTRECRUITERS_SLUGS:
        try:
            data = requests.get(f"https://smartrecruiters.com{slug}/postings?q=DevOps", timeout=12).json()
            for j in data.get("content", []):
                city = j.get("location", {}).get("city", "")
                if is_match(j.get("name", ""), city):
                    results.append((f"SR-{slug}-{j['id']}", f"{slug}: {j['name']} ({city})", f"https://smartrecruiters.com{slug}/{j['id']}"))
        except Exception:
            pass

    for slug in GREENHOUSE_SLUGS:
        try:
            data = requests.get(f"https://greenhouse.io{slug}/jobs", timeout=12).json()
            for j in data.get("jobs", []):
                loc = j.get("location", {}).get("name", "")
                if is_match(j.get("title", ""), loc):
                    results.append((f"GH-{slug}-{j['id']}", f"{slug.title()}: {j['title']} ({loc})", j["absolute_url"]))
        except Exception:
            pass

    for slug in LEVER_SLUGS:
        try:
            data = requests.get(f"https://lever.co{slug}?mode=json", timeout=12).json()
            for j in data:
                loc = j.get("categories", {}).get("location", "")
                if is_match(j.get("text", ""), loc):
                    results.append((f"LV-{slug}-{j['id']}", f"{slug.title()}: {j['text']} ({loc})", j["hostedUrl"]))
        except Exception:
            pass

    for name, tenant, site_id, base in WORKDAY_TARGETS:
        try:
            for term in ["DevOps", "Release", "Cloud Operations"]:
                res = requests.post(
                    f"{base}/wday/cxs/{tenant}/{site_id}/jobs",
                    json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": term},
                    timeout=12
                ).json()
                for j in res.get("jobPostings", []):
                    loc = j.get("locationsText", "")
                    if is_match(j.get("title", ""), loc):
                        path = j.get("externalPath", "")
                        results.append((f"WD-{name}-{path}", f"{name}: {j['title']} ({loc})", f"{base}/en-US/{site_id}{path}"))
        except Exception:
            pass

    return results

def main():
    seen = load_seen()
    for job_id, label, link in fetch_all():
        if job_id not in seen:
            seen.add(job_id)
            send_telegram(f"🚨 NEW PRACTICAL DEVOPS ROLE:\n{label}\nApply: {link}")
    save_seen(seen)

if __name__ == "__main__":
    main()
