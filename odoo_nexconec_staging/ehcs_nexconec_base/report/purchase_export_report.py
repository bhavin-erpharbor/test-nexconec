from odoo import models

class PurchaseOrderExportXLS(models.AbstractModel):
    _name = 'report.ehcs_nexconec_base.report_po_export'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Export Purchase Orders To Vendor'

    def generate_xlsx_report(self, workbook, data, purchase_orders):
        worksheet = workbook.add_worksheet('Po Export')
        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 30)
        worksheet.set_column('C:C', 30)
        worksheet.set_column('D:D', 30)
        worksheet.set_column('E:E', 30)
        worksheet.set_column('F:F', 30)
        worksheet.set_column('G:G', 30)
        row = 0
        table_header_left = workbook.add_format(
            {'align': 'left', 'font_size': 12,
             'font_color': 'black', 'bold': True})
        table_row_left = workbook.add_format(
            {'align': 'left', 'font_size': 12, })
        table_row_right = workbook.add_format(
            {'align': 'right', 'font_size': 12, })
        worksheet.write(row, 0, 'Order Reference', table_header_left)
        worksheet.write(row, 1, 'Source Document', table_header_left)
        worksheet.write(row, 2, 'Last ETD', table_header_left)
        worksheet.write(row, 3, 'ETA', table_header_left)
        worksheet.write(row, 4, 'Lead Time', table_header_left)
        worksheet.write(row, 5, 'Shipping Methods', table_header_left)
        worksheet.write(row, 6, 'Dropship Address', table_header_left)

        for order in purchase_orders:
            row += 1
            worksheet.write(row, 0, order.name or '', table_row_left)
            worksheet.write(row, 1, order.origin or '', table_row_left)
            worksheet.write(row, 2, order.x_studio_schedule_date and order.x_studio_schedule_date.strftime('%d-%m-%Y') or '', table_row_right)
            worksheet.write(row, 3, order.x_studio_expected_arrival and order.x_studio_expected_arrival.strftime('%d-%m-%Y') or '', table_row_right)
            worksheet.write(row, 4, order.x_studio_lead_time_display, table_row_left)
            worksheet.write(row, 5, order.x_studio_many2one_field_yWWBO.name or '', table_row_left)
            worksheet.write(row, 6, order.dest_address_id.display_name or '', table_row_left)
