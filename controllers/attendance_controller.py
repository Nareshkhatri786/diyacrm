# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError

class DiyaCrmAttendanceController(http.Controller):

    @http.route("/diyacrm/attendance/get_config", type="jsonrpc", auth="user")
    def get_attendance_config(self):
        employee = request.env.user.employee_id
        if not employee:
            return {"status": "error", "message": "No employee profile linked to current user."}
        return {"status": "success", "config": employee.get_attendance_config()}

    @http.route("/diyacrm/attendance/check_in_out", type="jsonrpc", auth="user")
    def check_in_out_selfie(self, photo=None, latitude=None, longitude=None):
        employee = request.env.user.employee_id
        if not employee:
            raise UserError(_("No employee profile found for current user."))
        return employee.process_selfie_attendance(photo=photo, latitude=latitude, longitude=longitude)
