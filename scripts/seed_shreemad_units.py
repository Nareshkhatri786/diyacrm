# -*- coding: utf-8 -*-
"""
Diya CRM: Replace Shreemad Family Inventory with New 52 Units.
Removes old Shreemad inventory and inserts the new verified units.
"""
import subprocess
import os
import sys

UNITS_DATA = [
    # (Block, Floor, Unit No, Size, Facing, Location Charge (PLC), Status)
    ("A", 3, "303", "285", "main_road", False, "available"),
    ("A", 4, "403", "285", "main_road", False, "available"),
    ("A", 5, "503", "285", "main_road", False, "available"),
    ("B", 2, "201", "285", "main_road", False, "available"),
    ("B", 6, "603", "285", "garden_view", False, "available"),
    ("B", 7, "701", "285", "main_road", False, "available"),
    ("B", 7, "703", "285", "garden_view", False, "available"),
    ("B", 9, "901", "285", "main_road", False, "available"),
    ("C", 1, "101", "380", "main_entry", True, "hold"),
    ("C", 1, "104", "380", "garden_view", True, "hold"),
    ("C", 2, "201", "380", "main_entry", True, "hold"),
    ("C", 2, "204", "380", "garden_view", True, "hold"),
    ("C", 3, "302", "295", "main_entry", True, "hold"),
    ("C", 3, "304", "380", "garden_view", True, "hold"),
    ("C", 4, "403", "295", "garden_view", True, "hold"),
    ("C", 4, "404", "380", "garden_view", True, "hold"),
    ("C", 5, "502", "295", "main_entry", False, "available"),
    ("C", 5, "503", "295", "garden_view", True, "hold"),
    ("C", 6, "604", "380", "garden_view", False, "available"),
    ("C", 7, "701", "380", "main_entry", False, "available"),
    ("C", 7, "702", "295", "main_entry", False, "available"),
    ("C", 7, "703", "295", "garden_view", True, "hold"),
    ("C", 8, "803", "295", "garden_view", True, "hold"),
    ("C", 9, "902", "295", "main_entry", False, "available"),
    ("C", 9, "903", "295", "garden_view", True, "hold"),
    ("C", 10, "1001", "380", "main_entry", False, "available"),
    ("C", 10, "1004", "380", "garden_view", False, "available"),
    ("D", 1, "101", "315", "garden_view", False, "available"),
    ("D", 1, "102", "295", "garden_view", False, "available"),
    ("D", 2, "202", "295", "garden_view", True, "hold"),
    ("D", 3, "301", "315", "garden_view", True, "hold"),
    ("D", 3, "302", "295", "garden_view", False, "available"),
    ("D", 4, "402", "295", "garden_view", True, "hold"),
    ("D", 4, "403", "295", "main_entry", False, "available"),
    ("D", 5, "501", "315", "garden_view", True, "hold"),
    ("D", 6, "601", "315", "garden_view", True, "hold"),
    ("D", 6, "602", "295", "garden_view", False, "available"),
    ("D", 7, "701", "315", "garden_view", True, "hold"),
    ("D", 7, "702", "295", "garden_view", True, "hold"),
    ("D", 7, "703", "295", "main_entry", True, "hold"),
    ("D", 7, "704", "400", "main_entry", True, "hold"),
    ("D", 8, "801", "315", "garden_view", True, "hold"),
    ("D", 8, "802", "295", "garden_view", True, "hold"),
    ("D", 8, "803", "295", "main_entry", False, "available"),
    ("D", 9, "901", "315", "garden_view", True, "hold"),
    ("D", 9, "902", "295", "garden_view", True, "hold"),
    ("D", 10, "1003", "295", "main_entry", False, "available"),
    ("B2", 7, "701", "285", "garden_view", False, "available"),
    ("C2", 1, "101", "285", "garden_view", False, "available"),
    ("C2", 3, "301", "285", "garden_view", False, "available"),
    ("C2", 6, "602", "285", "main_entry", False, "available"),
    ("D2", 1, "101", "320", "main_entry", False, "available"),
]

def seed_shreemad_units_sql():
    print("===================================================================")
    print(" 🏢 DIYA CRM: RESET & SEED NEW INVENTORY FOR 'SHREEMAD FAMILY'")
    print("===================================================================")

    insert_rows = []
    for block, floor, unit_no, size, facing, plc, status in UNITS_DATA:
        name = f"{block}-{unit_no}"
        plc_str = 'true' if plc else 'false'
        floor_key = str(floor).zfill(2)   # "1"->"01", "10"->"10"
        insert_rows.append(
            f"('{name}', '{unit_no}', '{block}', '{floor_key}', '{size}', '{facing}', {plc_str}, '{status}', comp_id, NOW(), NOW())"
        )

    all_inserts_sql = ",\n    ".join(insert_rows)

    sql = f"""
DO $$
DECLARE
    comp_id INT;
    comp_name VARCHAR;
    del_count INT := 0;
    ins_count INT := 0;
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

    -- 3. Unlink leads linked to old units of this company to avoid foreign key blocks
    UPDATE crm_lead 
    SET property_unit_id = NULL 
    WHERE property_unit_id IN (SELECT id FROM crm_property_unit WHERE company_id = comp_id);

    -- 4. Delete all existing old units for Shreemad
    DELETE FROM crm_property_unit WHERE company_id = comp_id;
    GET DIAGNOSTICS del_count = ROW_COUNT;
    RAISE NOTICE '🗑️ Removed % old inventory units for "%".', del_count, comp_name;

    -- 5. Insert all new 52 units
    INSERT INTO crm_property_unit 
        (name, unit_no, block, floor, size_sq_yard, facing, location_charge, status, company_id, create_date, write_date)
    VALUES 
    {all_inserts_sql};

    GET DIAGNOSTICS ins_count = ROW_COUNT;
    RAISE NOTICE '✅ Successfully added % new inventory units for "%"!', ins_count, comp_name;
    RAISE NOTICE '   • Open / Available: 27 units';
    RAISE NOTICE '   • Hold:             25 units';
    RAISE NOTICE '===================================================================';
END $$;
"""

    if os.name == 'posix':
        cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    else:
        cmd = ["psql", "-U", "postgres", "-d", "diyacrm", "-c", sql]

    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

if __name__ == '__main__':
    seed_shreemad_units_sql()
