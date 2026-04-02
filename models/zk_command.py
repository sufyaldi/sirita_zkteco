# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ZKCommand(models.Model):
    _name = 'zkteco.command'
    _description = 'ZKTeco Device Commands'
    _order = 'id asc'

    device_id = fields.Many2one('zkteco.device', string='Device', required=True, ondelete='cascade')
    command_text = fields.Char(string='Command', required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('completed', 'Completed'),
        ('error', 'Error')
    ], string='Status', default='pending')
    
    response = fields.Text(string='Response From Device')
    timestamp = fields.Datetime(string='Created At', default=fields.Datetime.now)
