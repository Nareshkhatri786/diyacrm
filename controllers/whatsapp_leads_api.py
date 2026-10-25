# -*- coding: utf-8 -*-
"""
Diya CRM: WhatsApp Campaign Leads API Endpoint
Provides company-wise and stage-wise leads to the WhatsApp Marketing Portal.

Endpoint:
    GET / POST https://crm.sigprop.in/api/whatsapp/leads
Headers:
    Authorization: Bearer diyacrm_secret_token
    x-api-key: diyacrm_secret_token
"""
import json
import logging
import re
from odoo import http, fields, SUPERUSER_ID
from odoo.http import request, Response
from odoo.orm.registry import Registry

_logger = logging.getLogger(__name__)

DEFAULT_SECRET_TOKEN = "diyacrm_secret_token"

# Known Meta WhatsApp Phone Number IDs mapped to company search keywords
PHONE_ID_TO_COMPANY = {
    "1161115510429761": {"canonical_name": "Shreemad Family", "keywords": ["shreemad", "family"]},
    "1152168267972565": {"canonical_name": "Shreemad Family", "keywords": ["shreemad", "family"]},
    "1305619522636450": {"canonical_name": "The 1st Residency", "keywords": ["1st", "the1st", "residency", "radhe", "first", "developers"]},
    "1224814500716320": {"canonical_name": "Royal Rudraksha", "keywords": ["royal", "rudraksha"]},
    "122101071140010719": {"canonical_name": "Royal Rudraksha", "keywords": ["royal", "rudraksha"]},
    "1265084363352795": {"canonical_name": "Devi Bungalows", "keywords": ["devi", "bungalows", "bungalow"]},
    "916390071558584": {"canonical_name": "Devi Bungalows", "keywords": ["devi", "bungalows", "bungalow"]},
    "1193758907159434": {"canonical_name": "Signature Properties", "keywords": ["signature"]},
}

def clean_mobile_number(raw_phone):
    """
    Extracts pure 10-digit Indian mobile number.
    Returns 10-digit string if valid mobile, otherwise empty string.
    """
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", str(raw_phone))
    if len(digits) >= 10:
        last10 = digits[-10:]
        if last10[0] in "6789":
            return last10
        return last10
    return ""

def json_response(data, status=200):
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Headers", "Authorization, X-Api-Key, Content-Type"),
        ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
    ]
    return Response(json.dumps(data, ensure_ascii=False, indent=2), status=status, headers=headers)


class WhatsAppLeadsApiController(http.Controller):

    @http.route(
        ["/api/whatsapp/leads", "/api/whatsapp/leads/"],
        type="http",
        auth="none",
        methods=["GET", "POST", "OPTIONS"],
        csrf=False,
        save_session=False,
    )
    def get_whatsapp_leads(self, **kwargs):
        # 1. Handle CORS Preflight OPTIONS
        if request.httprequest.method == "OPTIONS":
            return json_response({"status": "ok"}, status=200)

        try:
            # 2. Extract Authentication Token from Headers or Query
            auth_header = request.httprequest.headers.get("Authorization", "")
            api_key_header = (
                request.httprequest.headers.get("x-api-key", "")
                or request.httprequest.headers.get("X-Api-Key", "")
                or request.httprequest.headers.get("X-API-KEY", "")
            )
            token_param = kwargs.get("token") or kwargs.get("api_key") or ""

            token = ""
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
            elif auth_header:
                token = auth_header.strip()
            elif api_key_header:
                token = api_key_header.strip()
            elif token_param:
                token = str(token_param).strip()

            # Check Token Validity
            if token != DEFAULT_SECRET_TOKEN:
                return json_response(
                    {
                        "success": False,
                        "error": "Unauthorized: Invalid or missing API authentication token.",
                        "hint": "Provide 'Authorization: Bearer diyacrm_secret_token' or 'x-api-key: diyacrm_secret_token' header.",
                    },
                    status=401,
                )

            # 3. Parse Request Parameters (Support both JSON body and Query params)
            params = {}
            if request.httprequest.is_json:
                try:
                    params = request.httprequest.get_json() or {}
                except Exception:
                    params = {}
            if not params:
                # Fallback to GET query params or POST form
                params = dict(kwargs)

            company_param = str(params.get("company_name") or params.get("company") or "").strip()
            phone_id_param = str(params.get("phone_number_id") or params.get("phone_id") or "").strip()
            stage_filter = str(params.get("stage") or "").strip()
            is_lost_param = params.get("is_lost", False)
            limit_param = params.get("limit")

            # Normalize is_lost flag
            # false = active only (default), true = lost only, 'all' = both
            if isinstance(is_lost_param, str):
                if is_lost_param.lower() in ["true", "1", "yes"]:
                    is_lost_mode = True
                elif is_lost_param.lower() in ["all", "both"]:
                    is_lost_mode = "all"
                else:
                    is_lost_mode = False
            elif isinstance(is_lost_param, bool):
                is_lost_mode = is_lost_param
            else:
                is_lost_mode = False

            db_name = request.db or request.httprequest.headers.get("X-Odoo-Db") or "diyacrm"
            registry = Registry(db_name)

            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, SUPERUSER_ID, {})

                # 4. Resolve Company Record
                target_company = None
                if phone_id_param and phone_id_param in PHONE_ID_TO_COMPANY:
                    rule = PHONE_ID_TO_COMPANY[phone_id_param]
                    for kw in rule["keywords"]:
                        target_company = env["res.company"].search([("name", "ilike", kw)], limit=1)
                        if target_company:
                            break

                if not target_company and company_param:
                    # Direct company name search
                    target_company = env["res.company"].search([("name", "ilike", company_param)], limit=1)
                    if not target_company:
                        # Check known keywords
                        for pid, rule in PHONE_ID_TO_COMPANY.items():
                            if any(kw in company_param.lower() for kw in rule["keywords"]):
                                for kw in rule["keywords"]:
                                    target_company = env["res.company"].search([("name", "ilike", kw)], limit=1)
                                    if target_company:
                                        break
                                if target_company:
                                    break

                if not target_company:
                    available_companies = [c.name for c in env["res.company"].search([])]
                    return json_response(
                        {
                            "success": False,
                            "error": "Target company could not be found. Provide a valid 'company_name' or 'phone_number_id'.",
                            "available_companies": available_companies,
                            "supported_phone_ids": list(PHONE_ID_TO_COMPANY.keys()),
                        },
                        status=400,
                    )

                # 5. Calculate Full Company Stage Summary (Active stages + Lost/Dropped)
                stage_summary = {}
                all_stages = env["crm.stage"].search([], order="sequence asc")
                for stg in all_stages:
                    # Count active leads in this stage for this company
                    stg_count = env["crm.lead"].search_count([
                        ("company_id", "=", target_company.id),
                        ("active", "=", True),
                        ("stage_id", "=", stg.id),
                    ])
                    stage_summary[stg.name] = stg_count

                # Count lost / dropped leads for this company
                lost_count = env["crm.lead"].with_context(active_test=False).search_count([
                    ("company_id", "=", target_company.id),
                    ("active", "=", False),
                ])
                stage_summary["Lost / Dropped"] = lost_count

                # 6. Build Query Domain for Filtered Leads List
                domain = [("company_id", "=", target_company.id)]

                if is_lost_mode is True:
                    domain.append(("active", "=", False))
                elif is_lost_mode is False:
                    domain.append(("active", "=", True))
                # if 'all', no active filter added

                if stage_filter:
                    if any(k in stage_filter.lower() for k in ["lost", "dropped", "archive"]):
                        domain.append(("active", "=", False))
                    else:
                        domain.append(("stage_id.name", "ilike", stage_filter))

                # Fetch leads with active_test=False to allow retrieving both active and lost as requested
                crm_lead_obj = env["crm.lead"].with_context(active_test=False)
                
                search_limit = None
                if limit_param:
                    try:
                        search_limit = int(limit_param)
                    except (ValueError, TypeError):
                        search_limit = None

                leads = crm_lead_obj.search(domain, order="create_date desc, id desc", limit=search_limit)

                # 7. Format Output Leads List
                leads_list = []
                for lead in leads:
                    # Resolve phone number
                    phone_raw = lead.phone or (lead.partner_id and (lead.partner_id.mobile or lead.partner_id.phone)) or ""
                    clean_mob = clean_mobile_number(phone_raw)

                    # Skip leads without a valid 10-digit mobile number for campaign safety
                    if not clean_mob:
                        continue

                    lead_name = (lead.name or "Client").strip()
                    # Clean up call logs or phone number duplicates from title if present
                    if lead_name.startswith("Call:"):
                        lead_name = lead_name.replace("Call:", "").strip()

                    is_lost_lead = not lead.active
                    stage_label = "Lost / Dropped" if is_lost_lead else (lead.stage_id.name if lead.stage_id else "New Leads")
                    created_date_str = fields.Datetime.to_string(lead.create_date)[:10] if lead.create_date else ""

                    leads_list.append({
                        "id": lead.id,
                        "name": lead_name,
                        "mobile": clean_mob,
                        "stage": stage_label,
                        "is_lost": is_lost_lead,
                        "created_at": created_date_str,
                    })

                response_data = {
                    "success": True,
                    "company_name": target_company.name,
                    "total_leads": len(leads_list),
                    "stage_summary": stage_summary,
                    "leads": leads_list,
                }

                return json_response(response_data, status=200)

        except Exception as e:
            _logger.exception("Diya CRM WhatsApp Leads API Exception: %s", str(e))
            return json_response(
                {
                    "success": False,
                    "error": f"Internal Server Error: {str(e)}",
                },
                status=500,
            )
