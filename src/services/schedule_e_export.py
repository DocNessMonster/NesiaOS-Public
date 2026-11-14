"""Formatting helpers for preliminary Schedule E exports. No database writes."""
import csv
import io


def schedule_e_csv(report):
    """Produce a readable, non-filing-ready CSV for tax preparer review."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["NesiaOS Preliminary Schedule E Worksheet", report["year"]])
    writer.writerow(["STATUS", "NOT FILING READY"])
    writer.writerow([])
    writer.writerow(["Schedule E line", "Category", "Amount USD"])
    for line, amount in sorted(report["lines"].items()):
        writer.writerow([line, report["labels"][line], f"{amount:.2f}"])
    writer.writerow([])
    writer.writerow(["Known income", "", f"{report['income']:.2f}"])
    writer.writerow(["Known expenses excluding depreciation", "",
                     f"{report['known_expenses_excluding_depreciation']:.2f}"])
    writer.writerow(["Provisional difference (NOT taxable income)", "",
                     f"{report['provisional_difference']:.2f}"])
    writer.writerow(["Capital spending (NOT current deduction)", "",
                     f"{report['capital_spending']:.2f}"])
    writer.writerow([])
    writer.writerow(["Capital improvements — depreciation not calculated"])
    writer.writerow(["Description", "Completion date", "Placed in service", "Cost USD"])
    for asset in report["capital_improvements"]:
        writer.writerow([
            asset["description"], asset["completion_date"],
            asset["placed_in_service_date"] or "",
            f"{asset['cost_cents'] / 100:.2f}",
        ])
    writer.writerow([])
    writer.writerow(["Items requiring review"])
    for item in report["review"]:
        writer.writerow([item])
    return output.getvalue().encode("utf-8-sig")
