import io
from datetime import datetime

import pandas as pd


def generate_breakdown_excel(
    breakdown_data,
    overall_totals,
    manual_inputs_by_district,
    manual_inputs_meta,
    manual_data_types,
    school_year,
    host_filter,
) -> bytes:
    """Generate a multi-sheet Excel file for the detailed breakdown report."""

    output = io.BytesIO()

    # We must preserve the ordering of districts in breakdown_data
    district_names = list(breakdown_data.keys())

    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    workbook = writer.book

    # Document properties
    workbook.set_properties(
        {
            "title": f"District Breakdown {school_year}",
            "creator": "Polaris VMS",
            "created": datetime.now(),
        }
    )

    # --- Formatting ---
    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#366092",
            "font_color": "white",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )

    left_header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#366092",
            "font_color": "white",
            "border": 1,
            "align": "left",
            "valign": "vcenter",
        }
    )

    section_header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#e2e8f0",
            "border": 1,
            "align": "left",
            "valign": "vcenter",
        }
    )

    cell_format = workbook.add_format(
        {
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )

    left_cell_format = workbook.add_format(
        {
            "border": 1,
            "align": "left",
            "valign": "vcenter",
        }
    )

    indent_cell_format = workbook.add_format(
        {
            "border": 1,
            "align": "left",
            "valign": "vcenter",
            "indent": 1,
        }
    )

    # ==========================================
    # SHEET 1: SUMMARY
    # ==========================================
    worksheet_summary = workbook.add_worksheet("Summary")

    # Write Headers
    headers = ["Metric", "Overall"] + district_names
    for col_num, header_text in enumerate(headers):
        fmt = left_header_format if col_num == 0 else header_format
        worksheet_summary.write(0, col_num, header_text, fmt)

    row = 1

    def write_section(title):
        nonlocal row
        worksheet_summary.merge_range(
            row, 0, row, len(headers) - 1, title, section_header_format
        )
        row += 1

    def write_metric(
        label, overall_val, metric_key, is_indented=False, is_math_relays=False
    ):
        nonlocal row
        fmt = indent_cell_format if is_indented else left_cell_format
        worksheet_summary.write(row, 0, label, fmt)
        worksheet_summary.write(row, 1, str(overall_val), cell_format)

        for col_idx, d_name in enumerate(district_names):
            d_data = breakdown_data[d_name]
            if is_math_relays:
                val = d_data.get(metric_key, 0)
            else:
                val = (
                    d_data.get("in_person_events", {})
                    if metric_key.startswith("in_person_events.")
                    else d_data
                )
                keys = metric_key.split(".")
                for k in keys:
                    if isinstance(val, dict):
                        val = val.get(k, 0)
                    else:
                        break

            if isinstance(val, dict):  # For total/unique dicts
                val_str = f"{val.get('total', 0)} / {val.get('unique', 0)}"
            else:
                val_str = str(val)

            worksheet_summary.write(row, col_idx + 2, val_str, cell_format)
        row += 1

    # In-Person Events
    write_section("In-Person Events")

    def format_total_unique(data_dict):
        return f"{data_dict.get('total', 0)} / {data_dict.get('unique', 0)}"

    write_metric(
        "Students (In-Person)",
        format_total_unique(overall_totals.get("in_person_students", {})),
        "in_person_students",
    )
    write_metric(
        "Volunteers (In-Person)",
        format_total_unique(overall_totals.get("in_person_volunteers", {})),
        "in_person_volunteers",
    )
    write_metric(
        "In-Person Events",
        str(overall_totals.get("in_person_events_count", 0)),
        "in_person_events_count",
    )

    write_metric(
        "Career Jumping",
        str(overall_totals.get("in_person_events", {}).get("career_jumping", 0)),
        "in_person_events.career_jumping",
        True,
    )
    write_metric(
        "Career Speakers",
        str(overall_totals.get("in_person_events", {}).get("career_speakers", 0)),
        "in_person_events.career_speakers",
        True,
    )
    write_metric(
        "Career Fair / HS",
        str(overall_totals.get("in_person_events", {}).get("career_fair_hs", 0)),
        "in_person_events.career_fair_hs",
        True,
    )
    write_metric(
        "HealthStart",
        str(overall_totals.get("in_person_events", {}).get("healthstart", 0)),
        "in_person_events.healthstart",
        True,
    )
    write_metric(
        "Business Finance IT",
        str(overall_totals.get("in_person_events", {}).get("bfi", 0)),
        "in_person_events.bfi",
        True,
    )
    write_metric(
        "DIA",
        str(overall_totals.get("in_person_events", {}).get("dia", 0)),
        "in_person_events.dia",
        True,
    )
    write_metric(
        "SLA",
        str(overall_totals.get("in_person_events", {}).get("sla", 0)),
        "in_person_events.sla",
        True,
    )
    write_metric(
        "Client Connected Projects",
        str(overall_totals.get("in_person_events", {}).get("client_connected", 0)),
        "in_person_events.client_connected",
        True,
    )
    write_metric(
        "Prep 2 Tech",
        str(overall_totals.get("in_person_events", {}).get("p2t", 0)),
        "in_person_events.p2t",
        True,
    )
    write_metric(
        "P2GD",
        str(overall_totals.get("in_person_events", {}).get("p2gd", 0)),
        "in_person_events.p2gd",
        True,
    )

    # Virtual Sessions
    write_section("Virtual Sessions (Pathful)")
    write_metric(
        "Teachers Engaged",
        format_total_unique(
            overall_totals.get("virtual_sessions", {}).get("teachers_engaged", {})
        ),
        "virtual_sessions.teachers_engaged",
    )
    write_metric(
        "Students (est.)",
        str(overall_totals.get("virtual_sessions", {}).get("students_est", 0)),
        "virtual_sessions.students_est",
    )
    write_metric(
        "Number of Sessions",
        str(overall_totals.get("virtual_sessions", {}).get("session_count", 0)),
        "virtual_sessions.session_count",
    )

    # Math Relays
    write_section("Math Relays")
    write_metric(
        "Number of Events",
        str(overall_totals.get("math_relays_count", 0)),
        "math_relays_count",
        False,
        True,
    )

    # Set column widths
    worksheet_summary.set_column(0, 0, 30)
    for i in range(1, len(headers)):
        worksheet_summary.set_column(i, i, 15)

    # ==========================================
    # SHEET 2: MANUAL INPUTS
    # ==========================================
    worksheet_manual = workbook.add_worksheet("Manual Inputs")

    manual_headers = (
        ["Category", "Metric", "Overall"]
        + district_names
        + ["Last Editor", "Last Updated"]
    )
    for col_num, header_text in enumerate(manual_headers):
        fmt = left_header_format if col_num < 2 else header_format
        worksheet_manual.write(0, col_num, header_text, fmt)

    m_row = 1

    # Calculate overall manual inputs if not passed in directly as expected dict form
    overall_manual = {}
    for d, d_inputs in manual_inputs_by_district.items():
        for t_key, val in d_inputs.items():
            overall_manual[t_key] = overall_manual.get(t_key, 0) + val

    categories = []
    for type_key, type_info in manual_data_types.items():
        if type_info["category"] not in categories:
            categories.append(type_info["category"])

    for category in categories:
        for type_key, type_info in manual_data_types.items():
            if type_info["category"] == category:
                worksheet_manual.write(m_row, 0, category, left_cell_format)
                worksheet_manual.write(
                    m_row, 1, type_info["display_name"], left_cell_format
                )
                worksheet_manual.write(
                    m_row, 2, overall_manual.get(type_key, 0), cell_format
                )

                last_editor = "—"
                last_updated = "—"
                latest_update_time = None

                col_offset = 3
                for d_name in district_names:
                    val = manual_inputs_by_district.get(d_name, {}).get(type_key, 0)
                    worksheet_manual.write(m_row, col_offset, val, cell_format)

                    # Track latest editor
                    meta = manual_inputs_meta.get(d_name, {}).get(type_key)
                    if meta and meta["updated_at"]:
                        try:
                            dt = datetime.strptime(meta["updated_at"], "%Y-%m-%d %H:%M")
                            if not latest_update_time or dt > latest_update_time:
                                latest_update_time = dt
                                last_editor = meta["editor"]
                                last_updated = meta["updated_at"]
                        except ValueError:
                            pass

                    col_offset += 1

                worksheet_manual.write(m_row, col_offset, last_editor, cell_format)
                worksheet_manual.write(m_row, col_offset + 1, last_updated, cell_format)
                m_row += 1

    worksheet_manual.set_column(0, 0, 20)
    worksheet_manual.set_column(1, 1, 25)
    worksheet_manual.set_column(2, len(manual_headers) - 3, 12)
    worksheet_manual.set_column(len(manual_headers) - 2, len(manual_headers) - 1, 18)

    writer.close()
    return output.getvalue()
