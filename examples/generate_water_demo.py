"""Generate six entirely invented utility PDFs; never reads private documents."""
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas

OUT = Path(__file__).resolve().parent
TOTALS = {4: '75.00', 5: '82.50', 6: '91.20', 7: '105.40', 8: '98.60', 9: '87.30'}


def generate():
    outputs = []
    for month, value in TOTALS.items():
        total = Decimal(value)
        path = OUT / f'demo_water_bill_2026_{month:02d}.pdf'
        c = Canvas(str(path), pagesize=(612, 792), invariant=1)
        c.setTitle(f'SYNTHETIC DEMO Water Bill - 2026-{month:02d}')
        c.setAuthor('NesiaOS - SYNTHETIC DEMO')
        c.setFillColor(colors.HexColor('#17354c'))
        c.rect(0, 702, 612, 90, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 18)
        c.drawString(36, 755, 'SYNTHETIC DEMO WATER BILL')
        c.setFont('Helvetica', 11)
        c.drawString(36, 731, 'Invented utility data - not issued by a water company')
        c.setFillColor(colors.black)
        c.setFont('Helvetica', 11)
        lines = [
            'DEMO WATER AUTHORITY | Example Owner (fictional)',
            'Account Number: 0000002026',
            'Service Address: Fictional Demo Property (not a real address)',
            f'Billing Date: {month:02d}/17/2026',
            f'Due Date: {month+1:02d}/02/2026',
            'Previous Balance $0.00', 'Payment Received 0.00',
            'Balance Forward 0.00', 'Total Adjustments (Billed & Unbilled) 0.00',
            f'Current Charges {total:.2f}', f'Total Amount Due ${total:.2f}',
        ]
        y = 670
        for line in lines:
            c.drawString(36, y, line)
            y -= 22
        period = f'{month-1:02d}-17-2026 - {month:02d}-17-2026'
        sections = [('Water Residential City', total - Decimal('42.00')),
                    ('Wastewater Residential City', Decimal('22.00')),
                    ('Solid Waste Residential', Decimal('20.00'))]
        for index, (label, amount) in enumerate(sections):
            # Exercise continuation-page extraction with the July fixture.
            if month == 7 and index == 2:
                c.setFont('Helvetica-Oblique', 10)
                c.drawString(36, 40, 'SYNTHETIC DEMO - trash charges continue on page 2')
                c.showPage()
                c.setFont('Helvetica-Bold', 15)
                c.drawString(36, 750, 'SYNTHETIC DEMO - continued utility charges')
                y = 700
            c.setFont('Helvetica-Bold', 11)
            c.drawString(36, y, f'{label}: {period}')
            c.setFont('Helvetica', 11)
            c.drawString(36, y-22, f'Invented combined service charge {amount:.2f}')
            c.drawString(36, y-44, f'Subtotal {amount:.2f}')
            y -= 82
        c.setFont('Helvetica-Oblique', 10)
        c.drawString(36, 25, 'SYNTHETIC DEMO - all identifiers, dates and amounts are invented.')
        c.save()
        outputs.append(path)
    expected = OUT / 'demo_water_expected_totals.csv'
    with expected.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['month', 'water_billed', 'water_paid', 'utility_reimbursements'])
        for month, value in TOTALS.items():
            writer.writerow([f'2026-{month:02d}', value, value, '75.00' if month == 6 else '0.00'])
    outputs.append(expected)
    return outputs


if __name__ == '__main__':
    for path in generate():
        print(path.name)
