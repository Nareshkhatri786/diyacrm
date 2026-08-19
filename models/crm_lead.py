# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import datetime
import pytz


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    area = fields.Selection([
        ('hanspura', 'Hanspura'),
        ('nikol', 'Nikol'),
        ('vatva_lambha', 'Vatva / Lambha'),
        ('naroda_nava_naroda', 'Naroda / Nava Naroda'),
        ('vastral', 'Vastral'),
        ('odhav', 'Odhav'),
        ('narol', 'Narol'),
        ('isanpur', 'Isanpur'),
        ('ghodasar', 'Ghodasar'),
        ('kathwada', 'Kathwada'),
        ('hathijan', 'Hathijan'),
        ('ctm_ramol', 'CTM / Ramol'),
        ('aslali', 'Aslali'),
        ('maninagar', 'Maninagar'),
        ('other_ahmedabad', 'Other Area (Ahmedabad)'),
        ('outside_ahmedabad', 'Outside Ahmedabad'),
    ], string="Area", tracking=True)

    lead_temperature = fields.Selection([
        ('hot', '🔥 Hot'),
        ('warm', '⛅ Warm'),
        ('cold', '❄️ Cold'),
    ], string="Status", default='warm', tracking=True)

    last_call_outcome = fields.Selection([
        ('answered', 'Answered'),
        ('no_answer', 'No answer'),
        ('busy', 'Busy'),
        ('switched_off', 'Switched off'),
    ], string="Last Call Outcome", tracking=True)

    @api.model
    def get_dashboard_data(self, period='48h', company_id='all', user_id='all'):
        user_tz = pytz.timezone(self.env.user.tz or 'Asia/Kolkata')
        now_dt = datetime.datetime.now(user_tz)

        # 1. Determine Date Range
        if period == 'today':
            start_dt = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = now_dt
        elif period == 'yesterday':
            yesterday = now_dt - datetime.timedelta(days=1)
            start_dt = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == 'week':
            start_dt = (now_dt - datetime.timedelta(days=now_dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = now_dt
        elif period == 'month':
            start_dt = now_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_dt = now_dt
        elif period == '48h':
            start_dt = now_dt - datetime.timedelta(hours=48)
            end_dt = now_dt
        else:  # all time
            start_dt = now_dt - datetime.timedelta(days=365)
            end_dt = now_dt

        start_utc = start_dt.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
        end_utc = end_dt.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')

        # 2. Determine Allowed / Selected Companies
        allowed_companies = self.env.companies
        if company_id != 'all' and company_id:
            try:
                target_cid = int(company_id)
                target_company = allowed_companies.filtered(lambda c: c.id == target_cid)
                active_companies = target_company if target_company else self.env['res.company'].browse([target_cid])
            except Exception:
                active_companies = allowed_companies
        else:
            active_companies = allowed_companies

        company_ids = active_companies.ids

        # 3. Base Lead Domain
        base_lead_domain = [('company_id', 'in', company_ids)]
        if user_id != 'all' and user_id:
            try:
                base_lead_domain.append(('user_id', '=', int(user_id)))
            except Exception:
                pass

        all_comp_leads = self.with_context(active_test=False).search(base_lead_domain)
        lead_ids_in_scope = all_comp_leads.ids

        # 4. New vs Updated Opportunities in Period
        new_opps = all_comp_leads.filtered(
            lambda l: l.create_date and fields.Datetime.to_string(l.create_date) >= start_utc and fields.Datetime.to_string(l.create_date) <= end_utc
        )

        inbound_messages = self.env['mail.message'].search([
            ('model', '=', 'crm.lead'),
            ('res_id', 'in', lead_ids_in_scope),
            ('date', '>=', start_utc),
            ('date', '<=', end_utc),
        ])

        updated_lead_ids = set()
        for m in inbound_messages:
            lead = all_comp_leads.filtered(lambda l: l.id == m.res_id)
            if lead and lead.create_date and fields.Datetime.to_string(lead.create_date) < start_utc:
                if 'WhatsApp' in (m.body or '') or 'Inbound' in (m.body or ''):
                    updated_lead_ids.add(m.res_id)

        # 5. Exact Calling Analytics & Outcomes Matching Total
        leads_in_scope = all_comp_leads.filtered(
            lambda l: (l.create_date and fields.Datetime.to_string(l.create_date) >= start_utc and fields.Datetime.to_string(l.create_date) <= end_utc)
            or (l.write_date and fields.Datetime.to_string(l.write_date) >= start_utc and fields.Datetime.to_string(l.write_date) <= end_utc)
        )
        target_leads = leads_in_scope if leads_in_scope else all_comp_leads

        out_answered = 0
        out_noanswer = 0
        out_busy = 0
        out_switched = 0

        for lead in target_leads:
            if lead.last_call_outcome == 'answered':
                out_answered += 1
            elif lead.last_call_outcome == 'no_answer':
                out_noanswer += 1
            elif lead.last_call_outcome == 'busy':
                out_busy += 1
            elif lead.last_call_outcome == 'switched_off':
                out_switched += 1

        for m in inbound_messages:
            b = (m.body or '').lower()
            if 'call' in b or 'outcome' in b or 'connected' in b or 'answered' in b:
                if 'answered' in b or 'connected' in b:
                    out_answered += 1
                elif 'no answer' in b or 'not answered' in b or 'missed' in b:
                    out_noanswer += 1
                elif 'busy' in b:
                    out_busy += 1
                elif 'switched' in b or 'unreachable' in b:
                    out_switched += 1

        total_calls = out_answered + out_noanswer + out_busy + out_switched

        # Accurate Dynamic Percentages
        if total_calls > 0:
            connected_pct = round((out_answered / total_calls) * 100)
            answered_pct = round((out_answered / total_calls) * 100)
            no_answer_pct = round((out_noanswer / total_calls) * 100)
            busy_pct = round((out_busy / total_calls) * 100)
            switched_off_pct = round((out_switched / total_calls) * 100)
        else:
            connected_pct = 0
            answered_pct = 0
            no_answer_pct = 0
            busy_pct = 0
            switched_off_pct = 0

        # 6. Canonical 7 Active Pipeline Stages
        canonical_definitions = [
            (1, "1. New Lead", ["new", "new lead"], "#3b82f6"),
            (2, "2. Contacted / Follow-up", ["contacted", "followup", "follow up"], "#06b6d4"),
            (3, "3. Qualified", ["qualified", "interested"], "#6366f1"),
            (4, "4. Site Visit Scheduled", ["visit schedule", "visit scheduled", "site visit scheduled"], "#f59e0b"),
            (5, "5. Site Visit Done", ["visit done", "site visit done"], "#8b5cf6"),
            (6, "6. Negotiation / Token", ["negotiation", "token"], "#ec4899"),
            (7, "7. Won / Booked", ["won", "booked", "closed"], "#10b981"),
        ]

        stage_data = []
        for seq, name, aliases, color in canonical_definitions:
            count = len(all_comp_leads.filtered(
                lambda l: l.active and (
                    l.stage_id.name == name or
                    any(al in (l.stage_id.name or '').lower() for al in aliases)
                )
            ))
            stage_data.append({
                'id': seq,
                'name': name,
                'sequence': seq,
                'count': count,
                'color': color,
            })

        # 7. Lead Temperature Breakdown
        temp_hot = len(all_comp_leads.filtered(lambda l: l.active and l.lead_temperature == 'hot'))
        temp_warm = len(all_comp_leads.filtered(lambda l: l.active and l.lead_temperature == 'warm'))
        temp_cold = len(all_comp_leads.filtered(lambda l: l.active and l.lead_temperature == 'cold'))

        # 8. Source Attribution (UTM)
        source_counts = {}
        for l in all_comp_leads.filtered(lambda l: l.active):
            src_name = l.source_id.name if l.source_id else 'Walk In'
            source_counts[src_name] = source_counts.get(src_name, 0) + 1

        # 9. Site Visits Analytics
        visits_scheduled = stage_data[3]['count']
        visits_done = stage_data[4]['count']
        won_count = stage_data[6]['count']

        # 10. Team Leaderboard
        users = self.env['res.users'].search([('company_ids', 'in', company_ids), ('share', '=', False)])
        team_leaderboard = []
        today_date = fields.Date.today()

        for u in users:
            u_leads = all_comp_leads.filtered(lambda l: l.user_id.id == u.id)
            if not u_leads and u.id != self.env.user.id:
                continue

            u_new_opps = len(u_leads.filtered(
                lambda l: l.create_date and fields.Datetime.to_string(l.create_date) >= start_utc and fields.Datetime.to_string(l.create_date) <= end_utc
            ))
            u_visits = len(u_leads.filtered(lambda l: l.active and any(al in (l.stage_id.name or '').lower() for al in ["visit done", "site visit done"])))
            u_won = len(u_leads.filtered(lambda l: l.active and any(al in (l.stage_id.name or '').lower() for al in ["won", "booked"])))
            
            overdue_acts = self.env['mail.activity'].search_count([
                ('user_id', '=', u.id),
                ('res_model', '=', 'crm.lead'),
                ('date_deadline', '<', today_date)
            ])

            u_calls = len(u_leads.filtered(lambda l: l.last_call_outcome))

            team_leaderboard.append({
                'id': u.id,
                'name': u.name,
                'avatar': u.name[0].upper() if u.name else 'U',
                'project': u.company_id.name if u.company_id else 'General',
                'calls': u_calls,
                'new_opps': u_new_opps,
                'visits_done': u_visits,
                'won': u_won,
                'pending_overdue': overdue_acts,
            })

        return {
            'period': period,
            'is_multi_company': len(active_companies) > 1,
            'active_companies': [{'id': c.id, 'name': c.name} for c in active_companies],
            'available_companies': [{'id': c.id, 'name': c.name} for c in allowed_companies],
            'kpis': {
                'total_calls': total_calls,
                'connected_pct': connected_pct,
                'new_opps': len(new_opps),
                'updated_opps': len(updated_lead_ids),
                'visits_scheduled': visits_scheduled,
                'visits_done': visits_done,
                'won': won_count,
            },
            'calling_outcomes': {
                'answered': out_answered,
                'no_answer': out_noanswer,
                'busy': out_busy,
                'switched_off': out_switched,
                'answered_pct': answered_pct,
                'no_answer_pct': no_answer_pct,
                'busy_pct': busy_pct,
                'switched_off_pct': switched_off_pct,
            },
            'stages': stage_data,
            'temperature': {
                'hot': temp_hot,
                'warm': temp_warm,
                'cold': temp_cold,
            },
            'sources': [{'name': k, 'count': v} for k, v in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:6]],
            'leaderboard': sorted(team_leaderboard, key=lambda x: (x['won'], x['visits_done'], x['new_opps']), reverse=True),
        }
