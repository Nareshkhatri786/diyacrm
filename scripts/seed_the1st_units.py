# -*- coding: utf-8 -*-
import subprocess

UNITS_DATA = [
    # Block B (16 units)
    ("B", 1, "102", "265", "project_facing", False),
    ("B", 1, "103", "265", "plot_facing", False),
    ("B", 2, "202", "265", "project_facing", False),
    ("B", 3, "301", "275", "project_facing", True),
    ("B", 4, "402", "265", "project_facing", False),
    ("B", 5, "502", "265", "project_facing", False),
    ("B", 6, "601", "275", "project_facing", True),
    ("B", 6, "602", "265", "project_facing", False),
    ("B", 6, "603", "265", "plot_facing", False),
    ("B", 6, "604", "275", "plot_facing", True),
    ("B", 7, "701", "275", "project_facing", True),
    ("B", 7, "702", "265", "project_facing", False),
    ("B", 8, "802", "265", "project_facing", False),
    ("B", 9, "901", "275", "project_facing", True),
    ("B", 9, "903", "265", "plot_facing", False),
    ("B", 10, "1002", "265", "project_facing", False),

    # Block C (36 units)
    ("C", 1, "101", "275", "plot_facing", False),
    ("C", 1, "102", "270", "plot_facing", False),
    ("C", 1, "103", "265", "plot_facing", False),
    ("C", 1, "104", "265", "project_facing", False),
    ("C", 1, "105", "270", "garden_view", True),
    ("C", 1, "106", "275", "garden_view", True),
    ("C", 2, "202", "270", "plot_facing", False),
    ("C", 2, "205", "270", "garden_view", True),
    ("C", 2, "206", "275", "garden_view", True),
    ("C", 3, "301", "275", "plot_facing", False),
    ("C", 3, "304", "265", "project_facing", False),
    ("C", 3, "305", "270", "garden_view", True),
    ("C", 3, "306", "275", "garden_view", True),
    ("C", 4, "402", "270", "plot_facing", False),
    ("C", 4, "404", "265", "project_facing", False),
    ("C", 4, "405", "270", "garden_view", True),
    ("C", 4, "406", "275", "garden_view", True),
    ("C", 5, "504", "265", "project_facing", False),
    ("C", 5, "505", "270", "garden_view", True),
    ("C", 5, "506", "275", "garden_view", True),
    ("C", 6, "602", "270", "plot_facing", False),
    ("C", 6, "604", "265", "project_facing", False),
    ("C", 6, "605", "270", "garden_view", True),
    ("C", 7, "702", "270", "plot_facing", False),
    ("C", 7, "704", "265", "project_facing", False),
    ("C", 7, "705", "270", "garden_view", True),
    ("C", 8, "801", "275", "plot_facing", False),
    ("C", 8, "802", "270", "plot_facing", False),
    ("C", 8, "804", "265", "project_facing", False),
    ("C", 8, "805", "270", "garden_view", True),
    ("C", 9, "901", "275", "plot_facing", False),
    ("C", 9, "904", "265", "project_facing", False),
    ("C", 9, "905", "270", "garden_view", True),
    ("C", 9, "906", "275", "garden_view", True),
    ("C", 10, "1004", "265", "project_facing", False),
    ("C", 10, "1005", "270", "garden_view", True),
]

def seed_units_sql():
    print("===================================================================")
    print(" 🏢 Seeding Real Estate Units for 'The 1st Residency' into Diya CRM")
    print("===================================================================")

    upsert_lines = []
    for block, floor, unit_no, size, facing, plc in UNITS_DATA:
        name = f"{block}-{unit_no}"
        plc_str = 'true' if plc else 'false'
        upsert_lines.append(f"""
        IF EXISTS (SELECT 1 FROM crm_property_unit WHERE company_id = comp_id AND block = '{block}' AND unit_no = '{unit_no}') THEN
            UPDATE crm_property_unit
            SET size_sq_yard = '{size}',
                facing = '{facing}',
                location_charge = {plc_str},
                floor = {floor},
                name = '{name}'
            WHERE company_id = comp_id AND block = '{block}' AND unit_no = '{unit_no}';
            upd_count := upd_count + 1;
        ELSE
            INSERT INTO crm_property_unit 
                (name, unit_no, block, floor, size_sq_yard, facing, location_charge, status, company_id, create_date, write_date)
            VALUES 
                ('{name}', '{unit_no}', '{block}', {floor}, '{size}', '{facing}', {plc_str}, 'available', comp_id, NOW(), NOW());
            ins_count := ins_count + 1;
        END IF;
        """)

    all_upserts = "\n".join(upsert_lines)

    sql = f"""
DO $$
DECLARE
    comp_id INT;
    ins_count INT := 0;
    upd_count INT := 0;
BEGIN
    SELECT id INTO comp_id FROM res_company 
    WHERE name ILIKE '%1st%' OR name ILIKE '%first%' 
    ORDER BY id ASC LIMIT 1;

    IF comp_id IS NULL THEN
        SELECT id INTO comp_id FROM res_company ORDER BY id ASC LIMIT 1;
        RAISE NOTICE '⚠️ Could not find exact company name, using Company ID: %', comp_id;
    ELSE
        RAISE NOTICE '🏢 Found Company ID: % for The 1st Residency', comp_id;
    END IF;

    CREATE TABLE IF NOT EXISTS crm_property_unit (
        id SERIAL PRIMARY KEY,
        name VARCHAR,
        unit_no VARCHAR NOT NULL,
        block VARCHAR NOT NULL,
        floor INT NOT NULL,
        size_sq_yard VARCHAR NOT NULL,
        facing VARCHAR NOT NULL,
        location_charge BOOLEAN DEFAULT FALSE,
        status VARCHAR DEFAULT 'available',
        company_id INT NOT NULL,
        booking_lead_id INT,
        customer_id INT,
        customer_name VARCHAR,
        customer_phone VARCHAR,
        salesperson_id INT,
        booking_date DATE,
        remarks TEXT,
        create_date TIMESTAMP DEFAULT NOW(),
        write_date TIMESTAMP DEFAULT NOW(),
        create_uid INT DEFAULT 1,
        write_uid INT DEFAULT 1
    );

    {all_upserts}

    RAISE NOTICE '🎉 UNIT SEEDING COMPLETE: % inserted, % updated! Total 52 units ready in The 1st Residency.', ins_count, upd_count;
END $$;
"""

    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

if __name__ == '__main__':
    seed_units_sql()
