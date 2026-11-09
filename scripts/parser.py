#!/usr/bin/env python3
"""
ADMEXA News Parser
Runs via GitHub Actions every 6 hours.
Output: output/news.json + output/digest.md
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import json
import time
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 20
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "7"))

RSS_SOURCES = [
    {"id": "step_blog", "name": "STEP Blog", "pillar": "Private capital, succession", "priority": "A",
     "url": "https://blog.step.org/feed/", "admexa_service": "Estate planning, succession"},
    {"id": "oecd_tax", "name": "OECD Taxation", "pillar": "Tax, international initiatives", "priority": "A",
     "url": "https://www.oecd.org/newsroom/taxation.xml", "admexa_service": "Tax & international structure"},
    {"id": "ecb", "name": "ECB Press", "pillar": "ECB decisions, banking", "priority": "A",
     "url": "https://www.ecb.europa.eu/rss/press.html", "admexa_service": "Banking architecture"},
    {"id": "esma", "name": "ESMA", "pillar": "EU markets regulation, MiCA", "priority": "A",
     "url": "https://www.esma.europa.eu/rss.xml", "admexa_service": "Capital structure, digital assets"},
    {"id": "fatf", "name": "FATF", "pillar": "AML/KYC, compliance", "priority": "A",
     "url": "https://www.fatf-gafi.org/en/the-fatf/news.rss", "admexa_service": "Compliance, banking"},
    {"id": "invest_europe", "name": "Invest Europe", "pillar": "Private equity, venture, funds", "priority": "A",
     "url": "https://www.investeurope.eu/feed/", "admexa_service": "Direct investments, capital"},
    {"id": "iea", "name": "IEA", "pillar": "Energy, projects", "priority": "B",
     "url": "https://www.iea.org/rssfeed.xml", "admexa_service": "Project strategy, energy"},
    {"id": "itij", "name": "ITIJ", "pillar": "Medical, international assistance", "priority": "B",
     "url": "https://www.itij.com/rss.xml", "admexa_service": "International life, healthcare"},
    {"id": "ukvi", "name": "UK Visas and Immigration", "pillar": "Visas, relocation", "priority": "B",
     "url": "https://www.gov.uk/government/organisations/uk-visas-and-immigration.atom",
     "admexa_service": "Relocation, international life"},
    {"id": "enisa", "name": "ENISA", "pillar": "Cybersecurity, AI, EU digital policy", "priority": "B",
     "url": "https://www.enisa.europa.eu/topics/enisa-news/SecurityNewsFeed",
     "admexa_service": "Technology, business risk"},
]

HTML_SOURCES = [
    {"id": "wealthbriefing", "name": "WealthBriefing", "pillar": "Private capital, family office", "priority": "A",
     "url": "https://www.wealthbriefing.com/html/index.php",
     "selectors": ["h2 a", "h3 a", ".article-title a", ".news-title a"],
     "base_url": "https://www.wealthbriefing.com", "admexa_service": "Family office, wealth"},
    {"id": "cysec", "name": "CySEC", "pillar": "Cyprus regulator", "priority": "A",
     "url": "https://www.cysec.gov.cy/en-GB/public-info/announcements/",
     "selectors": [".list-items a", "article a", "h3 a", "h4 a", ".announcement a"],
     "base_url": "https://www.cysec.gov.cy", "admexa_service": "Cyprus structures, compliance"},
    {"id": "kpmg_eu_tax", "name": "KPMG EU Tax Centre", "pillar": "EU taxes", "priority": "A",
     "url": "https://kpmg.com/xx/en/our-insights/eu-tax.html",
     "selectors": ["h3 a", "h4 a", ".card__title a", ".article-title a"],
     "base_url": "https://kpmg.com", "admexa_service": "Tax & international structure"},
    {"id": "penews", "name": "Private Equity News", "pillar": "PE, deals", "priority": "A",
     "url": "https://www.penews.com/",
     "selectors": ["h2 a", "h3 a", ".headline a", ".story-title a"],
     "base_url": "https://www.penews.com", "admexa_service": "Direct investments, funds"},
    {"id": "knightfrank", "name": "Knight Frank Research", "pillar": "Real estate", "priority": "B",
     "url": "https://www.knightfrank.com/research/reports",
     "selectors": ["h3 a", "h4 a", ".report-title a", ".card-title a"],
     "base_url": "https://www.knightfrank.com", "admexa_service": "Real estate, international assets"},
    {"id": "eu_digital", "name": "EU Digital Strategy", "pillar": "AI, EU digital policy", "priority": "B",
     "url": "https://digital-strategy.ec.europa.eu/en/news",
     "selectors": ["h3 a", "h4 a", ".ecl-content-item__title a", "article a"],
     "base_url": "https://digital-strategy.ec.europa.eu", "admexa_service": "Technology, regulation"},
    {"id": "ecia", "name": "ECIA News", "pillar": "Components, supply chains", "priority": "B",
     "url": "https://www.ecianow.org/news-and-alerts/",
     "selectors": ["h2 a", "h3 a", "article a", ".post-title a"],
     "base_url": "https://www.ecianow.org", "admexa_service": "Supply chain, projects"},
    {"id": "artbasel", "name": "Art Basel / UBS Art Market", "pillar": "Art market", "priority": "B",
     "url": "https://theartmarket.artbasel.com/",
     "selectors": ["h2 a", "h3 a", "article a", ".report-link"],
     "base_url": "https://theartmarket.artbasel.com", "admexa_service": "Art, collectibles, alternative assets"},
]


def parse_date(entry):
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def age_ok(dt):
    if dt is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    return dt >= cutoff


def clean(text, limit=400):
    if not text:
        return ""
    return " ".join(str(text).split())[:limit]


def strip_html(text):
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(separator=" ")


def fetch_rss(source):
    items = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        for e in feed.entries[:15]:
            dt = parse_date(e)
            if not age_ok(dt):
                continue
            title = clean(e.get("title", ""))
            link = e.get("link", "")
            summary = clean(strip_html(e.get("summary", "") or e.get("description", "")))
            if not title or not link:
                continue
            items.append({
                "source_id": source["id"], "source_name": source["name"],
                "pillar": source["pillar"], "priority": source["priority"],
                "admexa_service": source.get("admexa_service", ""),
                "title": title, "url": link, "summary": summary,
                "date": dt.strftime("%Y-%m-%d") if dt else "",
                "fetch_method": "RSS", "status": "new",
            })
        return items, "ok " + str(len(items)) + " items"
    except Exception as ex:
        return [], "err " + str(ex)[:80]


def fetch_html(source):
    items = []
    seen = set()
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for sel in source["selectors"]:
            for a in soup.select(sel):
                title = clean(a.get_text())
                href = a.get("href", "")
                if not href or not title or len(title) < 20:
                    continue
                if not href.startswith("http"):
                    href = source["base_url"].rstrip("/") + "/" + href.lstrip("/")
                if href in seen:
                    continue
                seen.add(href)
                items.append({
                    "source_id": source["id"], "source_name": source["name"],
                    "pillar": source["pillar"], "priority": source["priority"],
                    "admexa_service": source.get("admexa_service", ""),
                    "title": title, "url": href, "summary": "",
                    "date": "", "fetch_method": "HTML", "status": "new",
                })
                if len(items) >= 6:
                    break
            if len(items) >= 6:
                break
        return items, "ok " + str(len(items)) + " items"
    except Exception as ex:
        return [], "err " + str(ex)[:80]


def main():
    all_items = []
    log = []
    now = datetime.now(timezone.utc)
    print(f"ADMEXA Parser {now.strftime('%Y-%m-%d %H:%M')} UTC | MAX_AGE_DAYS={MAX_AGE_DAYS}")

    for src in RSS_SOURCES:
        items, status = fetch_rss(src)
        all_items.extend(items)
        log.append({"source": src["name"], "priority": src["priority"], "method": "RSS", "status": status})
        print(f"  [{src['priority']}] {src['name']}: {status}")
        time.sleep(0.5)

    for src in HTML_SOURCES:
        items, status = fetch_html(src)
        all_items.extend(items)
        log.append({"source": src["name"], "priority": src["priority"], "method": "HTML", "status": status})
        print(f"  [{src['priority']}] {src['name']}: {status}")
        time.sleep(1.0)

    ok_count = sum(1 for l in log if l["status"].startswith("ok"))
    total = len(RSS_SOURCES) + len(HTML_SOURCES)
    print(f"Sources OK: {ok_count}/{total} | Items: {len(all_items)}")

    os.makedirs("output", exist_ok=True)
    result = {
        "fetched_at": now.isoformat(),
        "fetched_at_human": now.strftime("%d %B %Y, %H:%M UTC"),
        "max_age_days": MAX_AGE_DAYS,
        "sources_ok": ok_count, "sources_total": total,
        "total_items": len(all_items), "items": all_items, "log": log,
    }
    with open("output/news.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    lines = [
        "# ADMEXA News Digest", "",
        f"**Collected:** {now.strftime('%d %B %Y, %H:%M')} UTC  ",
        f"**Sources:** {ok_count}/{total} available  ",
        f"**Items:** {len(all_items)}", "", "---", "",
    ]
    for priority in ("A", "B"):
        group = [i for i in all_items if i["priority"] == priority]
        if not group:
            continue
        lines.append(f"## Priority {priority}\n")
        seen_sources = list(dict.fromkeys(i["source_name"] for i in group))
        for src_name in seen_sources:
            src_items = [i for i in group if i["source_name"] == src_name]
            lines.append(f"### {src_name}")
            lines.append(f"*{src_items[0]['pillar']}*\n")
            for item in src_items:
                date_str = f" {item['date']}" if item["date"] else ""
                lines.append(f"- [{item['title']}]({item['url']}){date_str}")
            lines.append("")

    lines += ["---", "", "## Source log", "",
              "| Source | Priority | Method | Status |",
              "|--------|----------|--------|--------|"]
    for l in log:
        lines.append(f"| {l['source']} | {l['priority']} | {l['method']} | {l['status']} |")
    lines += ["", "---", "*Auto-generated by ADMEXA SMM Parser*"]

    with open("output/digest.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Saved: output/news.json + output/digest.md")
    return 0


if __name__ == "__main__":
    exit(main())
