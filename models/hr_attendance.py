# -*- coding: utf-8 -*-
import math
from odoo import models, fields, api, _

def haversine_distance(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2:
        return 0.0
    R = 6371000.0  # Earth radius in meters
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    in_photo = fields.Image(string="Check-In Selfie", max_width=640, max_height=480)
    out_photo = fields.Image(string="Check-Out Selfie", max_width=640, max_height=480)

    in_distance = fields.Float(string="Check-In Distance (m)", readonly=True)
    out_distance = fields.Float(string="Check-Out Distance (m)", readonly=True)

    in_geofence_status = fields.Selection([
        ("inside", "Inside Geofence (<= 150m)"),
        ("outside", "Outside Geofence (> 150m)"),
        ("unknown", "Location Not Available")
    ], string="Check-In Status", default="unknown")

    out_geofence_status = fields.Selection([
        ("inside", "Inside Geofence (<= 150m)"),
        ("outside", "Outside Geofence (> 150m)"),
        ("unknown", "Location Not Available")
    ], string="Check-Out Status", default="unknown")

    in_map_url = fields.Char(string="Check-In Map", compute="_compute_map_urls")
    out_map_url = fields.Char(string="Check-Out Map", compute="_compute_map_urls")

    @api.depends("in_latitude", "in_longitude", "out_latitude", "out_longitude")
    def _compute_map_urls(self):
        for att in self:
            att.in_map_url = f"https://maps.google.com/?q={att.in_latitude},{att.in_longitude}" if att.in_latitude and att.in_longitude else False
            att.out_map_url = f"https://maps.google.com/?q={att.out_latitude},{att.out_longitude}" if att.out_latitude and att.out_longitude else False
