#!/usr/bin/env python3
"""Apply and validate bounded SEO fixes after a Webflow HTML export (stdlib only)."""
import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://nathanlittle.com.au"
EXCLUDED = {"404.html", "thank-you.html"}
JSON_LD = re.compile(r'(<script\b[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>)(.*?)(</script>)', re.S | re.I)
CANONICAL = re.compile(r'<link\b(?=[^>]*\brel=[\"\']canonical[\"\'])[^>]*>\s*', re.I)
ROBOTS_META = re.compile(r'<meta\b(?=[^>]*\bname=[\"\']robots[\"\'])[^>]*>\s*', re.I)


def pages():
    return sorted(p for p in ROOT.rglob("*.html")
                  if not any(part.startswith(".") or part in {"node_modules", "scripts"}
                             for part in p.relative_to(ROOT).parts))


def url(path):
    relative = path.relative_to(ROOT).as_posix()
    return ORIGIN + ("/" if relative == "index.html" else "/" + relative)


def visible_offers(source):
    # Read the actual pricing headings and next visible price; never infer a package.
    body = re.split(r'<body\b[^>]*>', source, maxsplit=1, flags=re.I)[-1]
    result = []
    for match in re.finditer(r'<h5\b[^>]*>([^<]*Website Package)</h5>(.{0,350}?)\$([\d,]+)', body, re.S):
        result.append({"@type": "Offer", "name": html.unescape(match[1]),
                       "price": match[3].replace(",", ""), "priceCurrency": "AUD"})
    if len(result) != 2 or {x["name"] for x in result} != {"Standard Website Package", "Pro Website Package"}:
        raise ValueError("Expected exactly the two visible website packages; review the new export")
    return result


def social_profiles(source):
    # Footer links are the existing visible source of truth, not guessed handles.
    footer = source[source.find('class="footer"'):]
    links = re.findall(r'<a\b[^>]*href="(https://[^\"]+)"', footer)
    hosts = {"www.facebook.com", "www.instagram.com", "www.linkedin.com", "www.threads.com",
             "www.tiktok.com", "www.youtube.com", "x.com", "bsky.app"}
    return list(dict.fromkeys(html.unescape(link) for link in links if urlsplit(link).netloc in hosts))


def transform_schema(value, offers, profiles):
    if isinstance(value, list):
        return [transform_schema(item, offers, profiles) for item in value]
    if not isinstance(value, dict):
        return value
    value = {key: transform_schema(item, offers, profiles) for key, item in value.items()}
    if "sameAs" in value and value.get("name") == "Nathan Little":
        value["sameAs"] = profiles
    if offers and value.get("@type") == "ProfessionalService" and "offers" in value:
        value["offers"] = offers
        value.pop("priceRange", None)  # Website prices do not establish a whole-business price range.
    return value


def prepare_page(path, source, profiles):
    relative = path.relative_to(ROOT).as_posix()
    offers = visible_offers(source) if relative in {"index.html", "website-design.html"} else None

    def schema(match):
        raw = match[2]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Known Webflow export error: offers array closed with } instead of ].
            repaired = re.sub(r'(\n\s*})\s*\n\s*}\s*\n\s*}\s*\n\s*}\s*$', r'\1\n    ]\n  }\n}', raw)
            if relative != "website-design.html" or repaired == raw:
                raise ValueError(f"Unexpected invalid JSON-LD in {relative}; repair explicitly")
            data = json.loads(repaired)
        data = transform_schema(data, offers, profiles)
        if relative == "website-design.html" and data.get("@type") == "WebPage":
            data["name"] = "Website Design Services | Nathan Little"
            data["url"] = url(path)
            data["description"] = "Website design services and packages for sole traders, small businesses and non-profit organisations."
        # Align existing page identities with the exported URL format.
        if data.get("@type") in {"ContactPage", "AboutPage", "WebPage"}:
            data["url"] = url(path)
        return match[1] + "\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n" + match[3]

    source = JSON_LD.sub(schema, source)
    source = CANONICAL.sub("", source)
    additions = f'<link rel="canonical" href="{url(path)}">\n'
    if relative in EXCLUDED:
        source = ROBOTS_META.sub("", source)
        additions += '<meta name="robots" content="noindex, follow">\n'
    return re.sub(r'</head>', additions + '</head>', source, count=1, flags=re.I)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate without modifying files")
    args = parser.parse_args()
    paths = pages()
    profiles = social_profiles((ROOT / "index.html").read_text())
    if len(profiles) < 5:
        raise ValueError("Visible footer social links changed; review before generating schema")
    outputs = {path: prepare_page(path, path.read_text(), profiles) for path in paths}
    sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for path in paths:
        if path.relative_to(ROOT).as_posix() not in EXCLUDED:
            ET.SubElement(ET.SubElement(sitemap, "url"), "loc").text = url(path)
    ET.indent(sitemap, space="  ")
    outputs[ROOT / "sitemap.xml"] = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(sitemap, encoding="unicode") + "\n"
    outputs[ROOT / "robots.txt"] = "User-agent: *\nAllow: /\n\nSitemap: " + ORIGIN + "/sitemap.xml\n"
    changed = []
    for path, expected in outputs.items():
        if not path.exists() or path.read_text() != expected:
            changed.append(path.relative_to(ROOT).as_posix())
            if not args.check:
                path.write_text(expected)
    if args.check and changed:
        parser.exit(1, "Export preparation required: " + ", ".join(changed) + "\n")
    print(f"{'Validated' if args.check else 'Prepared'} {len(paths)} HTML pages; "
          f"{len(paths) - len(EXCLUDED)} sitemap URLs; {len(changed)} files {'need changes' if args.check else 'updated'}.")


if __name__ == "__main__":
    main()
