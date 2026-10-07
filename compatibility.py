from db import get_connection


def _get_part(conn, table, part_id):
    """Fetch one part's details (from its type table) plus its name (from Part)."""
    row = conn.execute(
        f"SELECT p.Name, t.* FROM {table} t JOIN Part p ON p.PartID = t.PartID "
        f"WHERE t.PartID = ?",
        (part_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"No {table} found with PartID {part_id}")
    return row


def check_build(cpu_id, motherboard_id, ram_id, gpu_id, psu_id, case_id, cooler_id):
    """
    Run every compatibility rule on a set of parts.
    Returns a list of results: {"rule": ..., "passed": True/False, "detail": ...}
    """
    conn = get_connection()
    try:
        cpu    = _get_part(conn, "CPU", cpu_id)
        mb     = _get_part(conn, "Motherboard", motherboard_id)
        ram    = _get_part(conn, "RAM", ram_id)
        gpu    = _get_part(conn, "GPU", gpu_id)
        psu    = _get_part(conn, "PSU", psu_id)
        case   = _get_part(conn, "PCCase", case_id)
        cooler = _get_part(conn, "Cooler", cooler_id)

        # Many-to-many lists: which sockets the cooler fits, which boards the case fits
        cooler_sockets = {r["Socket"] for r in conn.execute(
            "SELECT Socket FROM CoolerSocket WHERE PartID = ?", (cooler_id,))}
        case_form_factors = {r["FormFactor"] for r in conn.execute(
            "SELECT FormFactor FROM CaseFormFactor WHERE PartID = ?", (case_id,))}
    finally:
        conn.close()

    results = []

    def add(rule, passed, detail):
        results.append({"rule": rule, "passed": passed, "detail": detail})

    # 1. CPU socket matches motherboard socket
    add("CPU socket",
        cpu["Socket"] == mb["Socket"],
        f"{cpu['Name']} ({cpu['Socket']}) vs {mb['Name']} ({mb['Socket']})")

    # 2. RAM type matches motherboard
    add("RAM type",
        ram["RAMType"] == mb["RAMType"],
        f"{ram['Name']} ({ram['RAMType']}) vs {mb['Name']} ({mb['RAMType']})")

    # 3. PSU powerful enough (CPU + GPU, with 20% headroom)
    needed = (cpu["TDP_W"] + gpu["TDP_W"]) * 1.2
    add("PSU wattage",
        needed <= psu["Wattage"],
        f"needs {needed:.0f}W, {psu['Name']} gives {psu['Wattage']}W")

    # 4. PSU size fits the case
    add("PSU size",
        psu["FormFactor"] == case["PSUFormFactor"],
        f"{psu['Name']} ({psu['FormFactor']}) vs {case['Name']} takes {case['PSUFormFactor']}")

    # 5. GPU fits in the case
    add("GPU length",
        gpu["Length_mm"] <= case["MaxGPULength_mm"],
        f"{gpu['Name']} {gpu['Length_mm']}mm vs {case['Name']} max {case['MaxGPULength_mm']}mm")

    # 6. Motherboard size fits the case
    add("Motherboard size",
        mb["FormFactor"] in case_form_factors,
        f"{mb['Name']} ({mb['FormFactor']}) vs {case['Name']} supports {sorted(case_form_factors)}")

    # 7. Cooler supports the CPU socket
    add("Cooler socket",
        cpu["Socket"] in cooler_sockets,
        f"{cooler['Name']} supports {sorted(cooler_sockets)}, CPU needs {cpu['Socket']}")

    # 8. Cooler fits under the case side panel
    add("Cooler height",
        cooler["Height_mm"] <= case["MaxCoolerHeight_mm"],
        f"{cooler['Name']} {cooler['Height_mm']}mm vs {case['Name']} max {case['MaxCoolerHeight_mm']}mm")

    return results


def print_report(title, results):
    """Show results nicely in the terminal."""
    print(f"\n=== {title} ===")
    for r in results:
        mark = "✅" if r["passed"] else "❌"
        print(f"{mark} {r['rule']:<17} {r['detail']}")
    passed = sum(r["passed"] for r in results)
    print(f"--> {passed}/{len(results)} checks passed")


# Runs only when you do: python compatibility.py
if __name__ == "__main__":
    good = check_build(cpu_id=1, motherboard_id=3, ram_id=5, gpu_id=7,
                       psu_id=8, case_id=9, cooler_id=10)
    print_report("GOOD BUILD (should all pass)", good)

    bad = check_build(cpu_id=2, motherboard_id=3, ram_id=6, gpu_id=12,
                      psu_id=13, case_id=14, cooler_id=10)
    print_report("BAD BUILD (should mostly fail)", bad)