# Diya CRM - Custom Odoo 19 Module

Custom Odoo 19 CRM Module for Real Estate Lead Management, Pipeline Customizations, Activity Workflows, and Data Migration.

## 🚀 Key Features

1. **Lead Status Temperature System**:
   - `🔥 Hot`, `⛅ Warm`, `❄️ Cold` with soft pastel mild tone badges.
   - Kanban cards display Full Name on Top-Left and Status on Top-Right.
   - Pre-configured filters and group-by options in search views.

2. **Real Estate Activity Types**:
   - **Call**: Interactive Call Outcome pills (`Answered`, `No answer`, `Busy`, `Switched off`).
   - **Site Visit**: Auto 30-minute calendar time-slotting (10:00 AM, 10:30 AM, 11:00 AM...) and qualification outcome dropdowns (`Purchase Timeline`, `Finance Mode`, `Budget Comfort`, `Decision Maker`, and `Client Ke Saath Kaun Aaya` multi-choice).
   - **WhatsApp**: Direct WhatsApp activity tracking.
   - **To-Do**: Standard follow-up task tracking.

3. **16 Pre-configured Ahmedabad Areas**:
   - Pre-populated location selection field for fast lead qualification.

4. **Chatter Timeline Integration**:
   - Every completed call outcome and site visit qualification is automatically formatted and logged into the lead's Chatter history.

5. **Automated Migration Script**:
   - `scripts/migrate_test_leads.py`: Script for migrating leads, users, companies, stages, chatter timeline notes, and scheduled activities directly from JSON data into Odoo.

## 📦 Installation & Deployment

1. Copy/Clone this folder into your Odoo addons path:
   ```bash
   git clone https://github.com/Nareshkhatri786/diyacrm.git custom_addons/diyacrm
   ```

2. Add the custom addons directory to your `odoo.conf`:
   ```ini
   addons_path = /path/to/odoo/addons, /path/to/custom_addons
   ```

3. Install/Upgrade the module:
   ```bash
   odoo-bin -c odoo.conf -d <your_database> -u diyacrm --stop-after-init
   ```
