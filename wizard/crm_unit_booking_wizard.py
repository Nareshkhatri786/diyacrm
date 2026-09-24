# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CrmUnitBookingWizard(models.TransientModel):
    _name = "crm.unit.booking.wizard"
    _description = "Book Real Estate Property Unit"

    unit_id = fields.Many2one("crm.property.unit", string="Property Unit", required=True)
    company_id = fields.Many2one("res.company", related="unit_id.company_id", readonly=True)
    unit_name = fields.Char(string="Unit Code", related="unit_id.name", readonly=True)
    block = fields.Selection(related="unit_id.block", readonly=True)
    floor = fields.Selection(related="unit_id.floor", readonly=True)
    size_sq_yard = fields.Selection(related="unit_id.size_sq_yard", readonly=True)
    facing = fields.Selection(related="unit_id.facing", readonly=True)
    location_charge = fields.Boolean(related="unit_id.location_charge", readonly=True)

    lead_id = fields.Many2one("crm.lead", string="Select Lead / Opportunity")
    customer_name = fields.Char(string="Customer / Buyer Name", required=True)
    customer_phone = fields.Char(string="Contact Phone")
    salesperson_id = fields.Many2one("res.users", string="Sales Executive", 
                                     default=lambda self: self.env.user, required=True)
    booking_date = fields.Date(string="Booking Date", default=fields.Date.context_today, required=True)
    token_amount = fields.Float(string="Token / Advance Amount")
    remarks = fields.Text(string="Booking Notes / Terms")

    @api.onchange("lead_id")
    def _onchange_lead_id(self):
        if self.lead_id:
            self.customer_name = self.lead_id.contact_name or self.lead_id.name
            self.customer_phone = self.lead_id.phone
            if self.lead_id.user_id:
                self.salesperson_id = self.lead_id.user_id

    def action_confirm_booking(self):
        self.ensure_one()
        unit = self.unit_id
        if unit.status == "booked":
            raise UserError(_("Unit %s has already been booked by another client!") % unit.name)

        unit.write({
            "status": "booked",
            "booking_lead_id": self.lead_id.id if self.lead_id else False,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "salesperson_id": self.salesperson_id.id,
            "booking_date": self.booking_date,
            "remarks": self.remarks,
        })

        if self.lead_id:
            self.lead_id.write({
                "property_unit_id": unit.id,
            })
            token_info = f"<br/>Advance / Token: ₹ {self.token_amount:,.2f}" if self.token_amount > 0 else ""
            plc_info = "Yes (PLC Applicable)" if unit.location_charge else "No"
            facing_label = dict(unit._fields['facing'].selection).get(unit.facing, unit.facing)
            body = f"""
            <div style="background-color: #f0fdf4; border-left: 4px solid #16a34a; padding: 10px; border-radius: 4px;">
                <p style="margin: 0 0 5px 0; color: #15803d; font-weight: bold; font-size: 14px;">
                    🎉 🏢 PROPERTY UNIT BOOKED: {unit.name}
                </p>
                <div style="font-size: 12.5px; color: #1e293b;">
                    • <b>Block:</b> {unit.block} | <b>Floor:</b> {unit.floor}<br/>
                    • <b>Size:</b> {unit.size_sq_yard} Sq. Yards<br/>
                    • <b>Facing:</b> {facing_label} | <b>Location Charge (PLC):</b> {plc_info}<br/>
                    • <b>Booked By:</b> {self.customer_name} ({self.customer_phone or 'No Phone'})<br/>
                    • <b>Salesperson:</b> {self.salesperson_id.name} | <b>Date:</b> {self.booking_date}
                    {token_info}
                </div>
            </div>
            """
            self.lead_id.message_post(body=body)

        unit.message_post(
            body=_("Unit booked for %s by %s on %s") % (self.customer_name, self.salesperson_id.name, self.booking_date)
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Booking Confirmed!"),
                "message": _("Unit %s successfully booked for %s!") % (unit.name, self.customer_name),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            }
        }
