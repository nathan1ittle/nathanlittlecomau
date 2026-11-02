# Preparing a Webflow export

Keep the exported HTML, CSS, JavaScript and assets in this repository's root.
After replacing them with a fresh export, run:

```sh
python3 scripts/prepare_export.py
python3 scripts/prepare_analytics.py
python3 scripts/prepare_export.py --check
python3 scripts/prepare_analytics.py --check
node tests/analytics.mjs
```

The preparation script adds one canonical URL per page, generates `robots.txt`
and `sitemap.xml`, and excludes the 404 and thank-you pages from the sitemap.
Those two pages receive `noindex, follow`. Existing `.html` page URLs are
retained; the homepage canonical is `/`.

It also repairs the known website-design JSON-LD array error, derives the two
website package offers from their visible headings and prices, and aligns
Nathan Little social-profile schema with the existing homepage footer links.
Unexpected schema errors or pricing structure changes stop the script for
review. It does not rewrite layouts, form embeds, tracking or external assets.

The separate analytics preparation restores the existing GitHub-compatible GA4
loader when it recognises the original Webflow export format. A changed format
stops for review. It adds `generate_lead` to the existing HubSpot enquiry form's
`onFormSubmitted` callback, which fires after successful submission. It sends
only the fixed form ID to GA4, never names, emails, messages or submission values.
Page views, failed validation and submit-button clicks are not leads. Analytics
errors are caught so they cannot prevent the normal enquiry confirmation.

Keep `scripts/`, `tests/`, `.github/` and this guide when replacing exported files.
CI checks prepared output; it never modifies or publishes the site. GitHub Pages
continues to publish the repository root from `main`. Review and merge changes
using your normal publishing process.

## Analytics follow-up

After publishing, verify an authorised successful test submission in GA4
DebugView/Realtime and HubSpot. Local tests simulate callbacks and never send a
real enquiry. Mark `generate_lead` as a GA4 key event once the tracking is live.
The old `contact_us` and `ads_conversion_Contact_Us_1` rules both match contact-page
views. They are not confirmed leads. Review their Google Ads usage before
changing or retiring them; do not add their counts to confirmed submissions.

Weekly and monthly PDF summaries were scheduled in GA4 to
`nathan@nathanlittle.com.au`, starting 9 November and 1 December 2026, respectively,
for 12 months. They use the last 7 and last 28 days. Descriptions record the
existing contact-event limitation. Google notes that associated Gmail addresses
can receive reports instead when both addresses belong to the same Analytics
user: https://support.google.com/analytics/answer/13722168

Search Console was not linked: the signed-in account offered no verified
properties. Verify this domain in Search Console, link it to stream 5192231231,
and submit the sitemap after publication. Event retention is currently 2 months
(user retention 14 months); consider 14-month event retention if it fits the
site's privacy policy and analysis needs. Standard aggregate reports are not
limited by that event-retention setting.

Review the diff before publishing. Check live canonical tags, sitemap access,
HTTPS redirects, and successful enquiry tracking after deployment. Redirects
must be configured at the hosting layer: canonical tags alone do not redirect
duplicate routes or HTTP requests. Submit the sitemap in Search Console after
it is live. A future export can overwrite these generated fixes; rerun the
commands above every time.
