# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DiyaCrmDashboardController(http.Controller):

    @http.route('/diyacrm/dashboard/get_data', type='jsonrpc', auth='user')
    def get_dashboard_data(self, period='48h', company_id='all', user_id='all', **kwargs):
        """Delegate to the central crm.lead get_dashboard_data method."""
        try:
            return request.env['crm.lead'].get_dashboard_data(
                period=period,
                company_id=company_id,
                user_id=user_id
            )
        except Exception as e:
            _logger.exception("Error in dashboard controller get_dashboard_data: %s", str(e))
            return {"status": "error", "message": str(e)}
