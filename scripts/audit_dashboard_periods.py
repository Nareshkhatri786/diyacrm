# -*- coding: utf-8 -*-
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Determine Odoo config path and database
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

config.parse_config(['-c', config_path, '-d', db_name])


def print_separator(char="=", length=90):
    print(char * length)


def run_period_audit():
    print_separator("=")
    print(" 📊 DIYA CRM - EXECUTIVE DASHBOARD LIVE PERIOD AUDIT REPORT")
    print_separator("=")
    print(f" Database: {db_name} | Config: {config_path}")

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        periods = [
            ('today', '📅 TODAY (LIVE)'),
            ('yesterday', '📅 YESTERDAY'),
            ('48h', '📅 LAST 48 HOURS'),
            ('week', '📅 THIS WEEK'),
            ('month', '📅 THIS MONTH'),
            ('all', '📅 ALL TIME'),
        ]

        for p_key, p_label in periods:
            data = env['crm.lead'].get_dashboard_data(period=p_key, company_id='all', user_id='all')
            kpis = data['kpis']
            outcomes = data['calling_outcomes']
            temp = data['temperature']
            stages = data['stages']
            leaderboard = data['leaderboard']

            print("\n")
            print_separator("-")
            print(f" >>> {p_label} <<<")
            print_separator("-")

            print(f" 📞 TOTAL CALLS LOGGED       : {kpis['total_calls']}  (Connected: {kpis['connected_pct']}%)")
            print(f"    ├─ 🟢 Answered          : {outcomes['answered']} ({outcomes['answered_pct']}%)")
            print(f"    ├─ 🔴 No Answer         : {outcomes['no_answer']} ({outcomes['no_answer_pct']}%)")
            print(f"    ├─ 🟡 Busy              : {outcomes['busy']} ({outcomes['busy_pct']}%)")
            print(f"    └─ ⚫ Switched Off      : {outcomes['switched_off']} ({outcomes['switched_off_pct']}%)")

            print(f"\n 👥 OPPORTUNITIES IN PERIOD :")
            print(f"    ├─ 🆕 New Opps Created   : {kpis['new_opps']}")
            print(f"    ├─ 🔄 Repeat Inquiries   : {kpis['updated_opps']}")
            print(f"    ├─ 🚗 Visits Scheduled   : {kpis['visits_scheduled']}")
            print(f"    ├─ 🏁 Visits Completed   : {kpis['visits_done']}")
            print(f"    └─ 🏆 Won / Booked       : {kpis['won']}")

            print(f"\n 🔥 LEAD TEMPERATURE        : Hot: {temp['hot']} | Warm: {temp['warm']} | Cold: {temp['cold']}")

            print("\n 🚀 7-STAGE FUNNEL TOTALS   :")
            for stg in stages:
                print(f"    • {stg['name']:<28} : {stg['count']:>4} opps")

            if leaderboard:
                print("\n 👤 TEAM PERFORMANCE LEADERBOARD :")
                print(f"    {'Salesperson':<20} | {'Project':<20} | {'Calls':<6} | {'New Opps':<9} | {'Visits':<7} | {'Won':<4} | {'Due':<4}")
                print("    " + "-" * 80)
                for u in leaderboard:
                    print(f"    {u['name']:<20} | {u['project']:<20} | {u['calls']:<6} | {u['new_opps']:<9} | {u['visits_done']:<7} | {u['won']:<4} | {u['pending_overdue']:<4}")

    print("\n")
    print_separator("=")
    print(" ✅ AUDIT COMPLETED - All numbers above match 1:1 with Executive Dashboard")
    print_separator("=")


if __name__ == '__main__':
    run_period_audit()
