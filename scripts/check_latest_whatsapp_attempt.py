# -*- coding: utf-8 -*-
import subprocess
import sys

sql = """
SELECT 
    m.id,
    m.date,
    m.res_id AS lead_id,
    l.name AS lead_name,
    c.name AS company_name,
    m.body
FROM mail_message m
JOIN crm_lead l ON l.id = m.res_id
JOIN res_company c ON c.id = l.company_id
WHERE m.model = 'crm.lead'
  AND (m.body ILIKE '%WhatsApp Failed%' OR m.body ILIKE '%WhatsApp Delivered%')
ORDER BY m.id DESC
LIMIT 5;
"""

cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
try:
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
except Exception as e:
    print(e)
