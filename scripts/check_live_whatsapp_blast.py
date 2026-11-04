#!/usr/bin/env python3
"""
Live WhatsApp Blast Check - Last 15 minutes
Checks how many WhatsApp messages went out recently and to whom
"""
import sys, os, subprocess, json
from datetime import datetime, timedelta, timezone

# ── Odoo bootstrap ──────────────────────────────────────────────────────────
sys.path.insert(0, '/opt/odoo19/odoo')
sys.path.insert(0, '/opt/odoo19/custom_addons')
os.environ.setdefault('GEVENT_SUPPORT', 'True')

import odoo
from odoo.tools import config
config.parse_config(['-c', '/etc/odoo19.conf'])
odoo.cli.server.report_configuration()

registry = odoo.registry(config['db_name'])

with registry.cursor() as cr:
    from odoo.api import Environment
    import odoo.modules.registry
    uid = 1
    ctx = {'lang': 'en_US', 'tz': 'Asia/Kolkata', 'uid': uid}
    env = Environment(cr, uid, ctx)

    # IST = UTC+5:30
    now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    # Last 20 minutes
    since_ist = now_ist - timedelta(minutes=20)
    since_utc = since_ist.astimezone(timezone.utc).replace(tzinfo=None)

    print(f"\n{'='*80}")
    print(f" 📡 LIVE WhatsApp Blast Monitor")
    print(f" Checking messages from: {since_ist.strftime('%H:%M:%S IST')} to NOW ({now_ist.strftime('%H:%M:%S IST')})")
    print(f"{'='*80}")

    cr.execute("""
        SELECT
            m.id,
            (m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata') AS date_ist,
            m.phone_number,
            p.name AS author_name,
            l.id AS lead_id,
            l.partner_name AS lead_name,
            c.name AS company_name,
            LEFT(m.body, 80) AS body_preview
        FROM mail_message m
        LEFT JOIN res_partner p ON p.id = m.author_id
        LEFT JOIN crm_lead l ON l.id = m.res_id AND m.model = 'crm.lead'
        LEFT JOIN res_company c ON c.id = l.company_id
        WHERE m.message_type = 'whatsapp'
          AND m.date >= %s
          AND m.phone_number IS NOT NULL
        ORDER BY m.date DESC
        LIMIT 200
    """, (since_utc,))

    rows = cr.fetchall()
    cols = [d[0] for d in cr.description]

    if not rows:
        print("\n✅ Koi bhi WhatsApp message abhi nahi gaya last 20 minutes me.")
    else:
        print(f"\n⚠️  TOTAL MESSAGES SENT (Last 20 min): {len(rows)}\n")

        # Group by company
        from collections import defaultdict, Counter
        by_company = defaultdict(list)
        by_author = Counter()
        for row in rows:
            d = dict(zip(cols, row))
            by_company[d['company_name'] or 'Unknown'].append(d)
            by_author[d['author_name'] or 'System'] += 1

        print(f"{'─'*80}")
        print(f"📊 COMPANY-WISE BREAKDOWN:")
        print(f"{'─'*80}")
        for company, msgs in sorted(by_company.items(), key=lambda x: -len(x[1])):
            print(f"\n  🏢 {company}: {len(msgs)} messages")

        print(f"\n{'─'*80}")
        print(f"👤 SENDER-WISE BREAKDOWN:")
        print(f"{'─'*80}")
        for author, count in by_author.most_common():
            print(f"  • {author}: {count} messages")

        print(f"\n{'─'*80}")
        print(f"📋 DETAILED LOG (Most Recent First):")
        print(f"{'─'*80}")
        print(f"{'Time (IST)':<12} {'Lead ID':<8} {'Lead Name':<20} {'Phone':<14} {'Company':<20} {'Author':<18} Body Preview")
        print(f"{'-'*12} {'-'*8} {'-'*20} {'-'*14} {'-'*20} {'-'*18} {'-'*40}")
        for row in rows:
            d = dict(zip(cols, row))
            time_str = d['date_ist'].strftime('%H:%M:%S') if d['date_ist'] else '?'
            lead_name = (d['lead_name'] or '')[:19]
            company = (d['company_name'] or '')[:19]
            author = (d['author_name'] or '')[:17]
            phone = (d['phone_number'] or '')[:13]
            body = (d['body_preview'] or '').replace('\n', ' ')[:40]
            print(f"{time_str:<12} {str(d['lead_id'] or ''):<8} {lead_name:<20} {phone:<14} {company:<20} {author:<18} {body}")

        # Check for rapid burst (>5 in 1 minute)
        print(f"\n{'─'*80}")
        print(f"⚡ BURST DETECTION (messages per minute):")
        print(f"{'─'*80}")
        by_minute = Counter()
        for row in rows:
            d = dict(zip(cols, row))
            if d['date_ist']:
                minute_key = d['date_ist'].strftime('%H:%M')
                by_minute[minute_key] += 1
        for minute, count in sorted(by_minute.items(), reverse=True):
            flag = "🔴 BURST!" if count >= 5 else ("🟡" if count >= 2 else "🟢")
            print(f"  {flag} {minute} IST: {count} messages")

    print(f"\n{'='*80}\n")
