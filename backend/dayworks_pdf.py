"""Renders a dayworks_entries row into a polished PDF (Jinja2 + WeasyPrint)."""
import re
from datetime import date, datetime

from jinja2 import Template
from weasyprint import HTML

TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 18mm 16mm; }
  * { box-sizing: border-box; }
  body { font-family: Arial, Helvetica, sans-serif; color: #1a1f27; font-size: 11px; margin: 0; }
  h1 { font-size: 18px; border-bottom: 2px solid #1a1f27; padding-bottom: 8px; margin: 0 0 14px; }
  h2 { font-size: 12.5px; margin: 0 0 6px; }
  .meta { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 14px; font-size: 11.5px; margin-bottom: 16px; }
  table { width: 100%; border-collapse: collapse; font-size: 10.5px; margin-bottom: 16px; }
  th, td { border: 1px solid #ccc; padding: 5px 6px; text-align: left; }
  th { background: #f3f4f6; }
  .comments { margin-bottom: 16px; white-space: pre-wrap; line-height: 1.5; }
  .photos { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
  .photos img { width: 80px; height: 80px; object-fit: cover; border: 1px solid #ccc; border-radius: 3px; }
  .signoff { border-top: 1px solid #ccc; padding-top: 12px; margin-top: 6px; }
  .sig-box { border: 1px dashed #ccc; border-radius: 4px; height: 70px; display: flex; align-items: center; justify-content: center; margin-top: 6px; }
  .sig-box img { max-height: 66px; }
  .sig-note { font-size: 10.5px; color: #9aa3b0; }
</style>
</head>
<body>
  <h1>Daily Labour Records</h1>
  <div class="meta">
    <div><b>Job Number / Name:</b> {{ job }}</div>
    <div><b>Date:</b> {{ entry_date }}</div>
    <div><b>Location:</b> {{ location_part }}</div>
    <div><b>Grid:</b> {{ grid_part }}</div>
    {% if vo_number %}<div><b>Variation No:</b> {{ vo_number }}</div>{% endif %}
    <div><b>Status:</b> {{ status }}</div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Name</th><th>Activity</th><th>Start</th><th>Finish</th><th>Total hours</th><th>Chargeable hours</th>
      </tr>
    </thead>
    <tbody>
      {% for row in labour_rows %}
      <tr>
        <td>{{ row.name }}</td>
        <td>{{ row.activity }}</td>
        <td>{{ row.start }}</td>
        <td>{{ row.end }}</td>
        <td>{{ row.hoursLabel }}</td>
        <td>{{ row.hoursLabel }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <h2>Materials</h2>
  <table>
    <thead><tr><th>Item</th><th>Unit</th><th>Qty</th></tr></thead>
    <tbody>
      {% for row in material_rows %}
      <tr><td>{{ row.item }}</td><td>{{ row.unit }}</td><td>{{ row.qty }}</td></tr>
      {% endfor %}
    </tbody>
  </table>

  {% if comments %}
  <h2>Comments</h2>
  <div class="comments">{{ comments }}</div>
  {% endif %}

  {% if photos %}
  <h2>Photos ({{ photos|length }})</h2>
  <div class="photos">
    {% for p in photos %}{% if p.src %}<img src="{{ p.src }}">{% endif %}{% endfor %}
  </div>
  {% endif %}

  <div class="signoff">
    <h2>Client sign off</h2>
    <div>Signature:</div>
    <div class="sig-box">
      {% if signature_data_url %}
        <img src="{{ signature_data_url }}">
      {% else %}
        <span class="sig-note">Signed remotely by client</span>
      {% endif %}
    </div>
    <div style="margin-top:8px">Name: {{ client_name or '—' }} &nbsp;&nbsp; Date: {{ entry_date }}</div>
  </div>
</body>
</html>
""")


def _fmt_date(value):
    if value is None:
        return '—'
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value)[:10]


def _location_parts(location):
    location = location or ''
    location_part = location.split('/')[0].strip() or '—'
    m = re.search(r'grid\s*(.+)$', location, re.IGNORECASE)
    if m:
        grid_part = m.group(1).strip()
    else:
        parts = location.split('·')
        grid_part = parts[1].strip() if len(parts) > 1 else ''
    return location_part, grid_part or '—'


def render_dayworks_pdf(entry: dict) -> bytes:
    """Render a dayworks_entries row (as returned from the DB, or the create payload) to PDF bytes."""
    location_part, grid_part = _location_parts(entry.get('location'))
    html = TEMPLATE.render(
        job=entry.get('job') or '—',
        entry_date=_fmt_date(entry.get('entry_date') or entry.get('date')),
        location_part=location_part,
        grid_part=grid_part,
        vo_number=entry.get('vo_number') if entry.get('variation') == 'Yes' else None,
        status=entry.get('status') or '—',
        labour_rows=entry.get('labour_rows') or [],
        material_rows=entry.get('material_rows') or [],
        comments=entry.get('comments'),
        photos=entry.get('photos') or [],
        signature_data_url=entry.get('signature_data_url'),
        client_name=entry.get('client_name'),
    )
    return HTML(string=html).write_pdf()
