# -*- coding: utf-8 -*-
from odoo import http, fields, models
from odoo.http import request
import logging, traceback
from datetime import datetime

_logger = logging.getLogger(__name__)

class ZKTecoADMSController(http.Controller):

    @http.route(['/iclock/cdata'], type='http', auth="none", csrf=False, methods=['GET', 'POST'])
    def iclock_cdata(self, **kwargs):
        # Paksa gunakan Administrator (ID=1) di seluruh fungsi untuk menghindari Singleton Error
        env = request.env(user=1)
        sn = request.params.get('SN')
        if not sn: return "ERROR: SN NOT FOUND"
            
        Device = env['zkteco.device'].sudo()
        device = Device.search([('serial_number', '=', sn), ('is_active', '=', True)], limit=1)
        if not device: return "ERROR: UNREG DEVICE"

        device.last_seen = fields.Datetime.now()
        
        if request.httprequest.method == 'GET':
            response_options = (f"GET OPTION FROM: {sn}\r\nStamp=9999\r\nOpStamp=9999\r\nErrorDelay=60\r\nDelay=10\r\nRealtime=1\r\nEncrypt=0\r\n")
            return request.make_response(response_options, headers=[('Content-Type', 'text/plain')])

        if request.httprequest.method == 'POST':
            table_type = request.params.get('table', '').upper()
            raw_data = request.httprequest.get_data()
            try:
                body = raw_data.decode('latin-1')
            except Exception: return "OK"

            # Auto-detect table from body if not in URL
            if not table_type and body:
                first_line = body.split('\n')[0].upper().strip()
                if 'USERINFO' in first_line or 'USER ' in first_line: table_type = 'USERINFO'
                elif 'ATTLOG' in first_line: table_type = 'ATTLOG'
                elif 'OPERLOG' in first_line: table_type = 'OPERLOG'
                elif 'BIODATA' in first_line: table_type = 'BIODATA'

            _logger.info("ADMS Hit: SN=%s, Table=%s", sn, table_type)
            device.debug_data = f"Table: {table_type}\nSample:\n{body[:1000]}"

            lines = body.split('\n')
            
            # CASE A: Log Absensi
            if table_type == 'ATTLOG':
                _logger.info("Memproses %d baris ATTLOG dari %s", len(lines), sn)
                for line in lines:
                    line = line.strip()
                    if not line or 'ATTLOG' in line.upper(): continue
                    
                    data = self._parse_adms_line(line)
                    pin = data.get('PIN') or data.get('ID')
                    time_str = data.get('TIME')
                    
                    if not pin or not time_str:
                        parts = line.split() 
                        if len(parts) >= 3:
                            pin = parts[0]
                            time_str = f"{parts[1]} {parts[2]}"

                    if pin and time_str:
                        try:
                            time_obj = False
                            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%d-%m-%Y %H:%M:%S'):
                                try:
                                    time_obj = datetime.strptime(time_str.strip(), fmt)
                                    break
                                except: continue
                            
                            if time_obj:
                                try:
                                    self._process_attendance(pin, time_obj, device)
                                except Exception:
                                    _logger.error("Error memproses PIN %s: %s", pin, traceback.format_exc())
                            else:
                                _logger.warning("Gagal parse format waktu: %s", time_str)
                        except Exception as e:
                            _logger.error("Error fatal pada baris log: %s", traceback.format_exc())
                            continue
                return "OK"
            
            # CASE B: Daftar User (Sangat Robust)
            elif table_type in ['USERINFO', 'USER', 'OPERLOG', 'BIODATA', 'TEMPLATE']:
                UserQueue = env['zkteco.user.queue'].sudo()
                user_count = 0
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    data = self._parse_adms_line(line)
                    pin = data.get('PIN') or data.get('ID')
                    name = data.get('NAME') or data.get('Name') or data.get('NAME1') or ""
                    
                    if pin:
                        pin_str = str(pin).strip()
                        existing = UserQueue.search([('device_id', '=', device.id), ('zk_pin', '=', pin_str)], limit=1)
                        if existing:
                            if name and existing.status == 'new': existing.write({'name': name})
                        else:
                            UserQueue.create({'device_id': device.id, 'zk_pin': pin_str, 'name': name})
                            user_count += 1
                
                if user_count > 0:
                    _logger.info("ADMS Sinkron: %d user baru dari %s (%s)", user_count, sn, table_type)
                return "OK"

            return "OK"

    def _parse_adms_line(self, line):
        """
        Parser untuk format Key=Value (misal: PIN=123\tTIME=2024-01-01...)
        """
        res = {}
        parts = line.split('\t')
        for p in parts:
            if '=' in p:
                kv = p.split('=', 1)
                key_raw = kv[0].strip().upper()
                key = key_raw.split()[-1] if ' ' in key_raw else key_raw
                res[key] = kv[1].strip()
        return res

    def _process_attendance(self, zk_pin, att_time, device):
        # Gunakan with_user(1) untuk menghindari 'Expected singleton: res.users()' di auth="none"
        env = request.env(user=1)
        Employee = env['hr.employee'].sudo()
        Attendance = env['hr.attendance'].sudo()
        
        employee = Employee.search([('zk_pin', '=', str(zk_pin))], limit=1)
        if not employee:
            _logger.warning("PIN %s tidak terdaftar di Karyawan manapun!", zk_pin)
            return
        
        _logger.info("Mencatat absen untuk: %s (PIN: %s) pada %s", employee.name, zk_pin, att_time)
        open_att = Attendance.search([('employee_id', '=', employee.id), ('check_out', '=', False)], limit=1)
        if open_att:
            # Jika selisih lebih dari 2 menit, catat sebagai Check Out
            if (att_time - open_att.check_in).total_seconds() > 120:
                open_att.check_out = att_time
        else:
            Attendance.create({'employee_id': employee.id, 'check_in': att_time})

    @http.route(['/iclock/getrequest'], type='http', auth="none", csrf=False)
    def iclock_getrequest(self, **kwargs):
        env = request.env(user=1)
        sn = request.params.get('SN')
        if not sn: return "OK"
        Device = env['zkteco.device'].sudo()
        device = Device.search([('serial_number', '=', sn), ('is_active', '=', True)], limit=1)
        if not device: return "OK"
        cmd = env['zkteco.command'].sudo().search([('device_id', '=', device.id), ('status', '=', 'pending')], order='id asc', limit=1)
        if cmd:
            cmd.write({'status': 'sent'})
            return request.make_response(f"C:{cmd.id}:{cmd.command_text}", headers=[('Content-Type', 'text/plain')])
        return "OK"

    @http.route(['/iclock/devicecmd'], type='http', auth="none", csrf=False, methods=['POST'])
    def iclock_devicecmd(self, **kwargs):
        env = request.env(user=1)
        sn = request.params.get('SN')
        body = request.httprequest.get_data().decode('latin-1')
        if ":" in body:
            parts = body.split(":")
            cmd_id_str, res = parts[0], parts[1] if len(parts) > 1 else ""
            try:
                cmd = env['zkteco.command'].sudo().browse(int(cmd_id_str))
                if cmd.exists():
                    status = 'completed' if 'OK' in res or 'Return=0' in res else 'error'
                    cmd.write({'status': status, 'response': res})
            except Exception: pass
        return "OK"
