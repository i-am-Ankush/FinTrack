from flask import Blueprint, request, send_file, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import get_db
from datetime import datetime
import io

export_bp = Blueprint('export', __name__)

@export_bp.route('/pdf', methods=['GET'])
@jwt_required()
def export_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm

    user_id = get_jwt_identity()
    now     = datetime.now()
    month   = int(request.args.get('month', now.month))
    year    = int(request.args.get('year',  now.year))
    month_str = f"{year}-{month:02d}"
    month_label = datetime(year, month, 1).strftime('%B %Y')

    conn = get_db()
    rows = conn.execute(
        "SELECT date, description, category, amount FROM transactions "
        "WHERE user_id=? AND date LIKE ? ORDER BY date",
        (user_id, f"{month_str}%")
    ).fetchall()

    budget_row = conn.execute(
        "SELECT amount FROM budgets WHERE user_id=? AND month=? AND year=?",
        (user_id, month, year)
    ).fetchone()
    conn.close()

    budget  = budget_row['amount'] if budget_row else 0
    total   = sum(r['amount'] for r in rows if r['amount'] > 0)
    income  = abs(sum(r['amount'] for r in rows if r['amount'] < 0))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    styles  = getSampleStyleSheet()
    title_s = ParagraphStyle('title', parent=styles['Heading1'], fontSize=18, spaceAfter=6)
    sub_s   = ParagraphStyle('sub',   parent=styles['Normal'],   fontSize=10, textColor=colors.grey)

    story = [
        Paragraph("FinTrack — Monthly Report", title_s),
        Paragraph(month_label, sub_s),
        Spacer(1, 6*mm),
    ]

    # Summary table
    summary_data = [
        ['Total Spent', f"₹{total:,.2f}"],
        ['Total Income', f"₹{income:,.2f}"],
        ['Monthly Budget', f"₹{budget:,.2f}"],
        ['Remaining', f"₹{budget - total:,.2f}"],
    ]
    summary_tbl = Table(summary_data, colWidths=[80*mm, 60*mm])
    summary_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F4FF')),
        ('FONTNAME',   (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE',   (0,0), (-1,-1), 10),
        ('FONTNAME',   (0,0), (0,-1), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#E8EDFF'), colors.HexColor('#F5F7FF')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story += [summary_tbl, Spacer(1, 6*mm)]

    # Transactions table
    if rows:
        story.append(Paragraph("Transactions", styles['Heading2']))
        story.append(Spacer(1, 3*mm))

        header = [['Date', 'Description', 'Category', 'Amount (₹)']]
        data   = header + [
            [r['date'], r['description'][:40], r['category'],
             f"+{r['amount']:,.2f}" if r['amount'] > 0 else f"{r['amount']:,.2f}"]
            for r in rows
        ]

        tbl = Table(data, colWidths=[28*mm, 80*mm, 35*mm, 32*mm])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4F46E5')),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9F9FF')]),
            ('GRID', (0,0), (-1,-1), 0.3, colors.lightgrey),
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("No transactions found for this month.", styles['Normal']))

    doc.build(story)
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f"fintrack_{month_str}.pdf")
