"""
Buy now / Fair / Wait rating for each part.

Plain maths decides the rating, using REAL price history when we have it
(Channel3's 90-day history is fetched live during each build; see live_prices.py):
  1. Trend: fit a straight line through the last 30 days of prices (least squares).
     Falling fast -> probably cheaper soon -> Wait.
  2. Position: is today's price near the 90-day low or high?
  3. Channel3's own "low / typical / high" verdict on today's price, if live.
  4. Season: Black Friday / Cyber Monday (late November) usually brings deals.
Claude then (optionally) writes one short summary of all ratings in plain English.
"""
from datetime import date, timedelta

import ai_client
from db import get_connection


MIN_POINTS = 7          # fewer days than this can't show a trend


def get_history(part_id, condition="New", days=90):
    """
    Price history for one part, real history first:
      * "real": Channel3's live history (fetched during this build) or eBay prices we've seen
      * "test": made-up history from the seed data, only if there isn't enough real history
    Returns (rows, source). Never mixes the two, because a real £529 next to a test
    £549 the day before would look like a price drop that never happened.
    """
    since = (date.today() - timedelta(days=days)).isoformat()
    conn = get_connection()
    try:
        for source_filter, label in (("Source != 'test'", "real"), ("Source = 'test'", "test")):
            rows = conn.execute(
                "SELECT Date, MIN(Price) AS Price FROM PriceHistory "
                f"WHERE PartID = ? AND Condition = ? AND Date >= ? AND {source_filter} "
                "GROUP BY Date ORDER BY Date", (part_id, condition, since)).fetchall()
            if len(rows) >= MIN_POINTS:
                return [dict(r) for r in rows], label
    finally:
        conn.close()
    return [dict(r) for r in rows], label


def slope_per_day(prices):
    """Least-squares line through the prices: how many £ per day it's moving."""
    n = len(prices)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2
    mean_y = sum(prices) / n
    top = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(prices))
    bottom = sum((x - mean_x) ** 2 for x in range(n))
    return top / bottom


def days_to_black_friday(today=None):
    """Black Friday = the day after the 4th Thursday of November."""
    today = today or date.today()
    for year in (today.year, today.year + 1):
        nov1 = date(year, 11, 1)
        first_thu = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
        bf = first_thu + timedelta(weeks=3, days=1)
        if bf + timedelta(days=4) >= today:          # still inside the BF weekend
            return (bf - today).days
    return 365


def rate_part(part_id, current_price, condition="New", today=None, price_status=None):
    """
    Returns {"rating", "confidence", "reason", "history", "history_source"}.
    price_status = Channel3's own verdict on today's price ("low"/"typical"/"high"), if we have it.
    """
    history, history_source = get_history(part_id, condition)
    prices = [h["Price"] for h in history]
    if len(prices) < MIN_POINTS:
        return {"rating": "Fair", "confidence": 0.3, "history": history,
                "history_source": history_source,
                "reason": "Not enough price history yet to spot a trend."}

    recent = prices[-30:]
    trend_pct_30d = slope_per_day(recent) * 30 / current_price * 100   # % change per month
    low, high = min(prices), max(prices)
    position = (current_price - low) / (high - low) if high > low else 0.5  # 0 = at the low
    bf_days = days_to_black_friday(today)

    score = 0.0                      # positive = buy now, negative = wait
    reasons = []
    if trend_pct_30d <= -3:
        score -= 1.5
        reasons.append(f"price is falling (~{abs(trend_pct_30d):.0f}% a month)")
    elif trend_pct_30d >= 3:
        score += 1.0
        reasons.append(f"price is rising (~{trend_pct_30d:.0f}% a month)")
    else:
        reasons.append("price is stable")

    if position <= 0.2:
        score += 1.0
        reasons.append(f"it's near its 90-day low (£{low:.0f})")
    elif position >= 0.8:
        score -= 1.0
        reasons.append(f"it's near its 90-day high (£{high:.0f})")

    if price_status == "low":
        score += 0.5
        reasons.append("Channel3 rates today's price as low for this part")
    elif price_status == "high":
        score -= 0.5
        reasons.append("Channel3 rates today's price as high for this part")

    if 0 <= bf_days <= 30 and condition == "New":
        score -= 0.5
        reasons.append(f"Black Friday is in {bf_days} days" if bf_days else "it's Black Friday")

    if score >= 1:
        rating = "Buy now"
    elif score <= -1:
        rating = "Wait"
    else:
        rating = "Fair"
    confidence = round(min(0.95, 0.5 + 0.15 * abs(score)), 2)
    reason = reasons[0][0].upper() + reasons[0][1:]
    if len(reasons) > 1:
        reason += ", " + ", ".join(reasons[1:])
    return {"rating": rating, "confidence": confidence, "history": history,
            "history_source": history_source, "reason": reason + ".", "trend_pct_30d": round(trend_pct_30d, 1),
            "low_90d": low, "high_90d": high}


def rate_build(parts):
    """Rate every part in a build. parts = picker build["parts"]."""
    return {cat: rate_part(p["PartID"], p["Price"], p["Condition"], price_status=p.get("PriceStatus"))
            for cat, p in parts.items()}


def summarise(parts, ratings):
    """One short paragraph of advice (Claude if available, else a simple sentence)."""
    lines = [f"- {cat}: {parts[cat]['Name']} £{parts[cat]['Price']:.0f} -> {r['rating']} ({r['reason']})"
             for cat, r in ratings.items()]
    waits = [cat for cat, r in ratings.items() if r["rating"] == "Wait"]
    text = ai_client.ask_text(
        "You are RigAgent. In 2-3 sentences, advise a first-time PC builder whether to buy "
        "everything now or wait for some parts, using only these ratings. Mention the "
        "price-watch feature if any part says Wait. Use £.",
        "\n".join(lines), max_tokens=1500)
    if text:
        return text
    if not waits:
        return "Nothing here is likely to get much cheaper soon, so it's a good time to buy."
    return (f"Consider waiting on: {', '.join(waits)}. You can buy the rest now and set a "
            "price watch so RigAgent prepares the order when the price drops.")
