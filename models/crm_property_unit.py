# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CrmPropertyUnit(models.Model):
    _name = "crm.property.unit"
    _description = "Real Estate Property Unit"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "block asc, floor desc, unit_no asc"

    name = fields.Char(string="Unit Code", compute="_compute_name", store=True, index=True)
    unit_no = fields.Char(string="Unit No.", required=True, tracking=True)
    block = fields.Selection([
        ("A", "Block A"),
        ("B", "Block B"),
        ("C", "Block C"),
        ("D", "Block D"),
    ], string="Block", required=True, default="B", tracking=True)
    floor = fields.Integer(string="Floor", required=True, default=1, tracking=True)
    size_sq_yard = fields.Selection([
        ("265", "265 Sq. Yards"),
        ("270", "270 Sq. Yards"),
        ("275", "275 Sq. Yards"),
    ], string="Size (Sq. Yards)", required=True, tracking=True)
    facing = fields.Selection([
        ("project_facing", "Project Facing"),
        ("plot_facing", "Plot Facing"),
        ("garden_view", "Garden View"),
        ("road_facing", "Road Facing"),
    ], string="Facing", required=True, default="project_facing", tracking=True)
    location_charge = fields.Boolean(string="Location Charge (PLC)", default=False, tracking=True)
    status = fields.Selection([
        ("available", "Open / Available"),
        ("hold", "Hold / In Discussion"),
        ("booked", "Booked"),
    ], string="Status", default="available", required=True, tracking=True)

    company_id = fields.Many2one("res.company", string="Project / Company", required=True,
                                 default=lambda self: self.env.company, tracking=True)
    booking_lead_id = fields.Many2one("crm.lead", string="Booked Lead", tracking=True)
    customer_id = fields.Many2one("res.partner", string="Customer / Buyer", tracking=True)
    customer_name = fields.Char(string="Buyer Name", tracking=True)
    customer_phone = fields.Char(string="Buyer Phone", tracking=True)
    salesperson_id = fields.Many2one("res.users", string="Sales Executive", tracking=True)
    booking_date = fields.Date(string="Booking Date", tracking=True)
    remarks = fields.Text(string="Remarks / Notes")

    @api.constrains('company_id', 'block', 'unit_no')
    def _check_unique_unit(self):
        for rec in self:
            domain = [
                ('company_id', '=', rec.company_id.id),
                ('block', '=', rec.block),
                ('unit_no', '=', rec.unit_no),
                ('id', '!=', rec.id),
            ]
            if self.search_count(domain):
                raise UserError(_(
                    "Unit %s in Block %s already exists for this company!"
                ) % (rec.unit_no, rec.block))

    @api.depends("block", "unit_no")
    def _compute_name(self):
        for rec in self:
            if rec.block and rec.unit_no:
                rec.name = f"{rec.block}-{rec.unit_no}"
            elif rec.unit_no:
                rec.name = rec.unit_no
            else:
                rec.name = "New Unit"

    def action_book_wizard(self):
        self.ensure_one()
        if self.status == 'booked':
            raise UserError(_("Unit %s is already booked!") % self.name)
        return {
            "name": _("Book Unit: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "crm.unit.booking.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_unit_id": self.id,
                "default_salesperson_id": self.env.user.id,
            }
        }

    def action_release_unit(self):
        self.ensure_one()
        prev_lead = self.booking_lead_id
        prev_name = self.name
        self.write({
            "status": "available",
            "booking_lead_id": False,
            "customer_id": False,
            "customer_name": False,
            "customer_phone": False,
            "salesperson_id": False,
            "booking_date": False,
        })
        self.message_post(body=_("Unit %s has been released and is now Available.") % prev_name)
        if prev_lead:
            prev_lead.message_post(body=_("Booked unit %s was released back to Available inventory.") % prev_name)
        return True

    def action_hold_unit(self):
        self.ensure_one()
        if self.status == 'booked':
            raise UserError(_("Unit is already booked, cannot put on hold."))
        new_status = 'available' if self.status == 'hold' else 'hold'
        self.status = new_status

    @api.model
    def get_unit_matrix_data(self, company_id=None):
        """
        API method for OWL Interactive Matrix view:
        Returns structured data grouped by Block and Floor.
        """
        if not company_id or company_id == 'current':
            company_id = self.env.company.id
        elif isinstance(company_id, str) and company_id.isdigit():
            company_id = int(company_id)

        company = self.env["res.company"].browse(company_id)
        units = self.search([("company_id", "=", company_id)], order="floor desc, unit_no asc")

        blocks = sorted(list(set(units.mapped("block"))))
        if not blocks:
            blocks = ["B", "C"]

        total_count = len(units)
        available_count = len(units.filtered(lambda u: u.status == "available"))
        booked_count = len(units.filtered(lambda u: u.status == "booked"))
        hold_count = len(units.filtered(lambda u: u.status == "hold"))

        # Group data: { 'B': { 10: [units...], 9: [units...] }, 'C': { ... } }
        block_data = {}
        for b in blocks:
            b_units = units.filtered(lambda u: u.block == b)
            floors = sorted(list(set(b_units.mapped("floor"))), reverse=True)
            floor_groups = []
            for fl in floors:
                fl_units = b_units.filtered(lambda u: u.floor == fl)
                units_list = []
                for u in fl_units:
                    units_list.append({
                        "id": u.id,
                        "name": u.name,
                        "unit_no": u.unit_no,
                        "block": u.block,
                        "floor": u.floor,
                        "size": u.size_sq_yard,
                        "facing": u.facing,
                        "facing_label": dict(u._fields['facing'].selection).get(u.facing, u.facing),
                        "plc": u.location_charge,
                        "status": u.status,
                        "buyer": u.customer_name or (u.booking_lead_id.contact_name if u.booking_lead_id else "") or "",
                        "salesperson": u.salesperson_id.name if u.salesperson_id else "",
                        "lead_id": u.booking_lead_id.id if u.booking_lead_id else False,
                    })
                floor_groups.append({
                    "floor": fl,
                    "units": units_list,
                })
            block_data[b] = {
                "total": len(b_units),
                "available": len(b_units.filtered(lambda u: u.status == "available")),
                "booked": len(b_units.filtered(lambda u: u.status == "booked")),
                "floors": floor_groups,
            }

        # Size breakdown stats
        size_stats = {
            "265": len(units.filtered(lambda u: u.size_sq_yard == "265" and u.status == "available")),
            "270": len(units.filtered(lambda u: u.size_sq_yard == "270" and u.status == "available")),
            "275": len(units.filtered(lambda u: u.size_sq_yard == "275" and u.status == "available")),
        }

        return {
            "company_name": company.name,
            "company_id": company.id,
            "total_count": total_count,
            "available_count": available_count,
            "booked_count": booked_count,
            "hold_count": hold_count,
            "blocks": blocks,
            "block_data": block_data,
            "size_stats": size_stats,
        }
