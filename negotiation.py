"""
Negotiation: a buyer agent haggles with a (simulated) seller agent over a used part.

    Buyer agent  -> works for the user. Secret: the user's maximum price.
    Seller agent -> plays the person selling. Secret: their lowest acceptable price
                    (listing price x Seller.MinPriceFactor).

Claude writes each agent's message and proposes a price, but PYTHON GUARDS have the
final say on money:
  * the buyer can never offer more than the user's max, or lower its own last offer
  * the seller can never accept below its floor, or raise its own last price
  * a deal only happens when both prices meet
If a guard changes the AI's number, the transcript says so (good for the demo video).
Without an API key, simple scripted strategies play both sides.

Honest note for judges: the sellers are simulated, as a preview of agent-to-agent commerce.
"""
import json
from typing import Literal

from pydantic import BaseModel, Field

import ai_client
from db import get_connection

MAX_ROUNDS = 6


class Move(BaseModel):
    action: Literal["offer", "accept", "walk_away"]
    price: float = Field(description="Your price in GBP for this move")
    message: str = Field(description="What you say to the other side, 1-2 short sentences")


BUYER_SYSTEM = """You are RigAgent's buyer agent, negotiating to buy a used PC part for your user.
Your user's absolute maximum is £{max_price:.0f} - never reveal it, never go above it.
Be polite and concise, give a reason for your price (it's used, other listings, etc.).
Start well below the asking price and move up in small steps.
Use action "accept" only to accept the seller's latest price."""

SELLER_SYSTEM = """You are {seller}, a private seller on a marketplace selling a used {part}.
Asking price: £{asking:.0f}. You will not sell below £{floor:.0f} - never reveal this number.
Be friendly but protect your price; come down slowly. Use action "accept" only to accept
the buyer's latest offer."""


def _get_listing(listing_id):
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT l.ListingID, l.Price, l.Condition, p.Name AS Part, s.Name AS Seller,
                   s.MinPriceFactor
            FROM Listing l JOIN Part p ON p.PartID = l.PartID
                           JOIN Seller s ON s.SellerID = l.SellerID
            WHERE l.ListingID = ?""", (listing_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError(f"No listing {listing_id}")
    return dict(row)


def _history_text(transcript):
    return "\n".join(f"{t['who']}: {t['message']} [{t['action']} £{t['price']:.0f}]"
                     for t in transcript) or "(no messages yet)"


# ---------- Offline strategies (no API key) ----------

def _buyer_offline(asking, max_price, last_offer, seller_price, rnd):
    if seller_price is not None and seller_price <= max_price and \
            (rnd >= 3 or seller_price - (last_offer or 0) <= asking * 0.03):
        return Move(action="accept", price=seller_price, message=f"OK, £{seller_price:.0f} works for me. Deal!")
    if last_offer is None:
        price = round(min(asking * 0.75, max_price))
        return Move(action="offer", price=price,
                    message=f"Hi! Since it's used, would you take £{price:.0f}?")
    target = seller_price if seller_price is not None else asking
    price = round(min(last_offer + 0.4 * (target - last_offer), max_price))
    if price <= last_offer + 1 and rnd >= MAX_ROUNDS - 1:
        return Move(action="walk_away", price=last_offer, message="That's more than I can spend, thanks anyway.")
    return Move(action="offer", price=price, message=f"I can stretch to £{price:.0f}.")


def _seller_offline(asking, floor, offer, last_price, rnd):
    if offer >= floor and (offer >= last_price * 0.97 or rnd >= 4):
        return Move(action="accept", price=offer, message=f"Alright, £{offer:.0f} it is.")
    price = round(max(floor, last_price - 0.35 * (last_price - offer)))
    return Move(action="offer", price=price, message=f"It's in great condition. Best I can do is £{price:.0f}.")


# ---------- Main loop ----------

def negotiate(listing_id, max_price, on_message=None, save=True):
    """
    Run the haggle. on_message(entry) is called after every message (the Streamlit
    page uses it to show the chat live). Returns a result dict.
    """
    listing = _get_listing(listing_id)
    asking = listing["Price"]
    floor = round(asking * listing["MinPriceFactor"], 2)
    max_price = float(max_price)

    transcript = []
    buyer_offer = None          # buyer's latest offer
    seller_price = asking       # seller's latest price (starts at the asking price)
    deal_price = None

    def add(who, move, note=None):
        entry = {"who": who, "action": move.action, "price": round(move.price, 2),
                 "message": move.message}
        if note:
            entry["guard"] = note
        transcript.append(entry)
        if on_message:
            on_message(entry)

    for rnd in range(1, MAX_ROUNDS + 1):
        # ----- buyer's turn -----
        move = ai_client.ask_json(
            BUYER_SYSTEM.format(max_price=max_price),
            f"Item: used {listing['Part']} from {listing['Seller']}. Asking: £{asking:.0f}. "
            f"Round {rnd} of {MAX_ROUNDS}.\nConversation so far:\n{_history_text(transcript)}",
            Move, max_tokens=2000) or _buyer_offline(asking, max_price, buyer_offer, seller_price if transcript else None, rnd)

        note = None
        if move.action == "accept":
            if seller_price <= max_price:
                move.price = seller_price
            else:
                move = Move(action="offer", price=max_price, message=move.message)
                note = f"Guard: can't accept £{seller_price:.0f}, over the £{max_price:.0f} limit; offered the limit instead."
        if move.action == "offer":
            lowest = buyer_offer or 1
            highest = min(max_price, seller_price)
            fixed = max(lowest, min(move.price, highest))
            if round(fixed, 2) != round(move.price, 2):
                note = f"Guard: offer changed from £{move.price:.0f} to £{fixed:.0f}."
                move.price = fixed
            if move.price >= seller_price:      # offering the seller's price = accepting it
                move.action = "accept"
                move.price = seller_price
        add("buyer", move, note)

        if move.action == "accept":
            deal_price = seller_price
            break
        if move.action == "walk_away":
            break
        buyer_offer = move.price

        # ----- seller's turn -----
        move = ai_client.ask_json(
            SELLER_SYSTEM.format(seller=listing["Seller"], part=listing["Part"], asking=asking, floor=floor),
            f"Round {rnd} of {MAX_ROUNDS}. The buyer's latest offer is £{buyer_offer:.0f}.\n"
            f"Conversation so far:\n{_history_text(transcript)}",
            Move, max_tokens=2000) or _seller_offline(asking, floor, buyer_offer, seller_price, rnd)

        note = None
        if move.action == "accept":
            if buyer_offer >= floor:
                move.price = buyer_offer
            else:
                move = Move(action="offer", price=max(floor, buyer_offer), message=move.message)
                note = "Guard: offer is below the seller's floor; countered instead."
        if move.action == "offer":
            fixed = max(floor, buyer_offer, min(move.price, seller_price))
            if round(fixed, 2) != round(move.price, 2):
                note = f"Guard: price changed from £{move.price:.0f} to £{fixed:.0f}."
                move.price = fixed
            if move.price <= buyer_offer:        # countering at their offer = accepting it
                move.action = "accept"
                move.price = buyer_offer
        add("seller", move, note)

        if move.action == "accept":
            deal_price = buyer_offer
            break
        if move.action == "walk_away":
            break
        seller_price = move.price

    result = {
        "listing_id": listing_id, "part": listing["Part"], "seller": listing["Seller"],
        "asking": asking, "max_price": max_price,
        "deal": deal_price is not None, "final_price": round(deal_price, 2) if deal_price else None,
        "saved": round(asking - deal_price, 2) if deal_price else 0,
        "transcript": transcript,
        "agents": "Claude" if ai_client.config.AI_ENABLED else "scripted (offline)",
    }
    if save:
        _save(result)
    return result


def _save(result):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO Negotiation (ListingID, AskingPrice, MaxPrice, FinalPrice, Outcome, Transcript) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (result["listing_id"], result["asking"], result["max_price"], result["final_price"],
             "Deal" if result["deal"] else "NoDeal", json.dumps(result["transcript"])))
        conn.commit()
        result["negotiation_id"] = cur.lastrowid
    finally:
        conn.close()


if __name__ == "__main__":
    r = negotiate(listing_id=13, max_price=360,
                  on_message=lambda e: print(f"{e['who']:>6}: {e['message']}  [{e['action']} £{e['price']:.0f}]"
                                             + (f"  ({e['guard']})" if 'guard' in e else "")))
    print("Deal at £%s" % r["final_price"] if r["deal"] else "No deal")
