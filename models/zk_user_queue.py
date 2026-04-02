# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ZKUserQueue(models.Model):
    _name = 'zkteco.user.queue'
    _description = 'ZKTeco User Sync Queue'
    _order = 'zk_pin asc'

    device_id = fields.Many2one('zkteco.device', string='Device', required=True)
    zk_pin = fields.Char(string='PIN', required=True)
    name = fields.Char(string='Name on Device')
    status = fields.Selection([
        ('new', 'New'),
        ('mapped', 'Mapped'),
        ('ignored', 'Ignored')
    ], string='Status', default='new')
    
    employee_id = fields.Many2one('hr.employee', string='Mapped Employee')

    _sql_constraints = [
        ('unique_pin_device', 'unique(zk_pin, device_id)', 'PIN and Device must be unique!')
    ]

    def action_map_to_employee(self):
        """Map back to employee or create new if not found"""
        self.ensure_one()
        Employee = self.env['hr.employee']
        
        # 1. Prioritas 1: Jika user sudah memilih Employee secara manual di form antrean
        employee = self.employee_id
        
        # 2. Prioritas 2: Cari berdasarkan PIN (Hubungkan otomatis)
        if not employee:
            employee = Employee.search([('zk_pin', '=', self.zk_pin)], limit=1)
            
        # 3. Prioritas 3: Cari berdasarkan Nama (Exact Match) untuk menghindari duplikat
        if not employee and self.name:
            employee = Employee.search([('name', '=', self.name)], limit=1)
        
        # 4. Jika tetap tidak ketemu, baru buat record baru
        if not employee:
            employee = Employee.create({
                'name': self.name or f"New ZK User {self.zk_pin}",
                'zk_pin': self.zk_pin,
            })
        else:
            # Pastikan PIN mesin tersimpan di Employee tersebut jika belum ada
            if not employee.zk_pin:
                employee.write({'zk_pin': self.zk_pin})
            
        self.write({
            'employee_id': employee.id,
            'status': 'mapped'
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': employee.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def write(self, vals):
        # Jika user mengubah pemetaan karyawan secara manual
        if 'employee_id' in vals and vals.get('employee_id'):
            Employee = self.env['hr.employee']
            new_emp = Employee.browse(vals.get('employee_id'))
            
            for rec in self:
                # 1. Bersihkan PIN dari karyawan lama (opsional tapi disarankan agar rapi)
                # search employee with same pin and clear it
                old_owners = Employee.search([('zk_pin', '=', rec.zk_pin)])
                if old_owners:
                    old_owners.write({'zk_pin': False})
                
                # 2. Update status jadi mapped jika baru pertama kali di-link
                if rec.status == 'new':
                    vals['status'] = 'mapped'
                
                # 3. Paksa tulis PIN ke Karyawan terpilih yang baru
                new_emp.write({'zk_pin': rec.zk_pin})
        
        return super(ZKUserQueue, self).write(vals)
