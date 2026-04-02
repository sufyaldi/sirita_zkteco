# -*- coding: utf-8 -*-
from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    zk_pin = fields.Char(string='ID/PIN Mesin Absensi', help="Nomor PIN atau badge yang didaftarkan di mesin ZKTeco")
