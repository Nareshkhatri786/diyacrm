# -*- coding: utf-8 -*-
"""
Diya CRM: Seed 57 Units for 'Shreemad Family'
Strictly isolated to Shreemad company ID.
"""
import subprocess

UNITS_DATA = [
    # (Block, Floor, Unit No, Size, Facing, Location Charge (PLC), Status)
    ("A", 3, "303", "285", "main_road", True, "available"),
    ("A", 4, "403", "285", "main_road", True, "available"),
    ("A", 5, "503", "285", "main_road", True, "available"),
    ("A", 6, "601", "285", "internal_road", True, "available"),
    ("B", 2, "201", "285", "main_road", True, "available"),
    ("B", 6, "603", "285", "garden_view", True, "available"),
    ("B", 7, "701", "285", "main_road", True, "available"),
    ("B", 7, "703", "285", "garden_view", False, "available"),
    ("C", 1, "101", "380", "garden_view", True, "available"),
    ("C", 2, "201", "380", "internal_road", True, "available"),
    ("C", 3, "302", "295", "internal_road", True, "available"),
    ("C", 3, "304", "380", "garden_view", True, "available"),
    ("C", 2, "202", "295", "internal_road", False, "available"),
    ("C", 4, "403", "295", "garden_view", True, "available"),
    ("C", 4, "402", "295", "internal_road", False, "available"),
    ("C", 5, "502", "295", "internal_road", False, "available"),
    ("C", 5, "503", "295", "garden_view", True, "available"),
    ("C", 7, "702", "295", "internal_road", False, "available"),
    ("C", 9, "902", "295", "internal_road", False, "available"),
    ("C", 10, "1002", "295", "internal_road", False, "available"),
    ("C", 7, "703", "295", "garden_view", True, "available"),
    ("C", 8, "803", "295", "garden_view", True, "available"),
    ("D", 1, "102", "295", "garden_view", False, "available"),
    ("D", 3, "302", "295", "garden_view", False, "available"),
    ("C", 9, "903", "295", "garden_view", True, "available"),
    ("D", 4, "403", "295", "internal_road", False, "available"),
    ("D", 6, "602", "295", "garden_view", False, "available"),
    ("D", 8, "803", "295", "internal_road", False, "available"),
    ("D", 10, "1003", "295", "internal_road", False, "available"),
    ("D", 1, "101", "315", "garden_view", False, "available"),
    ("D", 2, "202", "295", "garden_view", True, "available"),
    ("D", 3, "301", "315", "garden_view", True, "available"),
    ("C", 1, "104", "380", "garden_view", False, "available"),
    ("D", 4, "402", "295", "garden_view", True, "available"),
    ("C", 2, "204", "380", "garden_view", False, "available"),
    ("D", 5, "501", "315", "garden_view", True, "available"),
    ("D", 6, "601", "315", "garden_view", True, "available"),
    ("C", 4, "404", "380", "garden_view", False, "available"),
    ("D", 7, "701", "315", "garden_view", True, "available"),
    ("D", 7, "702", "295", "garden_view", True, "available"),
    ("D", 7, "703", "295", "internal_road", True, "available"),
    ("D", 7, "704", "400", "internal_road", True, "available"),
    ("D", 8, "801", "315", "garden_view", True, "available"),
    ("D", 8, "802", "295", "garden_view", True, "available"),
    ("C", 6, "604", "380", "garden_view", False, "available"),
    ("D", 9, "902", "295", "garden_view", True, "available"),
    ("C", 7, "701", "380", "internal_road", False, "available"),
    ("C", 9, "901", "380", "internal_road", False, "available"),
    ("C", 10, "1001", "380", "internal_road", False, "available"),
    ("C", 10, "1004", "380", "garden_view", False, "available"),
    ("D", 2, "204", "400", "internal_road", False, "available"),
    # Units on Hold (at the end so UPSERT accurately preserves Hold status)
    ("A", 1, "101", "285", "internal_road", True, "hold"),
    ("A", 8, "802", "285", "main_road", True, "hold"),
    ("A", 9, "903", "285", "main_road", True, "hold"),
    ("B", 4, "402", "285", "internal_road", True, "hold"),
    ("B", 9, "903", "285", "garden_view", True, "hold"),
    ("C", 5, "502", "295", "internal_road", True, "hold"),
    ("C", 6, "603", "295", "garden_view", True, "hold"),
]

def seed_shreemad_units_sql():
    print("===================================================================")
    print(" 🏢 Seeding Real Estate Units for 'Shreemad Family' into Diya CRM")
    print("===================================================================")

    upsert_lines = []
    for block, floor, unit_no, size, facing, plc, status in UNITS_DATA:
        name = f"{block}-{unit_no}"
        plc_str = 'true' if plc else 'false'
        floor_key = str(floor).zfill(2)   # "1"->"01", "10"->"10"
        upsert_lines.append(f"""
        IF EXISTS (SELECT 1 FROM crm_property_unit WHERE company_id = comp_id AND block = '{block}' AND unit_no = '{unit_no}') THEN
            UPDATE crm_property_unit
            SET size_sq_yard = '{size}',
                facing = '{facing}',
                location_charge = {plc_str},
                floor = '{floor_key}',
                status = '{status}',
                name = '{name}'
            WHERE company_id = comp_id AND block = '{block}' AND unit_no = '{unit_no}';
            upd_count := upd_count + 1;
        ELSE
            INSERT INTO crm_property_unit 
                (name, unit_no, block, floor, size_sq_yard, facing, location_charge, status, company_id, create_date, write_date)
            VALUES 
                ('{name}', '{unit_no}', '{block}', '{floor_key}', '{size}', '{facing}', {plc_str}, '{status}', comp_id, NOW(), NOW());
            ins_count := ins_count + 1;
        END IF;
        """)

    all_upserts = "\n".join(upsert_lines)

    sql = f"""
DO $$
DECLARE
    comp_id INT;
    comp_name VARCHAR;
    ins_count INT := 0;
    upd_count INT := 0;
BEGIN
    -- 1. Find Shreemad Company
    SELECT id, name INTO comp_id, comp_name FROM res_company 
    WHERE name ILIKE '%shreemad%' 
    ORDER BY id ASC LIMIT 1;

    IF comp_id IS NULL THEN
        SELECT id, name INTO comp_id, comp_name FROM res_company 
        WHERE name ILIKE '%family%' 
        ORDER BY id ASC LIMIT 1;
    END IF;

    IF comp_id IS NULL THEN
        RAISE EXCEPTION '❌ Error: Could not find any Company with name containing Shreemad or Family in res_company!';
    END IF;

    RAISE NOTICE '🏢 Found Target Company ID: % ("%") for Shreemad Family', comp_id, comp_name;

    -- 2. Ensure table exists
    CREATE TABLE IF NOT EXISTS crm_property_unit (
        id SERIAL PRIMARY KEY,
        name VARCHAR,
        unit_no VARCHAR NOT NULL,
        block VARCHAR NOT NULL,
        floor VARCHAR NOT NULL,
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

    -- 3. Execute UPSERTs
    {all_upserts}

    RAISE NOTICE '🎉 SHREEMAD SEEDING COMPLETE: % inserted, % updated! Units ready for "%"', ins_count, upd_count, comp_name;
END $$;
"""

    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

if __name__ == '__main__':
    seed_shreemad_units_sql()
