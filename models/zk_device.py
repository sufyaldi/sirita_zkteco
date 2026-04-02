# -*- coding: utf-8 -*-
from odoo import models, fields

class ZKDevice(models.Model):
    _name = 'zkteco.device'
    _description = 'Registered ZKTeco ADMS Devices'

    name = fields.Char(string='Nama Mesin / Lokasi', required=True)
    serial_number = fields.Char(string='Serial Number (SN)', required=True, help="Harus sama persis dengan SN di hardware ZKTeco")
    last_seen = fields.Datetime(string='Terakhir Online', readonly=True)
    is_active = fields.Boolean(string='Aktif Menerima Data', default=True)
    
    # Smart button counter
    queue_count = fields.Integer(compute='_compute_queue_count')
    command_count = fields.Integer(compute='_compute_command_count')
    debug_data = fields.Text(string='Raw Debug Data', readonly=True)

    def _compute_queue_count(self):
        for rec in self:
            rec.queue_count = self.env['zkteco.user.queue'].search_count([('device_id', '=', rec.id)])

    def _compute_command_count(self):
        for rec in self:
            rec.command_count = self.env['zkteco.command'].search_count([('device_id', '=', rec.id)])

    def action_pull_users(self):
        """Kirim perintah ke mesin untuk tarik daftar user"""
        self.ensure_one()
        Command = self.env['zkteco.command']
        
        # Cek apakah sudah ada perintah pending yang sama
        existing = Command.search([
            ('device_id', '=', self.id),
            ('command_text', '=', 'DATA QUERY USERINFO'),
            ('status', '=', 'pending')
        ])
        
        if not existing:
            Command.create({
                'device_id': self.id,
                'command_text': 'DATA QUERY USERINFO',
                'status': 'pending'
            })
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Berhasil',
                'message': 'Perintah Tarik User telah dikirim ke antrean. Mesin akan mengeksekusi saat melakukan sinkronisasi berikutnya.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_user_queue(self):
        """View for smart button"""
        return {
            'name': 'Antrean User Mesin',
            'type': 'ir.actions.act_window',
            'res_model': 'zkteco.user.queue',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id}
        }

    def action_view_commands(self):
        """View for smart button"""
        return {
            'name': 'Log Perintah Mesin',
            'type': 'ir.actions.act_window',
            'res_model': 'zkteco.command',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id}
        }

    def action_pull_users_alt(self):
        """Kirim perintah alternatif (SELECT) jika QUERY tidak direspon data"""
        self.ensure_one()
        self.env['zkteco.command'].create({
            'device_id': self.id,
            'command_text': 'DATA SELECT USERINFO',
            'status': 'pending'
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Mode Alternatif',
                'message': 'Perintah SELECT dikirim. Gunakan ini jika penarikan standar tidak berhasil.',
                'type': 'warning',
            }
        }

    def action_pull_attendance(self):
        """Kirim perintah untuk menarik semua log absensi (ATTLOG)"""
        self.ensure_one()
        self.env['zkteco.command'].create({
            'device_id': self.id,
            'command_text': 'DATA QUERY ATTLOG',
            'status': 'pending'
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Berhasil',
                'message': 'Perintah Tarik Log Absensi telah dikirim ke antrean.',
                'type': 'success',
            }
        }

    _sql_constraints = [
        ('unique_serial_number', 'unique(serial_number)', 'Mesin dengan Serial Number ini sudah terdaftar!')
    ]
