/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { AttendanceSelfieDialog } from "./attendance_selfie_dialog";

patch(ActivityMenu.prototype, {
    async signInOut() {
        this.dropdown.close();
        if (this._attendanceInProgress) {
            return;
        }
        // Open the Selfie & 150m GPS Geofenced Attendance Dialog
        this.dialogService.add(AttendanceSelfieDialog, {
            onSuccess: async () => {
                await this.searchReadEmployee();
            },
        });
    }
});
