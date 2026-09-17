# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .hr_attendance import haversine_distance

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    work_latitude = fields.Float(string="Assigned Site Latitude", digits=(10, 7), tracking=True)
    work_longitude = fields.Float(string="Assigned Site Longitude", digits=(10, 7), tracking=True)
    geofence_radius = fields.Float(string="Allowed Radius (Meters)", default=150.0, tracking=True)
    require_selfie = fields.Boolean(string="Require Selfie Photo", default=True)
    require_geofence = fields.Boolean(string="Require 150m Geofence", default=True)

    def get_attendance_config(self):
        self.ensure_one()
        return {
            "employee_id": self.id,
            "employee_name": self.name,
            "attendance_state": self.attendance_state,
            "work_latitude": self.work_latitude or 0.0,
            "work_longitude": self.work_longitude or 0.0,
            "geofence_radius": self.geofence_radius or 150.0,
            "require_selfie": self.require_selfie,
            "require_geofence": self.require_geofence,
        }

    def process_selfie_attendance(self, photo=None, latitude=None, longitude=None):
        self.ensure_one()
        is_check_in = (self.attendance_state != "checked_in")

        # 1. Selfie Validation
        if self.require_selfie and not photo:
            raise UserError(_("Selfie photo is mandatory! Please allow camera access and capture your photo to proceed."))

        # 2. Geofence Validation
        distance = 0.0
        geofence_status = "unknown"
        if self.require_geofence:
            if not latitude or not longitude:
                raise UserError(_("GPS Location is mandatory! Please enable location/GPS in your browser/device settings."))

            if self.work_latitude and self.work_longitude:
                distance = haversine_distance(latitude, longitude, self.work_latitude, self.work_longitude)
                allowed_radius = self.geofence_radius or 150.0
                if distance > allowed_radius:
                    raise UserError(_("Check-in/out Blocked! You are %.1f meters away from your assigned work site. Allowed radius is %d meters.") % (distance, int(allowed_radius)))
                geofence_status = "inside"
            else:
                geofence_status = "inside"

        # 3. Clean Photo (strip data:image/...;base64, prefix if present)
        clean_photo = photo
        if clean_photo and "," in clean_photo:
            clean_photo = clean_photo.split(",", 1)[1]

        # 4. Perform Attendance Record Creation / Update
        action_date = fields.Datetime.now()
        if is_check_in:
            vals = {
                "employee_id": self.id,
                "check_in": action_date,
                "in_latitude": latitude or 0.0,
                "in_longitude": longitude or 0.0,
                "in_mode": "systray",
                "in_photo": clean_photo,
                "in_distance": distance,
                "in_geofence_status": geofence_status,
            }
            attendance = self.env["hr.attendance"].create(vals)
        else:
            attendance = self.env["hr.attendance"].search([
                ("employee_id", "=", self.id),
                ("check_out", "=", False)
            ], order="check_in desc", limit=1)
            if attendance:
                attendance.write({
                    "check_out": action_date,
                    "out_latitude": latitude or 0.0,
                    "out_longitude": longitude or 0.0,
                    "out_mode": "systray",
                    "out_photo": clean_photo,
                    "out_distance": distance,
                    "out_geofence_status": geofence_status,
                })
            else:
                raise UserError(_("Could not find open check-in record to check out."))

        return {
            "status": "success",
            "attendance_state": self.attendance_state,
            "message": "Checked In successfully!" if is_check_in else "Checked Out successfully!",
            "distance": round(distance, 1),
            "attendance_id": attendance.id if attendance else False,
        }
