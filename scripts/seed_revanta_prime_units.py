# -*- coding: utf-8 -*-
"""
Diya CRM: Seed 126 Units for 'Revanta Prime'
Strictly isolated to Revanta Prime company ID.
Block A: 56 units (Floors 1-14, 4 units/floor)
Block B: 70 units (Floors 1-14, 5 units/floor)
Total: 126 units (146 Sq. Yards)
"""
import subprocess

def generate_units():
    units = []
    # Block A: 14 floors, 4 units per floor
    for f in range(1, 15):
        floor_str = str(f).zfill(2)
        # Unit 1: Main Road
        units.append(("A", floor_str, f"{f}01", "146", "main_road", False, "available"))
        # Unit 2: Main Road
        units.append(("A", floor_str, f"{f}02", "146", "main_road", False, "available"))
        # Unit 3: Garden View
        units.append(("A", floor_str, f"{f}03", "146", "garden_view", False, "available"))
        # Unit 4: Garden View
        units.append(("A", floor_str, f"{f}04", "146", "garden_view", False, "available"))

    # Block B: 14 floors, 5 units per floor
    for f in range(1, 15):
        floor_str = str(f).zfill(2)
        # Unit 1: Main Road
        units.append(("B", floor_str, f"{f}01", "146", "main_road", False, "available"))
        # Unit 2: Main Road
        units.append(("B", floor_str, f"{f}02", "146", "main_road", False, "available"))
        # Unit 3: Temple Facing
        units.append(("B", floor_str, f"{f}03", "146", "temple_facing", False, "available"))
        # Unit 4: Temple Facing
        units.append(("B", floor_str, f"{f}04", "146", "temple_facing", False, "available"))
        # Unit 5: Garden View
        units.append(("B", floor_str, f"{f}05", "146", "garden_view", False, "available"))

    return units

UNITS_DATA = generate_units()

def seed_revanta_prime_units_sql():
    print("===================================================================")
    print(f" 🏢 Seeding Real Estate Units for 'Revanta Prime' into Diya CRM")
    print(f" Total Units to seed: {len(UNITS_DATA)}")
    print("===================================================================")

    upsert_lines = []
    for block, floor_key, unit_no, size, facing, plc, status in UNITS_DATA:
        name = f"{block}-{unit_no}"
        plc_str = 'true' if plc else 'false'
        upsert_lines.append(f"""
        IF EXISTS (SELECT 1 FROM crm_property_unit WHERE company_id = comp_id AND block = '{block}' AND unit_no = '{unit_no}') THEN
            UPDATE crm_property_unit
            SET size_sq_yard = '{size}',
                facing = '{facing}',
                location_charge = {plc_str},
                floor = '{floor_key}',
                name = '{name}',
                status = '{status}',
                write_date = NOW()
            WHERE company_id = comp_id AND block = '{block}' AND unit_no = '{unit_no}';
            upd_count := upd_count + 1;
        ELSE
            INSERT INTO crm_property_unit 
                (name, unit_no, block, floor, size_sq_yard, facing, location_charge, status, company_id, create_date, write_date, create_uid, write_uid)
            VALUES 
                ('{name}', '{unit_no}', '{block}', '{floor_key}', '{size}', '{facing}', {plc_str}, '{status}', comp_id, NOW(), NOW(), 1, 1);
            ins_count := ins_count + 1;
        END IF;
        """)

    all_upserts = "\n".join(upsert_lines)

    sql = f"""
DO $$
DECLARE
    comp_id INT;
    comp_name VARCHAR;
    part_id INT;
    ins_count INT := 0;
    upd_count INT := 0;
BEGIN
    -- 1. Find or create Revanta Prime company
    SELECT id, name INTO comp_id, comp_name FROM res_company 
    WHERE name ILIKE '%revanta%' OR name ILIKE '%reventa%' 
    ORDER BY id ASC LIMIT 1;

    IF comp_id IS NULL THEN
        INSERT INTO res_partner (name, is_company, active, create_date, write_date)
        VALUES ('Revanta Prime', true, true, NOW(), NOW())
        RETURNING id INTO part_id;

        INSERT INTO res_company (name, partner_id, currency_id, create_date, write_date)
        VALUES ('Revanta Prime', part_id, (SELECT currency_id FROM res_company WHERE id = 1 LIMIT 1), NOW(), NOW())
        RETURNING id, name INTO comp_id, comp_name;

        UPDATE res_partner SET company_id = comp_id WHERE id = part_id;
        RAISE NOTICE '✨ Created new Company ID: % ("%") in res_company!', comp_id, comp_name;
    ELSE
        RAISE NOTICE '🏢 Found Target Company ID: % ("%") for Revanta Prime', comp_id, comp_name;
    END IF;

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

    RAISE NOTICE '🎉 REVANTA PRIME SEEDING COMPLETE: % inserted, % updated! Total % units ready in "%".', 
                 ins_count, upd_count, (ins_count + upd_count), comp_name;
END $$;
"""

    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

if __name__ == '__main__':
    seed_revanta_prime_units_sql()
