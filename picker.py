"""
RigAgent part picker - "minimum first, then upgrade"

1. Filter out parts below the user's minimum requirements
2. For each platform (CPU socket), find the CHEAPEST compatible base build
3. Spend leftover budget on upgrades, best performance-per-£ first
4. Return the best final build + a list of upgrades (for the AI to explain later)
"""
from itertools import product
from db import get_connection
from compatibility import check_build

CATEGORIES = ["CPU", "Motherboard", "RAM", "GPU", "PSU", "Case", "Cooler", "Storage"]
TOP_K = 3                          # cheapest options per category tried for the base build
UPGRADE_CATEGORIES = ["GPU", "CPU"]  # parts that affect the performance score
HELPER_CATEGORIES = ["PSU", "Case"]  # may need swapping to make an upgrade fit


# ---------- Loading data ----------

def get_options(allow_used):
    """Every buyable part, cheapest listing only, with the specs the picker needs."""
    conditions = ("New", "Used") if allow_used else ("New",)
    placeholders = ",".join("?" * len(conditions))

    conn = get_connection()
    try:
        rows = conn.execute(f"""
            SELECT p.PartID, p.Name, p.Category,
                   l.ListingID, l.Price, l.Condition, s.Name AS Seller,
                   COALESCE(c.BenchmarkScore, g.BenchmarkScore, 0)     AS Benchmark,
                   c.Socket                                            AS Socket,
                   COALESCE(r.TotalCapacity_GB, st.Capacity_GB, 0)     AS Capacity_GB
            FROM Listing l
            JOIN Part p        ON p.PartID = l.PartID
            JOIN Seller s      ON s.SellerID = l.SellerID
            LEFT JOIN CPU c     ON c.PartID = p.PartID
            LEFT JOIN GPU g     ON g.PartID = p.PartID
            LEFT JOIN RAM r     ON r.PartID = p.PartID
            LEFT JOIN Storage st ON st.PartID = p.PartID
            WHERE l.Condition IN ({placeholders})
            ORDER BY l.Price
        """, conditions).fetchall()
    finally:
        conn.close()

    options = {c: {} for c in CATEGORIES}
    for r in rows:
        # sorted by price, so the first listing seen for a part is its cheapest
        if r["PartID"] not in options[r["Category"]]:
            options[r["Category"]][r["PartID"]] = dict(r)
    # each list stays sorted cheapest first
    return {c: list(parts.values()) for c, parts in options.items()}


def meets_minimum(item, req):
    """Does this part meet the user's minimum requirements?"""
    cat = item["Category"]
    if cat == "CPU":
        return item["Benchmark"] >= req["min_cpu_score"]
    if cat == "GPU":
        return item["Benchmark"] >= req["min_gpu_score"]
    if cat == "RAM":
        return item["Capacity_GB"] >= req["min_ram_gb"]
    if cat == "Storage":
        return item["Capacity_GB"] >= req["min_storage_gb"]
    return True   # no minimum for PSU, case, cooler, motherboard


# ---------- Helpers ----------

def total(parts):
    return sum(item["Price"] for item in parts.values())


def score(parts):
    """Gaming performance: GPU matters most, CPU counts half."""
    return parts["GPU"]["Benchmark"] + 0.5 * parts["CPU"]["Benchmark"]


def is_compatible(parts):
    results = check_build(
        cpu_id=parts["CPU"]["PartID"],
        motherboard_id=parts["Motherboard"]["PartID"],
        ram_id=parts["RAM"]["PartID"],
        gpu_id=parts["GPU"]["PartID"],
        psu_id=parts["PSU"]["PartID"],
        case_id=parts["Case"]["PartID"],
        cooler_id=parts["Cooler"]["PartID"],
    )
    return all(r["passed"] for r in results)


# ---------- Step 2: cheapest base build for one platform ----------

def cheapest_base(options, socket):
    """Cheapest compatible build using CPUs with this socket."""
    pools = {}
    for cat in CATEGORIES:
        items = options[cat]
        if cat == "CPU":
            items = [i for i in items if i["Socket"] == socket]
        pools[cat] = items[:TOP_K]          # only the few cheapest per category
        if not pools[cat]:
            return None

    # every combination of the cheap options, checked cheapest-total first
    combos = sorted(product(*(pools[c] for c in CATEGORIES)),
                    key=lambda combo: sum(i["Price"] for i in combo))
    for combo in combos:
        parts = dict(zip(CATEGORIES, combo))
        if is_compatible(parts):
            return parts                     # first compatible one = cheapest
    return None


# ---------- Step 3: upgrade loop ----------

def try_fix(trial, original, options, extra, leftover):
    """
    An upgrade broke compatibility (e.g. new GPU needs a bigger PSU).
    Try also swapping ONE helper part (PSU or case), cheapest first.
    """
    for helper in HELPER_CATEGORIES:
        for opt in options[helper]:
            if opt["PartID"] == trial[helper]["PartID"]:
                continue
            t2 = dict(trial)
            t2[helper] = opt
            extra2 = extra + opt["Price"] - original[helper]["Price"]
            if extra2 > leftover:
                continue
            if is_compatible(t2):
                return t2, extra2, helper
    return None, None, None


def find_best_swap(parts, options, leftover):
    """Look at every possible upgrade; return the best performance-per-£ one that fits."""
    best = None
    current_score = score(parts)

    for cat in UPGRADE_CATEGORIES:
        for new in options[cat]:
            if new["PartID"] == parts[cat]["PartID"]:
                continue
            trial = dict(parts)
            trial[cat] = new
            gain = score(trial) - current_score
            extra = new["Price"] - parts[cat]["Price"]
            if gain <= 0 or extra > leftover:
                continue

            changed = [cat]
            if not is_compatible(trial):
                trial, extra, helper = try_fix(trial, parts, options, extra, leftover)
                if trial is None:
                    continue
                changed.append(helper)

            value = gain / max(extra, 1)     # performance gained per £
            if best is None or value > best["value"]:
                best = {"parts": trial, "extra": extra, "gain": gain,
                        "value": value, "changed": changed}
    return best


def upgrade(parts, options, budget):
    """Keep making the best-value upgrade until nothing else fits the budget."""
    upgrades = []
    while True:
        swap = find_best_swap(parts, options, budget - total(parts))
        if swap is None:
            break
        for cat in swap["changed"]:
            old, new = parts[cat], swap["parts"][cat]
            upgrades.append(f"{cat}: {old['Name']} → {new['Name']} "
                            f"({'+' if new['Price'] >= old['Price'] else '-'}"
                            f"£{abs(new['Price'] - old['Price']):.0f})")
        parts = swap["parts"]
    return parts, upgrades


# ---------- Main entry point ----------

def pick_build(budget, requirements):
    """
    requirements = {"min_gpu_score", "min_cpu_score", "min_ram_gb",
                    "min_storage_gb", "allow_used"}
    Returns (best_build or None, message)
    """
    options = get_options(requirements["allow_used"])
    options = {c: [i for i in items if meets_minimum(i, requirements)]
               for c, items in options.items()}

    missing = [c for c in CATEGORIES if not options[c]]
    if missing:
        return None, f"No parts meet your requirements for: {', '.join(missing)}"

    sockets = sorted({cpu["Socket"] for cpu in options["CPU"]})
    candidates, cheapest_over_budget = [], None

    for socket in sockets:
        base = cheapest_base(options, socket)
        if base is None:
            continue
        base_total = total(base)
        if base_total > budget:
            if cheapest_over_budget is None or base_total < cheapest_over_budget:
                cheapest_over_budget = base_total
            continue
        final, ups = upgrade(base, options, budget)
        candidates.append({"platform": socket, "parts": final,
                           "total": total(final), "score": score(final),
                           "base_total": base_total, "upgrades": ups})

    if not candidates:
        if cheapest_over_budget:
            return None, (f"Cheapest build meeting your requirements costs "
                          f"£{cheapest_over_budget:.0f} (budget £{budget})")
        return None, "No compatible build found"

    best = max(candidates, key=lambda c: (c["score"], -c["total"]))
    others = ", ".join(f"{c['platform']} £{c['total']:.0f}" for c in candidates if c is not best)
    return best, f"Chose {best['platform']} platform" + (f" (also tried: {others})" if others else "")


def print_build(title, build, message):
    print(f"\n=== {title} ===")
    print(message)
    if build is None:
        return
    for cat, item in build["parts"].items():
        print(f"  {cat:<12} {item['Name']:<26} £{item['Price']:>7.2f}  "
              f"{item['Condition']:<4} from {item['Seller']}")
    print(f"  {'TOTAL':<12} {'':<26} £{build['total']:>7.2f}   "
          f"(base build was £{build['base_total']:.0f})")
    print(f"  Performance score: {build['score']:.0f}")
    if build["upgrades"]:
        print("  Upgrades made:")
        for u in build["upgrades"]:
            print(f"    - {u}")
    else:
        print("  No upgrades - base build used")


if __name__ == "__main__":
    # Later the AI will create this from "I play Valorant and Cyberpunk at 1440p"
    req = {"min_gpu_score": 20000, "min_cpu_score": 15000,
           "min_ram_gb": 16, "min_storage_gb": 500}

    for budget, allow_used in [(1100, True), (3000, False), (1100, False), (700, False)]:
        r = dict(req, allow_used=allow_used)
        label = "new + used" if allow_used else "new only"
        build, msg = pick_build(budget, r)
        print_build(f"£{budget}, {label}", build, msg)