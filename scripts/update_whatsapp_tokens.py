# -*- coding: utf-8 -*-
"""
Diya CRM: Update WhatsApp Access Tokens Tool
Allows fast CLI updating of Meta WhatsApp tokens in ir_config_parameter.
"""
import sys
import os
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def set_param(key, value):
    sql = f"""
    INSERT INTO ir_config_parameter (key, value, create_date, write_date, create_uid, write_uid)
    VALUES ('{key}', '{value}', NOW(), NOW(), 1, 1)
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW();
    """
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Successfully updated parameter '{key}'!")
    except Exception as e:
        print(f"❌ Failed to update '{key}': {e}")

def main():
    print("==================================================================")
    print(" 🔑 DIYA CRM: UPDATE WHATSAPP TOKENS")
    print("==================================================================")
    print("This script updates tokens for projects whose sessions expired.\n")
    print("Options:")
    print("1. Update Shreemad Family Token")
    print("2. Update Royal Rudraksha Token")
    print("3. Update Both")
    print("4. Exit")
    
    choice = input("\nEnter choice (1/2/3/4): ").strip()
    
    if choice in ['1', '3']:
        tok = input("\n👉 Paste NEW Token for 'Shreemad Family': ").strip()
        if tok:
            set_param('diyacrm.shreemad_family.token', tok)
            
    if choice in ['2', '3']:
        tok = input("\n👉 Paste NEW Token for 'Royal Rudraksha': ").strip()
        if tok:
            set_param('diyacrm.royal_rudraksha.token', tok)

    print("\nVerifying updated tokens with Meta API...")
    diag_script = os.path.join(os.path.dirname(__file__), 'diagnose_whatsapp_status.py')
    if os.path.exists(diag_script):
        subprocess.run([sys.executable, diag_script])

if __name__ == '__main__':
    main()
