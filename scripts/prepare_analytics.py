#!/usr/bin/env python3
"""Restore confirmed-enquiry tracking after a Webflow export (stdlib only)."""
from pathlib import Path
import argparse
import re

ROOT = Path(__file__).resolve().parents[1]
FORM_ID = '2db8aa91-057d-4827-9daf-8645717c5626'
START = '/* nl-confirmed-enquiry:start */'
END = '/* nl-confirmed-enquiry:end */'
CALLBACK = '''onFormSubmitted: function () {
      /* nl-confirmed-enquiry:start */
      // HubSpot calls this only after a successful submission. Never send field values.
      try {
        if (typeof window.gtag === "function") {
          window.gtag("event", "generate_lead", {
            send_to: "G-G27YDPP6Y2",
            form_id: "2db8aa91-057d-4827-9daf-8645717c5626",
            transport_type: "beacon"
          });
        }
      } catch (error) {
        // Analytics must never interrupt the enquiry confirmation.
      }
      /* nl-confirmed-enquiry:end */
    }'''
EMBED = re.compile(r'hbspt\.forms\.create\(\{(?P<config>.*?)\}\);', re.S)
GA_TAG = '''<script async src="https://www.googletagmanager.com/gtag/js?id=G-G27YDPP6Y2"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());gtag('config','G-G27YDPP6Y2');</script>'''
WEBFLOW_GA = re.compile(
    r'<script>\(function\(w,i,g\).*?google_tags_first_party.*?</script>'
    r'(?:<script\b[^>]*src="js/[^"/]+"[^>]*></script>){2}'
    r'<script\b[^>]*>window\.dataLayer\s*=.*?gtag\(\x27config\x27,\s*\x27UA-196586133-1\x27.*?</script>', re.S)


def prepare(source):
    source = WEBFLOW_GA.sub(GA_TAG, source)
    if 'https://www.googletagmanager.com/gtag/js?id=G-G27YDPP6Y2' not in source:
        raise ValueError('GA4 loader missing or Webflow tag format changed; review export')
    def update(match):
        config = match['config']
        if not re.search(r'formId\s*:\s*[\"\x27]' + FORM_ID, config):
            return match[0]
        if START in config:
            return match[0]
        if 'onFormSubmitted' in config:
            raise ValueError('Existing submission callback needs manual integration')
        return 'hbspt.forms.create({' + config.rstrip() + ',\n    ' + CALLBACK + '\n  });'
    return EMBED.sub(update, source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    count = 0
    for path in sorted(ROOT.rglob('*.html')):
        if any(part.startswith('.') for part in path.relative_to(ROOT).parts):
            continue
        original = path.read_text()
        prepared = prepare(original)
        if prepared != original:
            if args.check:
                raise SystemExit(f'Analytics export repair required: {path.relative_to(ROOT)}')
            path.write_text(prepared)
        count += prepared.count(START)
    if not count:
        raise SystemExit('No matching enquiry forms found; review the new export')
    print(f'Confirmed-enquiry tracking {"checked" if args.check else "prepared"}: {count} embeds')


if __name__ == '__main__':
    main()
