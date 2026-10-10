# -*- coding: utf-8 -*-
from urllib.parse import unquote, urlencode
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.webmanifest import WebManifest

class SignatureWebManifest(WebManifest):

    def _get_webmanifest(self):
        manifest = super()._get_webmanifest()
        manifest['name'] = 'Signature Properties'
        manifest['short_name'] = 'Signature Properties'
        manifest['description'] = 'Signature Properties - Your Growth Partner'
        manifest['background_color'] = '#FFFFFF'
        manifest['theme_color'] = '#FFFFFF'
        manifest['icons'] = [
            {
                'src': '/diyacrm/static/src/img/signature_pwa_192.png',
                'sizes': '192x192',
                'type': 'image/png',
                'purpose': 'any',
            },
            {
                'src': '/diyacrm/static/src/img/signature_pwa_512.png',
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'any',
            },
            {
                'src': '/diyacrm/static/src/img/signature_pwa_maskable_192.png',
                'sizes': '192x192',
                'type': 'image/png',
                'purpose': 'maskable',
            },
            {
                'src': '/diyacrm/static/src/img/signature_pwa_maskable_512.png',
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'maskable',
            },
        ]
        return manifest

    def _icon_path(self):
        return 'diyacrm/static/src/img/signature_pwa_192.png'

    @http.route('/web/manifest.webmanifest', type='http', auth='public', methods=['GET'], readonly=True)
    def webmanifest(self):
        return request.make_json_response(self._get_webmanifest(), {
            'Content-Type': 'application/manifest+json'
        })

    @http.route('/scoped_app', type='http', auth='public', methods=['GET'])
    def scoped_app(self, app_id, path='', app_name=''):
        response = super().scoped_app(app_id, path=path, app_name=app_name)
        if hasattr(response, 'qcontext') and isinstance(response.qcontext, dict):
            response.qcontext['apple_touch_icon'] = '/diyacrm/static/src/img/signature_pwa_ios.png'
            if not app_name or app_name.lower() in ('odoo', ''):
                response.qcontext['app_name'] = 'Signature Properties'
        return response
