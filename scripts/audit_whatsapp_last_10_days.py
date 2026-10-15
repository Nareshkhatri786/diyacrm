# -*- coding: utf-8 -*-
import sys
import os
import glob
import gzip
import re
import datetime
import subprocess
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

config_path = '/etc/odoo19.conf' if os.path.exists('/etc/odoo19.conf') else r'c:\xampp\htdocs\odoo-19\odoo.conf'
db_name = 'diyacrm' if os.path.exists('/etc/odoo19.conf') else 'odoo19'

if os.path.exists('/opt/odoo19/odoo'):
    sys.path.insert(0, '/opt/odoo19/odoo')
else:
    sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")

import odoo
from odoo import api, fields, models, SUPERUSER_ID
from odoo.orm.registry import Registry
from odoo.tools import config
import pytz

config.parse_config(['-c', config_path, '-d', db_name])

def run_audit():
    user_tz = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(user_tz)
    days_10_ago = now_ist - datetime.timedelta(days=10)
    cutoff_utc_str = days_10_ago.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')

    print("==========================================================================================")
    print(f" 🔍 DIYA CRM: WHATSAPP INBOUND & LEAD AUDIT REPORT (LAST 10 DAYS: {days_10_ago.strftime('%d-%b')} TO {now_ist.strftime('%d-%b-%Y')})")
    print("==========================================================================================")

    # -------------------------------------------------------------
    # 1. DATABASE AUDIT: LEADS CREATED & UPDATED IN LAST 10 DAYS
    # -------------------------------------------------------------
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        print("\n📊 1. LEADS CREATED IN LAST 10 DAYS (COMPANY-WISE & SOURCE-WISE):")
        all_new_leads = env['crm.lead'].with_context(active_test=False).search([
            ('create_date', '>=', cutoff_utc_str)
        ], order='create_date desc')

        print(f"   • Total Leads Created: {len(all_new_leads)}")

        comp_stats = defaultdict(lambda: {
            'total': 0, 'active': 0, 'lost': 0,
            'whatsapp_source': 0, 'other_source': 0,
            'by_stage': defaultdict(int),
            'by_user': defaultdict(int),
            'leads': []
        })

        for l in all_new_leads:
            c_name = l.company_id.name if l.company_id else 'No Company'
            stg_name = l.stage_id.name if l.stage_id else 'No Stage'
            u_name = l.user_id.name if l.user_id else 'Unassigned'
            s_name = l.source_id.name if l.source_id else 'Direct/Unknown'

            comp_stats[c_name]['total'] += 1
            if l.active:
                comp_stats[c_name]['active'] += 1
                comp_stats[c_name]['by_stage'][stg_name] += 1
            else:
                comp_stats[c_name]['lost'] += 1
                reason = l.lost_reason_id.name if l.lost_reason_id else 'No Reason'
                comp_stats[c_name]['by_stage'][f"Lost ({reason})"] += 1

            comp_stats[c_name]['by_user'][u_name] += 1

            if 'whatsapp' in s_name.lower():
                comp_stats[c_name]['whatsapp_source'] += 1
            else:
                comp_stats[c_name]['other_source'] += 1

            comp_stats[c_name]['leads'].append(l)

        for comp, s in comp_stats.items():
            print(f"\n   🏢 Company: {comp}")
            print(f"      ├── Total Leads Created: {s['total']}")
            print(f"      ├── WhatsApp Source: {s['whatsapp_source']} | Other Sources: {s['other_source']}")
            print(f"      ├── Active in Pipeline: {s['active']} | Lost/Archived: {s['lost']}")
            print(f"      ├── Stages Breakdown:")
            for stg, count in s['by_stage'].items():
                print(f"      │   • {stg}: {count}")
            print(f"      └── Assigned Staff:")
            for u, count in s['by_user'].items():
                print(f"          • {u}: {count}")

        # -------------------------------------------------------------
        # 2. WHATSAPP MESSAGES TABLE (crm.lead.whatsapp.message)
        # -------------------------------------------------------------
        print("\n\n📱 2. WHATSAPP MESSAGES AUDIT (LAST 10 DAYS):")
        wa_msgs = env['crm.lead.whatsapp.message'].search([
            ('date', '>=', cutoff_utc_str)
        ], order='date desc')

        inbound_msgs = wa_msgs.filtered(lambda m: m.direction == 'inbound')
        outbound_msgs = wa_msgs.filtered(lambda m: m.direction == 'outbound')

        print(f"   • Total WhatsApp Messages Logged: {len(wa_msgs)}")
        print(f"   • Inbound (Client sent): {len(inbound_msgs)}")
        print(f"   • Outbound (Staff/System sent): {len(outbound_msgs)}")

        # Group inbound by company
        inbound_by_comp = defaultdict(list)
        for m in inbound_msgs:
            c = m.lead_id.company_id.name if (m.lead_id and m.lead_id.company_id) else 'Unknown'
            inbound_by_comp[c].append(m)

        for c, ms in inbound_by_comp.items():
            print(f"\n   🏢 Inbound WhatsApp for [{c}]: {len(ms)} message(s)")
            for m in ms[:5]:
                m_dt = fields.Datetime.from_string(m.date).replace(tzinfo=pytz.utc).astimezone(user_tz)
                lead_status = "Active" if (m.lead_id and m.lead_id.active) else "Lost"
                body_clean = ' '.join(m.body.split())[:60] if m.body else ''
                print(f"      • {m_dt.strftime('%d-%b %I:%M %p')} | Lead #{m.lead_id.id} ({m.author_name}, {m.phone}) [{lead_status}]: \"{body_clean}...\"")

        # -------------------------------------------------------------
        # 3. CHECK LEADS CURRENTLY IN LOST STATUS WITH RECENT ACTIVITY
        # -------------------------------------------------------------
        print("\n\n⚠️ 3. LEADS CURRENTLY IN 'LOST' STATUS CREATED/TOUCHED IN LAST 10 DAYS:")
        lost_recent_leads = env['crm.lead'].with_context(active_test=False).search([
            ('active', '=', False),
            '|',
            ('create_date', '>=', cutoff_utc_str),
            ('write_date', '>=', cutoff_utc_str)
        ], order='write_date desc')

        print(f"   • Found {len(lost_recent_leads)} lead(s) modified or created in last 10 days that are currently LOST:")
        if lost_recent_leads:
            print(f"   {'ID':<6} | {'Created':<12} | {'Client Name':<22} | {'Phone':<13} | {'Project':<18} | {'Owner':<14} | {'Lost Reason'}")
            print("   " + "-" * 115)
            for l in lost_recent_leads[:15]:
                c_date = fields.Datetime.from_string(l.create_date).strftime('%d-%b %Y') if l.create_date else 'N/A'
                comp = l.company_id.name[:17] if l.company_id else 'N/A'
                owner = l.user_id.name[:13] if l.user_id else 'Unassigned'
                reason = l.lost_reason_id.name if l.lost_reason_id else 'No Reason Given'
                print(f"   {l.id:<6} | {c_date:<12} | {l.name[:21]:<22} | {str(l.phone or '')[:12]:<13} | {comp:<18} | {owner:<14} | {reason}")

    # -------------------------------------------------------------
    # 4. SERVER NGINX ACCESS LOGS & ODOO JOURNALCTL LOGS
    # -------------------------------------------------------------
    print("\n\n🌐 4. WEBHOOK TRAFFIC ON SERVER (NGINX ACCESS LOGS & JOURNALCTL):")
    if os.path.exists('/var/log/nginx'):
        try:
            # Check nginx logs for webhook hits in last 10 days
            cmd = "grep -h -E 'POST /(webhook/whatsapp|api/whatsapp/lead|v1/webhook/meta)' /var/log/nginx/access.log* 2>/dev/null | tail -n 30"
            out = subprocess.check_output(cmd, shell=True, text=True)
            lines = out.strip().split('\n') if out.strip() else []
            print(f"   • Total Recent Webhook POST hits found in Nginx access log: {len(lines)}")
            if lines:
                print("   • Sample Nginx Webhook Hits:")
                for line in lines[-10:]:
                    print(f"     {line}")
        except Exception as e:
            print(f"   Nginx log search error: {e}")

        try:
            # Check journalctl for Webhook Exceptions
            print("\n   🚨 Odoo Journalctl Webhook Exceptions (Errors in Webhook Processing):")
            cmd = "journalctl -u odoo19 --since '10 days ago' --no-pager 2>/dev/null | grep -i 'Webhook Ingestion Exception\\|matched_key\\|SUPERUSER_ID' | tail -n 20"
            out = subprocess.check_output(cmd, shell=True, text=True)
            if out.strip():
                print(out)
            else:
                print("   No recent Webhook Ingestion Exception found in journalctl.")
        except Exception as e:
            print(f"   Journalctl read note (requires root/adm group): {e}")
    else:
        print("   (Local environment - server logs not present locally)")

    print("\n==========================================================================================")
    print(" ✅ AUDIT FINISHED")
    print("==========================================================================================")

if __name__ == '__main__':
    run_audit()
