# -*- coding: utf-8 -*-
import sys
import os
import re
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

config.parse_config(['-c', config_path, '-d', db_name])


def clean_phone_10(phone_str):
    if not phone_str:
        return ''
    digits = re.sub(r'\D', '', str(phone_str))
    return digits[-10:] if len(digits) >= 10 else digits


def scan_and_merge_duplicates(auto_merge=False):
    print("==========================================================================================")
    print(" 🔍 DIYA CRM - COMPANY-WISE DUPLICATE PHONE NUMBER SCAN & MERGE ENGINE")
    print("==========================================================================================")

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        companies = env['res.company'].search([])
        grand_total_duplicate_groups = 0
        grand_total_merged_records = 0

        for comp in companies:
            print(f"\n🏢 PROCESSING COMPANY: {comp.name} (ID: {comp.id})")
            print("-" * 90)

            all_leads = env['crm.lead'].with_context(active_test=False).search([
                ('company_id', '=', comp.id)
            ], order='id asc')

            phone_groups = defaultdict(list)
            for lead in all_leads:
                digits_10 = clean_phone_10(lead.phone)
                if digits_10 and len(digits_10) == 10:
                    phone_groups[digits_10].append(lead)

            dup_groups = {p: leads for p, leads in phone_groups.items() if len(leads) > 1}
            print(f"   Found {len(dup_groups)} Duplicate Phone Groups in {comp.name}")
            grand_total_duplicate_groups += len(dup_groups)

            if dup_groups:
                # If just scanning, print sample
                if not auto_merge:
                    print(f"\n   {'Phone':<12} | {'Count':<6} | {'Lead IDs':<25} | {'Names & Stages'}")
                    print("   " + "-" * 85)
                    for phone_num, lead_list in list(dup_groups.items())[:15]:
                        ids_str = ', '.join([f"#{l.id}" for l in lead_list])
                        names_stages = ', '.join([f"{l.name} ({l.stage_id.name if l.stage_id else 'No Stage'})" for l in lead_list])
                        print(f"   {phone_num:<12} | {len(lead_list):<6} | {ids_str:<25} | {names_stages[:40]}")
                    if len(dup_groups) > 15:
                        print(f"   ... and {len(dup_groups) - 15} more duplicate phone numbers.")

                # If merging, process ALL duplicates in this company
                else:
                    merged_in_comp = 0
                    for phone_num, lead_list in dup_groups.items():
                        # Sort by: active first, then stage sequence higher, then ID higher
                        def rank_lead(l):
                            is_act = 1 if l.active else 0
                            seq = l.stage_id.sequence if l.stage_id else 0
                            return (is_act, seq, l.id)

                        sorted_leads = sorted(lead_list, key=rank_lead, reverse=True)
                        primary_lead = sorted_leads[0]
                        duplicates = sorted_leads[1:]

                        for dup in duplicates:
                            # 1. Re-link messages from duplicate to primary
                            dup_msgs = env['mail.message'].search([
                                ('model', '=', 'crm.lead'),
                                ('res_id', '=', dup.id)
                            ])
                            if dup_msgs:
                                dup_msgs.write({'res_id': primary_lead.id})

                            # 2. Re-link activities from duplicate to primary
                            dup_acts = env['mail.activity'].search([
                                ('res_model', '=', 'crm.lead'),
                                ('res_id', '=', dup.id)
                            ])
                            if dup_acts:
                                dup_acts.write({'res_id': primary_lead.id})

                            # 3. Unlink duplicate
                            dup.unlink()
                            merged_in_comp += 1
                            grand_total_merged_records += 1

                    print(f"   ✅ Cleaned & Merged {merged_in_comp} duplicate records in {comp.name}")

        if auto_merge:
            cr.commit()
            print("\n==========================================================================================")
            print(f" 🎉 MERGE COMPLETE: Cleaned & Consolidated {grand_total_merged_records} Duplicate Records across all companies!")
            print("==========================================================================================")
        else:
            print("\n==========================================================================================")
            print(f" ℹ️ SUMMARY: Found Total {grand_total_duplicate_groups} duplicate phone groups across all companies.")
            print(" Run with '--merge' to automatically consolidate all chatter and remove duplicates!")
            print("==========================================================================================")


if __name__ == '__main__':
    merge_flag = '--merge' in sys.argv or '-m' in sys.argv
    scan_and_merge_duplicates(auto_merge=merge_flag)
