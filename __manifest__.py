# -*- coding: utf-8 -*-
{
    'name': 'SIRITA - ZKTeco Integrator',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Menerima Push Attendance Log melalui protokol ADMS ZKTeco & Tarik Data User',
    'description': """
        Modul khusus penerima data Push Kehadiran dari mesin sidik jari/wajah ZKTeco (seperti X100-C, MB series) menggunakan metode ADMS/iClock.
        Fitur:
        - HTTP Controller Endpoint (/iclock/cdata) Publik
        - Registrasi Serial Number Mesin ZKTeco (Keamanan Whitelist)
        - Mapping PIN Mesin ke PIN hr.employee
        - Tarik/Pull Daftar User terdaftar di mesin ke Odoo (Tabel Antrean)
        - Auto Create hr.attendance records.
    """,
    'author': 'SIRITA | sufyaldys@gmail.com',
    'depends': ['base', 'hr', 'hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
        'views/zk_user_queue_view.xml',
        'views/zk_command_views.xml',
        'views/zk_device_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'GPL-3',
}
