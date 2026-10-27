import json, os, sys, re, copy
sys.path.append(os.path.abspath(".."))
from simulator.game_ui import run_replay_viewer

REPLAYS = os.listdir("EdisonExamples")

persistent_example = {
  "turn": 1,

  "me_life": 8000,
  "me_cards_in_deck": 40,
  "me_cards_in_extra_deck": 15,

  "me_hand": [],
  "me_GY": [],
  "me_banished": [],
  "me_banish": [],
  "me_field_spell": None,

  "me_field": {
    "M-1": None,
    "M-2": None,
    "M-3": None,
    "M-4": None,
    "M-5": None,

    "S-1": None,
    "S-2": None,
    "S-3": None,
    "S-4": None,
    "S-5": None,
  },

  "me_phase": None,

  "op_life": 8000,
  "op_cards_in_deck": 40,
  "op_cards_in_extra_deck": 15,

  "op_hand": [],
  "op_GY": [],
  "op_banished": [],
  "op_banish": [],

  "op_field_spell": None,

  "op_field": {
    "M-1": None,
    "M-2": None,
    "M-3": None,
    "M-4": None,
    "M-5": None,

    "S-1": None,
    "S-2": None,
    "S-3": None,
    "S-4": None,
    "S-5": None,
  },

  "op_phase": None
}

default_card = {
  "name": None,
  "object_id": None,
  "battle_position": None,
  "face_up": None,
  "owner": None
}


example_card = {
  "name": "Unknown Card",
  "object_id": 0,
  "battle_position": None,
  "face_up": True,
  "owner": "p1"
}

def get_log_text(play: dict) -> str:
    log = play.get("log") or {}
    if not isinstance(log, dict):
        return ""
    return (log.get("private_log") or log.get("public_log") or "").strip()

for replay in REPLAYS:
    game_log = json.load(open(f"EdisonExamples/{replay}", "r", encoding="utf-8"))



    persistent_state = {
    "turn": 1,

    "me_life": 8000,
    "me_cards_in_deck": 40,
    "me_cards_in_extra_deck": 15,

    "me_hand": [],
    "me_GY": [],
    "me_banished": [],
    "me_banish": [],
    "me_field_spell": None,

    "me_field": {
        "M-1": None,
        "M-2": None,
        "M-3": None,
        "M-4": None,
        "M-5": None,

        "S-1": None,
        "S-2": None,
        "S-3": None,
        "S-4": None,
        "S-5": None,
    },

    "me_phase": None,

    "op_life": 8000,
    "op_cards_in_deck": 40,
    "op_cards_in_extra_deck": 15,

    "op_hand": [],
    "op_GY": [],
    "op_banished": [],
    "op_banish": [],

    "op_field_spell": None,

    "op_field": {
        "M-1": None,
        "M-2": None,
        "M-3": None,
        "M-4": None,
        "M-5": None,

        "S-1": None,
        "S-2": None,
        "S-3": None,
        "S-4": None,
        "S-5": None,
    },

    "op_phase": None
    }

    player_1 = game_log["player1"]["username"]
    p1_main_total = game_log["player1"]["main_total"]
    p1_extra_total = game_log["player1"]["extra_total"]
    player_2 = game_log["player2"]["username"]
    p2_main_total = game_log["player2"]["main_total"]
    p2_extra_total = game_log["player2"]["extra_total"]

    persistent_state["me_cards_in_deck"] = p1_main_total
    persistent_state["me_cards_in_extra_deck"] = p1_extra_total
    persistent_state["op_cards_in_deck"] = p2_main_total
    persistent_state["op_cards_in_extra_deck"] = p2_extra_total


    STATE_ACTION_PAIRS = []

    for play in game_log["plays"]:
        play_type = play["play"]

        # Skipping
        if play_type in ["Good", "Shuffle hand", "RPS", "Attack directly", "View deck", "Stop viewing", "Shuffle deck", "Declare", "View GY", "View GY 2", "Duel message", "Attack", "Edit stats", "Thinking", "View ED", "Target card", "View Banished 2", "Reveal", "Done siding", "Add counter", "Remove counter", "View Banished", "Siding"]:
            print(f"⏭️ Skipping play: {play_type} - {play.get("username")}")
        
        # Real actions
        elif play_type == "Begin next duel":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            # Hard reset persistent state to initial conditions
            persistent_state = copy.deepcopy(persistent_example)

        elif play_type == "Admit defeat":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            # For now, just print and break; in a full implementation, you might want to record the final state or handle post-game logic
            print(f"Player {play['username']} admitted defeat. Ending replay.")
            id = game_log.get("id", "unknown_id")
            print(f"Url: https://www.duelingbook.com/replay?id={id}")
            break
            
        elif play_type == "Pick first":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            cards = play["cards"]
            card_names = [
                {"name": card["name"], "object_id": card["object_id"], "battle_position": None, "face_up": None} for card in cards]
            # add owner p1 to the first 5 cards, owner p2 to the next 5 cards
            card_names[:5] = [{**card, "owner": "p1"} for card in card_names[:5]]
            card_names[5:10] = [{**card, "owner": "p2"} for card in card_names[5:10]]
            persistent_state["me_hand"] = card_names[:5]
            persistent_state["op_hand"] = card_names[5:10]
            persistent_state["me_cards_in_deck"] -= 5
            persistent_state["op_cards_in_deck"] -= 5
        
        elif play_type == "Draw card":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            card = play["card"]
            drawn_card = {"name": card["name"], "object_id": card["object_id"], "battle_position": None, "face_up": None}
            if play["username"] == player_1:
                drawn_card["owner"] = "p1"
                persistent_state["me_hand"].append(drawn_card)
                persistent_state["me_cards_in_deck"] -= 1
            else:
                drawn_card["owner"] = "p2"
                persistent_state["op_hand"].append(drawn_card)
                persistent_state["op_cards_in_deck"] -= 1
        
        elif play_type == "Enter DP":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            if play["username"] == player_1:
                persistent_state["me_phase"] = "DP"
            else:
                persistent_state["op_phase"] = "DP"
        
        elif play_type == "Enter SP":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            if play["username"] == player_1:
                persistent_state["me_phase"] = "SP"
            else:
                persistent_state["op_phase"] = "SP"
        
        elif play_type == "Enter M1":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            if play["username"] == player_1:
                persistent_state["me_phase"] = "M1"
            else:
                persistent_state["op_phase"] = "M1"
        
        elif play_type == "Enter BP":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            if play["username"] == player_1:
                persistent_state["me_phase"] = "BP"
            else:
                persistent_state["op_phase"] = "BP"
        
        elif play_type == "Enter M2":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            if play["username"] == player_1:
                persistent_state["me_phase"] = "M2"
            else:
                persistent_state["op_phase"] = "M2"
        
        elif play_type == "Enter EP":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            if play["username"] == player_1:
                persistent_state["me_phase"] = "EP"
            else:
                persistent_state["op_phase"] = "EP"
        
        elif play_type == "End turn":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            if play["username"] == player_1:
                persistent_state["me_phase"] = "Opponent's turn"
                persistent_state["op_phase"] = "DP"
            else:
                persistent_state["op_phase"] = "Opponent's turn"
                persistent_state["me_phase"] = "DP"
            persistent_state["turn"] += 1
        
        elif play_type == "Start turn":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            if play["username"] == player_1:
                persistent_state["me_phase"] = "DP"
                persistent_state["op_phase"] = "Opponent's turn"
            else:
                persistent_state["op_phase"] = "DP"
                persistent_state["me_phase"] = "Opponent's turn"

        elif play_type == "Life points":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            if play["username"] == player_1:
                persistent_state["me_life"] +=play["amount"]
            else:
                persistent_state["op_life"] += play["amount"]

        elif play_type == "Set ST":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            log = get_log_text(play)
            pattern = r'Set "(.*?)" from (\w+) .* to (\S+)'
            match = re.search(pattern, log)

            if match:
                card_name = match.group(1)
                start = match.group(2)
                finish = match.group(3)

            card_object = None
            if start == "hand":
                if play["username"] == player_1:
                    # find the card in hand and remove it
                    for card in persistent_state["me_hand"]:
                        if card["name"] == card_name:
                            card_object = card
                            persistent_state["me_hand"].remove(card)
                            break
                    # place it on the field
                    persistent_state["me_field"][finish] = {"name": card_name, "object_id": card_object["object_id"] if card_object else None, "battle_position": None, "face_up": False, "owner": card_object["owner"] if card_object else None}
                else:
                    # find the card in hand and remove it
                    for card in persistent_state["op_hand"]:
                        if card["name"] == card_name:
                            card_object = card
                            persistent_state["op_hand"].remove(card)
                            break
                    # place it on the field
                    persistent_state["op_field"][finish] = {"name": card_name, "object_id": card_object["object_id"] if card_object else None, "battle_position": None, "face_up": False, "owner": card_object["owner"] if card_object else None}
        
        elif play_type == "Activate ST":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            log = get_log_text(play)

            pattern = r'^Activated(?: Set)?\s+"([^"]+)"(?:\s+from\s+(\w+)(?:\s+\(\d+/\d+\))?\s+to\s+(S-\d+)|\s+in\s+(S-\d+))\s*$'
            m = re.search(pattern, log)

            if not m:
                print(f"⚠️ Could not parse Activate ST log: {log!r}")
                continue

            card_name = m.group(1)
            start = (m.group(2) or "").lower() or None
            finish = m.group(3) or m.group(4)  # S-#

            is_me = play["username"] == player_1
            field = persistent_state["me_field"] if is_me else persistent_state["op_field"]
            hand  = persistent_state["me_hand"]  if is_me else persistent_state["op_hand"]
            default_owner = "p1" if is_me else "p2"

            # Case 1: Activated Set "X" in S-#
            if start is None:
                existing = field.get(finish)
                if isinstance(existing, dict):
                    existing["face_up"] = True
                    existing.setdefault("owner", default_owner)
                    field[finish] = existing
                else:
                    # fallback: if zone empty, create something so you don't crash later
                    field[finish] = {
                        "name": card_name,
                        "object_id": play.get("card", {}).get("object_id"),
                        "battle_position": None,
                        "face_up": True,
                        "owner": default_owner,
                    }

            # Case 2: Activated "X" from hand (...) to S-#
            elif start == "hand":
                card_object = None

                # prefer object_id match if you have it
                target_oid = play.get("card", {}).get("object_id")
                if target_oid is not None:
                    for i, c in enumerate(hand):
                        if c.get("object_id") == target_oid:
                            card_object = hand.pop(i)
                            break

                if card_object is None:
                    for i, c in enumerate(hand):
                        if c.get("name") == card_name:
                            card_object = hand.pop(i)
                            break

                if card_object is None:
                    card_object = {
                        "name": card_name,
                        "object_id": target_oid,
                        "battle_position": None,
                        "face_up": True,
                        "owner": default_owner,
                    }

                card_object["face_up"] = True
                card_object["battle_position"] = None
                card_object.setdefault("owner", default_owner)
                field[finish] = card_object

            else:
                print(f"⚠️ Activate ST start zone not handled: start={start!r}, log={log!r}")
                        
        elif play_type == "Set Field Spell":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            log = get_log_text(play)


            # Handles BOTH:
            # Set Field Spell "A Legendary Ocean" from hand (7/7)
            # Set Field Spell "A Legendary Ocean" in Field Spell Zone
            pattern = r'^Set Field Spell\s+"([^"]+)"(?:\s+from\s+([A-Za-z]+)\s+\(\d+/\d+\)|\s+in Field Spell Zone)\s*$'
            match = re.search(pattern, log)

            if not match:
                print(f"⚠️ Could not parse Set Field Spell log: {log!r}")
            else:
                card_name = match.group(1)
                start = match.group(2).lower() if match.group(2) else None
                finish = "FZ"  # your field-spell zone key; change if you use something else

                card_object = None

                if play["username"] == player_1:
                    if start == "hand":
                        for card in persistent_state["me_hand"]:
                            if card["name"] == card_name:
                                card_object = card
                                persistent_state["me_hand"].remove(card)
                                break

                    # place into my field spell zone (set = face_down)
                    persistent_state["me_field_spell"] = {
                        "name": card_name,
                        "object_id": card_object["object_id"] if card_object else persistent_state.get("me_field_spell", {}).get("object_id"),
                        "battle_position": None,
                        "face_up": False,
                        "owner": card_object["owner"] if card_object else None
                    }

                else:
                    if start == "hand":
                        for card in persistent_state["op_hand"]:
                            if card["name"] == card_name:
                                card_object = card
                                persistent_state["op_hand"].remove(card)
                                break

                    # place into opponent field spell zone (set = face_down)
                    persistent_state["op_field_spell"] = {
                        "name": card_name,
                        "object_id": card_object["object_id"] if card_object else persistent_state.get("op_field_spell", {}).get("object_id"),
                        "battle_position": None,
                        "face_up": False,
                        "owner": card_object["owner"] if card_object else None
                    }
        
        elif play_type == "Activate Field Spell":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            log = get_log_text(play)

            # Handles ALL formats:
            # Activated Field Spell "X" from Deck
            # Activated Field Spell "X" from hand (3/3)
            # Activated Field Spell Set "X" in Field Spell Zone
            pattern = r'^Activated Field Spell(?: Set)?\s+"([^"]+)"(?:\s+from\s+([A-Za-z]+)(?:\s+\(\d+/\d+\))?|\s+in Field Spell Zone)\s*$'
            match = re.search(pattern, log)

            if not match:
                print(f"⚠️ Could not parse Activate Field Spell log: {log!r}")
            else:
                card_name = match.group(1)
                start = match.group(2).lower() if match.group(2) else None

                card_object = None

                if play["username"] == player_1:

                    if start == "hand":
                        for card in persistent_state["me_hand"]:
                            if card["name"] == card_name:
                                card_object = card
                                persistent_state["me_hand"].remove(card)
                                break

                    elif start == "deck":
                        persistent_state["me_cards_in_deck"] -= 1

                    persistent_state["me_field_spell"] = {
                        "name": card_name,
                        "object_id": card_object["object_id"] if card_object else None,
                        "battle_position": None,
                        "face_up": True,
                        "owner": "p1"
                    }

                else:

                    if start == "hand":
                        for card in persistent_state["op_hand"]:
                            if card["name"] == card_name:
                                card_object = card
                                persistent_state["op_hand"].remove(card)
                                break

                    elif start == "deck":
                        persistent_state["op_cards_in_deck"] -= 1

                    persistent_state["op_field_spell"] = {
                        "name": card_name,
                        "object_id": card_object["object_id"] if card_object else None,
                        "battle_position": None,
                        "face_up": True,
                        "owner": "p2"
                    }

        elif play_type == "Normal Summon":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            log = get_log_text(play)

            pattern = r'Normal Summoned\s+"(.*?)"\s+from\s+(\w+)\s+\(\d+/\d+\)\s+to\s+(\S+)'
            match = re.search(pattern, log)

            if not match:
                print(f"⚠️ Could not parse Normal Summon log: {log!r}")
            else:
                card_name = match.group(1)
                start = match.group(2)
                finish = match.group(3)

                card_object = None
                if start == "hand":
                    if play["username"] == player_1:
                        for card in persistent_state["me_hand"]:
                            if card["name"] == card_name:
                                card_object = card
                                persistent_state["me_hand"].remove(card)
                                break
                        persistent_state["me_field"][finish] = {
                            "name": card_name,
                            "object_id": card_object["object_id"] if card_object else None,
                            "battle_position": "ATK",
                            "face_up": True,
                            "owner": card_object["owner"] if card_object else None
                        }
                    else:
                        for card in persistent_state["op_hand"]:
                            if card["name"] == card_name:
                                card_object = card
                                persistent_state["op_hand"].remove(card)
                                break
                        persistent_state["op_field"][finish] = {
                            "name": card_name,
                            "object_id": card_object["object_id"] if card_object else None,
                            "battle_position": "ATK",
                            "face_up": True,
                            "owner": card_object["owner"] if card_object else None
                        }

        elif play_type == "Set monster":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")

            log = get_log_text(play)

            mover_is_me = (play.get("username") == player_1)
            mover_hand  = persistent_state["me_hand"] if mover_is_me else persistent_state["op_hand"]
            mover_field = persistent_state["me_field"] if mover_is_me else persistent_state["op_field"]

            # Patterns it covers:
            # private: Set "Card Trooper" from hand (3/5) to M-3
            # public : Set card from hand (3/5) to M-3
            # private: Set "Giga Gagagigo" in M-3
            # public : Set "Giga Gagagigo" in M-3
            p_from_hand_named = r'^Set\s+"([^"]+)"\s+from\s+hand(?:\s+\(\d+/\d+\))?\s+to\s+(M-\d+|S-\d+)$'
            p_from_hand_anon  = r'^Set\s+card\s+from\s+hand(?:\s+\(\d+/\d+\))?\s+to\s+(M-\d+|S-\d+)$'
            p_in_zone_named   = r'^Set\s+"([^"]+)"\s+in\s+(M-\d+|S-\d+)$'

            m1 = re.search(p_from_hand_named, log)
            m2 = re.search(p_from_hand_anon, log)
            m3 = re.search(p_in_zone_named, log)

            # ---- CASE A: Set from hand (named) ----
            if m1:
                card_name = m1.group(1)
                dest_zone = m1.group(2)

                card_object = None
                for i, c in enumerate(mover_hand):
                    if c.get("name") == card_name:
                        card_object = mover_hand.pop(i)
                        break

                if card_object is None:
                    print(f'❌ SET ERROR: could not find "{card_name}" in mover hand')
                else:
                    # place facedown defense
                    card_object["battle_position"] = "DEF"
                    card_object["face_up"] = False
                    card_object.setdefault("owner", "p1" if mover_is_me else "p2")

                    mover_field[dest_zone] = card_object

            # ---- CASE B: Set from hand (anonymous public log) ----
            elif m2:
                dest_zone = m2.group(1)

                # If public log hides the card name, rely on play["card"] if present.
                card_name = play.get("card", {}).get("name")
                if not card_name:
                    print(f"❌ SET ERROR: public log hides card name and play['card'] missing; can't resolve")
                else:
                    card_object = None
                    for i, c in enumerate(mover_hand):
                        if c.get("name") == card_name:
                            card_object = mover_hand.pop(i)
                            break

                    if card_object is None:
                        print(f'❌ SET ERROR: could not find "{card_name}" in mover hand (public log case)')
                    else:
                        card_object["battle_position"] = "DEF"
                        card_object["face_up"] = False
                        card_object.setdefault("owner", "p1" if mover_is_me else "p2")

                        mover_field[dest_zone] = card_object

            # ---- CASE C: Set in-zone (already on field) ----
            elif m3:
                card_name = m3.group(1)
                zone      = m3.group(2)

                card_object = mover_field.get(zone)

                if card_object is None:
                    print(f'❌ SET ERROR: zone {zone} is empty; cannot set "{card_name}"')
                elif not isinstance(card_object, dict):
                    print(f'❌ SET ERROR: zone {zone} not a card dict: {card_object!r}')
                elif card_object.get("name") != card_name:
                    print(f'❌ SET ERROR: name mismatch at {zone}: found "{card_object.get("name")}", expected "{card_name}"')
                else:
                    card_object["battle_position"] = "DEF"
                    card_object["face_up"] = False
                    print(f'✔ Set in place: "{card_name}" in {zone} -> (FD DEF)')

            else:
                print(f"❌ Could not parse Set monster log: {log!r}")

        elif play_type == "Flip":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")

            log = (play.get("log", {}).get("private_log")
                or play.get("log", {}).get("public_log")
                or "").strip()

            # Examples:
            # Flipped Set "Ryko, Lightsworn Hunter" in M-3
            # (sometimes public could be: Flipped Set card in M-3)
            m_named = re.search(r'^Flipped\s+Set\s+"([^"]+)"\s+in\s+(M-\d+)$', log)
            m_anon  = re.search(r'^Flipped\s+Set\s+card\s+in\s+(M-\d+)$', log)

            if m_named:
                card_name = m_named.group(1)
                zone = m_named.group(2)
            elif m_anon:
                card_name = play.get("card", {}).get("name")  # may still exist in payload
                zone = m_anon.group(1)
            else:
                print(f"⚠️ Could not parse Flip log: {log!r}")
                continue

            target_oid = play.get("card", {}).get("object_id")

            flipper_is_me = (play.get("username") == player_1)
            field = persistent_state["me_field"] if flipper_is_me else persistent_state["op_field"]
            other_field = persistent_state["op_field"] if flipper_is_me else persistent_state["me_field"]

            card_obj = field.get(zone)

            # If not found on the flipper's field (rare desync), try the other side
            if not isinstance(card_obj, dict):
                card_obj = other_field.get(zone)
                if isinstance(card_obj, dict):
                    field = other_field  # switch reference so updates apply to correct dict

            if not isinstance(card_obj, dict):
                print(f'❌ FLIP ERROR: {zone} is empty/invalid; found={field.get(zone)!r}')
                continue

            # If we have an object_id, enforce it; otherwise enforce name when available
            if target_oid is not None and card_obj.get("object_id") is not None and card_obj.get("object_id") != target_oid:
                print(f'❌ FLIP ERROR: object_id mismatch at {zone}: found={card_obj.get("object_id")}, expected={target_oid}')
                continue
            if card_name and card_obj.get("name") and card_obj.get("name") != card_name:
                print(f'❌ FLIP ERROR: name mismatch at {zone}: found="{card_obj.get("name")}", expected="{card_name}"')
                continue

            # Flip Set: face-down DEF -> face-up DEF (keep DEF)
            card_obj["face_up"] = True
            card_obj["battle_position"] = "DEF"  # key rule: flips from DEF to DEF
            card_obj.setdefault("owner", "p1" if flipper_is_me else "p2")

            field[zone] = card_obj

        elif play_type == "Flip Summon":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")

            log = (play.get("log", {}).get("private_log")
                or play.get("log", {}).get("public_log")
                or "").strip()

            # Examples:
            # Flip Summoned Set "Super-Nimble Mega Hamster" in M-3
            # (possible public hidden form: Flip Summoned Set card in M-3)
            m_named = re.search(r'^Flip\s+Summoned\s+Set\s+"([^"]+)"\s+in\s+(M-\d+)$', log)
            m_anon  = re.search(r'^Flip\s+Summoned\s+Set\s+card\s+in\s+(M-\d+)$', log)

            if m_named:
                card_name = m_named.group(1)
                zone = m_named.group(2)
            elif m_anon:
                card_name = play.get("card", {}).get("name")  # may still exist in payload
                zone = m_anon.group(1)
            else:
                print(f"⚠️ Could not parse Flip Summon log: {log!r}")
                continue

            target_oid = play.get("card", {}).get("object_id")

            summoner_is_me = (play.get("username") == player_1)
            field = persistent_state["me_field"] if summoner_is_me else persistent_state["op_field"]
            other_field = persistent_state["op_field"] if summoner_is_me else persistent_state["me_field"]

            card_obj = field.get(zone)

            # If not found on the summoner's field (rare desync), try the other side
            if not isinstance(card_obj, dict):
                card_obj = other_field.get(zone)
                if isinstance(card_obj, dict):
                    field = other_field  # apply updates to correct side

            if not isinstance(card_obj, dict):
                print(f'❌ FLIP SUMMON ERROR: {zone} is empty/invalid; found={field.get(zone)!r}')
                continue

            # If we have an object_id, enforce it; otherwise enforce name when available
            if target_oid is not None and card_obj.get("object_id") is not None and card_obj.get("object_id") != target_oid:
                print(f'❌ FLIP SUMMON ERROR: object_id mismatch at {zone}: found={card_obj.get("object_id")}, expected={target_oid}')
                continue
            if card_name and card_obj.get("name") and card_obj.get("name") != card_name:
                print(f'❌ FLIP SUMMON ERROR: name mismatch at {zone}: found="{card_obj.get("name")}", expected="{card_name}"')
                continue

            # Flip Summon: face-down DEF -> face-up ATK
            card_obj["face_up"] = True
            card_obj["battle_position"] = "ATK"
            card_obj.setdefault("owner", "p1" if summoner_is_me else "p2")

            field[zone] = card_obj

        elif play_type == "To GY":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")

            log = get_log_text(play)

            # Matches ALL formats:
            # Sent "Machina Fortress" from hand (1/4) to GY
            # Sent "Moray of Greed" from S-4 to GY
            # Sent Set "Brain Control" from S-3 to GY
            # Sent "A Legendary Ocean" from Field Spell Zone to GY
            # Sent "Terraforming" from Deck to GY
            # Sent "Elemental HERO Absolute Zero" from Extra Deck to GY
            pattern = r'^Sent(?: Set)?\s+"([^"]+)"\s+from\s+(.+?)\s+to\s+GY$'
            match = re.search(pattern, log)

            if not match:
                print(f"⚠️ Could not parse To GY log: {log!r}")
                continue

            card_name = match.group(1)
            source_raw = match.group(2).strip()

            # -------- normalize source --------
            if source_raw.startswith("hand"):
                source = "hand"
            elif source_raw.startswith("Deck"):
                source = "Deck"
            elif source_raw.startswith("Extra Deck"):
                source = "Extra Deck"
            elif source_raw.startswith("Field Spell Zone"):
                source = "Field Spell Zone"
            elif source_raw.startswith("GY"):
                source = "GY"
            else:
                source = source_raw  # S-3, M-2, etc.

            is_me = play["username"] == player_1

            # -------- select correct zones --------
            if is_me:
                hand = persistent_state["me_hand"]
                field = persistent_state["me_field"]
                gy = persistent_state["me_GY"]
                field_spell = persistent_state.get("me_field_spell")
                owner_tag = "p1"
            else:
                hand = persistent_state["op_hand"]
                field = persistent_state["op_field"]
                gy = persistent_state["op_GY"]
                field_spell = persistent_state.get("op_field_spell")
                owner_tag = "p2"

            target_oid = play.get("card", {}).get("object_id")
            card_object = None

            def pop_from_list_by_oid_or_name(lst, oid, name):
                if oid is not None:
                    for i, c in enumerate(lst):
                        if isinstance(c, dict) and c.get("object_id") == oid:
                            return lst.pop(i)
                for i, c in enumerate(lst):
                    if isinstance(c, dict) and c.get("name") == name:
                        return lst.pop(i)
                return None

            # -------- remove from hand --------
            if source == "hand":
                card_object = pop_from_list_by_oid_or_name(hand, target_oid, card_name)

            # -------- remove from field (M-#/S-#) --------
            elif source in field:
                card_object = field.pop(source)

            # -------- remove from field spell zone --------
            elif source == "Field Spell Zone":
                card_object = field_spell
                if is_me:
                    persistent_state["me_field_spell"] = None
                else:
                    persistent_state["op_field_spell"] = None

            # -------- sent from deck --------
            elif source == "Deck":
                card_object = {
                    "name": card_name,
                    "object_id": target_oid,
                    "battle_position": None,
                    "face_up": True,
                    "owner": owner_tag
                }
                if is_me:
                    persistent_state["me_cards_in_deck"] = max(0, persistent_state["me_cards_in_deck"] - 1)
                else:
                    persistent_state["op_cards_in_deck"] = max(0, persistent_state["op_cards_in_deck"] - 1)

            # -------- sent from extra deck (FIX) --------
            elif source == "Extra Deck":
                card_object = {
                    "name": card_name,
                    "object_id": target_oid,
                    "battle_position": None,
                    "face_up": True,
                    "owner": owner_tag
                }
                if is_me:
                    persistent_state["me_cards_in_extra_deck"] = max(0, persistent_state["me_cards_in_extra_deck"] - 1)
                else:
                    persistent_state["op_cards_in_extra_deck"] = max(0, persistent_state["op_cards_in_extra_deck"] - 1)

            # -------- already in GY safety --------
            elif source == "GY":
                # don't duplicate if it's already there; but if you want to always append, remove this branch
                for c in gy:
                    if isinstance(c, dict) and ((target_oid is not None and c.get("object_id") == target_oid) or c.get("name") == card_name):
                        card_object = c
                        break

            # -------- fallback (never fail) --------
            if card_object is None:
                card_object = {
                    "name": card_name,
                    "object_id": target_oid,
                    "battle_position": None,
                    "face_up": True,
                    "owner": owner_tag
                }

            # -------- add to graveyard (by owner) --------
            target_gy = persistent_state["me_GY"] if card_object.get("owner") == "p1" else persistent_state["op_GY"]
            target_gy.append(card_object)

        elif play_type == "Mill":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")

            log = get_log_text(play)

            # Example: Milled "Legacy of Yata-Garasu" from top of deck
            m = re.search(r'^Milled\s+"([^"]+)"\s+from\s+top\s+of\s+deck$', log)

            if not m:
                print(f"⚠️ Could not parse Mill log: {log!r}")
            else:
                card_name = m.group(1)
                target_oid = play.get("card", {}).get("object_id")
                is_me = (play.get("username") == player_1)

                owner_tag = "p1" if is_me else "p2"

                # Decrement deck count
                if is_me:
                    persistent_state["me_cards_in_deck"] = max(0, persistent_state["me_cards_in_deck"] - 1)
                    target_gy = persistent_state["me_GY"]
                else:
                    persistent_state["op_cards_in_deck"] = max(0, persistent_state["op_cards_in_deck"] - 1)
                    target_gy = persistent_state["op_GY"]

                # Create card instance in GY
                card_object = {
                    "name": card_name,
                    "object_id": target_oid,
                    "battle_position": None,
                    "face_up": True,
                    "owner": owner_tag
                }

                target_gy.append(card_object)

        elif play_type == "To hand":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")

            log = get_log_text(play)

            # Matches ALL formats:
            # Added "A Legendary Ocean" from Deck to hand
            # Returned "Heavy Storm" from S-3 to hand
            # Returned "Moray of Greed" from GY to hand
            # Returned "A Legendary Ocean" from Field Spell Zone to hand
            pattern = r'^(Added|Returned)(?:\s+Set)?\s+"([^"]+)"\s+from\s+(.+?)\s+to\s+hand$'
            match = re.search(pattern, log)

            if not match:
                print(f"⚠️ Could not parse To hand log: {log!r}")
            else:
                action_type = match.group(1)   # Added or Returned
                card_name = match.group(2)
                source = match.group(3)

                is_me = play["username"] == player_1

                if is_me:
                    hand = persistent_state["me_hand"]
                    field = persistent_state["me_field"]
                    gy = persistent_state["me_GY"]
                    field_spell = persistent_state.get("me_field_spell")
                else:
                    hand = persistent_state["op_hand"]
                    field = persistent_state["op_field"]
                    gy = persistent_state["op_GY"]
                    field_spell = persistent_state.get("op_field_spell")

                card_object = None

                # ---------- FROM FIELD ZONE ----------
                if source in field:
                    card_object = field.pop(source)

                # ---------- FROM FIELD SPELL ZONE ----------
                elif source == "Field Spell Zone":
                    card_object = field_spell
                    if is_me:
                        persistent_state["me_field_spell"] = None
                    else:
                        persistent_state["op_field_spell"] = None

                # ---------- FROM GRAVEYARD ----------
                elif source == "GY":
                    for card in gy:
                        if card["name"] == card_name:
                            card_object = card
                            gy.remove(card)
                            break

                # ---------- FROM DECK ----------
                elif source == "Deck":
                    card_object = {
                        "name": card_name,
                        "object_id": play.get("card", {}).get("object_id"),
                        "battle_position": None,
                        "face_up": True,
                        "owner": "p1" if is_me else "p2"
                    }

                    if is_me:
                        persistent_state["me_cards_in_deck"] -= 1
                    else:
                        persistent_state["op_cards_in_deck"] -= 1

                # ---------- FALLBACK ----------
                if card_object is None:
                    card_object = {
                        "name": card_name,
                        "object_id": play.get("card", {}).get("object_id"),
                        "battle_position": None,
                        "face_up": True,
                        "owner": "p1" if is_me else "p2"
                    }

                # ---------- ADD TO HAND ----------
                hand = persistent_state["me_hand"] if card_object["owner"] == "p1" else persistent_state["op_hand"]
                hand.append(card_object)

        elif play_type == "Move":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")

            log = get_log_text(play)

            pattern = r'^Moved\s+"([^"]+)"\s+from\s+(\S+)\s+to\s+(\S+)$'
            m = re.search(pattern, log)

            if not m:
                print(f"❌ Could not parse Move log: {log!r}")
            else:
                card_name  = m.group(1)
                source_raw = m.group(2)
                dest_raw   = m.group(3)

                # mover side (global persistent_state me/op)
                mover_is_me = (play.get("username") == player_1)
                mover_side = "me" if mover_is_me else "op"
                other_side = "op" if mover_side == "me" else "me"

                def side_from_zone_relative_to_mover(zone: str) -> str:
                    # M2-/S2- means "other side relative to mover"
                    if zone.startswith(("M2-", "S2-")):
                        return other_side
                    return mover_side

                def normalize_zone(zone: str) -> str:
                    # M2-3 -> M-3, S2-4 -> S-4
                    return zone.replace("M2-", "M-").replace("S2-", "S-")

                source_side = side_from_zone_relative_to_mover(source_raw)
                dest_side   = side_from_zone_relative_to_mover(dest_raw)

                source_zone = normalize_zone(source_raw)
                dest_zone   = normalize_zone(dest_raw)

                source_field = persistent_state["me_field"] if source_side == "me" else persistent_state["op_field"]
                dest_field   = persistent_state["me_field"] if dest_side == "me" else persistent_state["op_field"]

                # STRICT: must already exist in the source zone (and be a dict)
                card_object = source_field.get(source_zone)

                if card_object is None:
                    print(f'❌ MOVE ERROR: source empty: {source_raw} -> {source_side}_field[{source_zone}] is None')
                elif not isinstance(card_object, dict):
                    print(f'❌ MOVE ERROR: source not a card dict: {source_raw} -> {card_object!r}')
                elif card_object.get("name") != card_name:
                    print(f'❌ MOVE ERROR: name mismatch at {source_raw}: found "{card_object.get("name")}", expected "{card_name}"')
                else:
                    # remove from source
                    source_field[source_zone] = None

                    # place into destination (overwrite whatever is there; strict move)
                    dest_field[dest_zone] = card_object

        elif play_type in ("SS ATK", "SS DEF"):
            print(f"✅ Processing play: {play_type} - {play.get('username')}")

            log = get_log_text(play)

            # Supports BOTH:
            # Special Summoned "X" from GY to M-4 (ATK)
            # Special Summoned banished "Gaia Plate the Earth Giant" (2/2) to M-4 (ATK)
            #
            # Also tolerates:
            # - optional "(x/y)" after the card name
            # - optional "from <zone>" clause
            # - "banished" keyword meaning the source is BANISH when no explicit "from" is present
            pattern = (
                r'^Special Summoned'
                r'(?:\s+(banished))?\s+"([^"]+)"'          # optional 'banished', then card name
                r'(?:\s+\(\d+/\d+\))?'                     # optional "(2/2)"
                r'(?:\s+from\s+(.+?))?'                    # optional "from <zone>"
                r'\s+to\s+(M-\d+)\s+\((ATK|DEF)\)$'         # destination + position
            )
            m = re.search(pattern, log)

            if not m:
                print(f"⚠️ Could not parse SS log: {log!r}")
                continue

            banished_flag = bool(m.group(1))
            card_name     = m.group(2)
            source_raw    = (m.group(3) or "").strip() or None
            dest_zone     = m.group(4)
            pos           = m.group(5)

            # Normalize source
            if banished_flag and source_raw is None:
                source = "BANISH"
            else:
                sr = source_raw or ""
                if sr.startswith("hand"):
                    source = "hand"
                elif sr.startswith("Deck"):
                    source = "Deck"
                elif sr.startswith("GY"):
                    source = "GY"
                elif sr.startswith("Extra Deck"):
                    source = "Extra Deck"
                elif sr.startswith("Field Spell Zone"):
                    source = "Field Spell Zone"
                elif sr.lower().startswith(("banish", "banished")):
                    source = "BANISH"
                else:
                    source = sr  # M-#, S-#, etc.

            summoner_is_me = (play.get("username") == player_1)

            if summoner_is_me:
                s_hand   = persistent_state["me_hand"]
                s_field  = persistent_state["me_field"]
                s_gy     = persistent_state["me_GY"]
                s_banish = persistent_state["me_banish"]
                o_gy     = persistent_state["op_GY"]
                o_banish = persistent_state["op_banish"]
                owner_tag = "p1"
            else:
                s_hand   = persistent_state["op_hand"]
                s_field  = persistent_state["op_field"]
                s_gy     = persistent_state["op_GY"]
                s_banish = persistent_state["op_banish"]
                o_gy     = persistent_state["me_GY"]
                o_banish = persistent_state["me_banish"]
                owner_tag = "p2"

            target_oid = play.get("card", {}).get("object_id")
            card_object = None

            # ---------------- FROM HAND ----------------
            if source == "hand":
                if target_oid is not None:
                    for i, c in enumerate(s_hand):
                        if c.get("object_id") == target_oid:
                            card_object = s_hand.pop(i)
                            break
                if card_object is None:
                    for i, c in enumerate(s_hand):
                        if c.get("name") == card_name:
                            card_object = s_hand.pop(i)
                            break
                if card_object is None:
                    print(f'❌ SS ERROR: could not find "{card_name}" (object_id={target_oid}) in HAND of summoner')
                    continue

            # ---------------- FROM GY ----------------
            elif source == "GY":
                if target_oid is not None:
                    for i, c in enumerate(s_gy):
                        if c.get("object_id") == target_oid:
                            card_object = s_gy.pop(i)
                            break
                if card_object is None:
                    for i, c in enumerate(s_gy):
                        if c.get("name") == card_name:
                            card_object = s_gy.pop(i)
                            break

                # safety: sometimes logs/desync can mean it was in the other GY
                if card_object is None:
                    if target_oid is not None:
                        for i, c in enumerate(o_gy):
                            if c.get("object_id") == target_oid:
                                card_object = o_gy.pop(i)
                                break
                    if card_object is None:
                        for i, c in enumerate(o_gy):
                            if c.get("name") == card_name:
                                card_object = o_gy.pop(i)
                                break

                if card_object is None:
                    print(f'❌ SS ERROR: could not find "{card_name}" (object_id={target_oid}) in either GY')
                    continue

            # ---------------- FROM BANISH ----------------
            elif source == "BANISH":
                if target_oid is not None:
                    for i, c in enumerate(s_banish):
                        if c.get("object_id") == target_oid:
                            card_object = s_banish.pop(i)
                            break
                if card_object is None:
                    for i, c in enumerate(s_banish):
                        if c.get("name") == card_name:
                            card_object = s_banish.pop(i)
                            break

                # safety: try other banish pile if not found
                if card_object is None and target_oid is not None:
                    for i, c in enumerate(o_banish):
                        if c.get("object_id") == target_oid:
                            card_object = o_banish.pop(i)
                            break
                if card_object is None:
                    for i, c in enumerate(o_banish):
                        if c.get("name") == card_name:
                            card_object = o_banish.pop(i)
                            break

                if card_object is None:
                    print(f'❌ SS ERROR: could not find "{card_name}" (object_id={target_oid}) in either BANISH')
                    continue

            # ---------------- FROM DECK ----------------
            elif source == "Deck":
                card_object = {
                    "name": card_name,
                    "object_id": target_oid,
                    "battle_position": pos,
                    "face_up": True,
                    "owner": owner_tag,
                }
                if summoner_is_me:
                    persistent_state["me_cards_in_deck"] = max(0, persistent_state["me_cards_in_deck"] - 1)
                else:
                    persistent_state["op_cards_in_deck"] = max(0, persistent_state["op_cards_in_deck"] - 1)

            # ---------------- FROM EXTRA DECK ----------------
            elif source == "Extra Deck":
                card_object = {
                    "name": card_name,
                    "object_id": target_oid,
                    "battle_position": pos,
                    "face_up": True,
                    "owner": owner_tag,
                }
                if summoner_is_me:
                    persistent_state["me_cards_in_extra_deck"] = max(0, persistent_state["me_cards_in_extra_deck"] - 1)
                else:
                    persistent_state["op_cards_in_extra_deck"] = max(0, persistent_state["op_cards_in_extra_deck"] - 1)

            else:
                print(f"❌ SS ERROR: unknown/unhandled source {source_raw!r} normalized as {source!r} in log {log!r}")
                continue

            # ---------------- PLACE ON FIELD ----------------
            card_object["battle_position"] = pos
            card_object["face_up"] = True
            card_object.setdefault("owner", owner_tag)

            s_field[dest_zone] = card_object

        elif play_type in ("To DEF", "To ATK"):
            print(f"✅ Processing play: {play_type} - {play.get("username")}")

            log = get_log_text(play)

            # Handles:
            # Changed "Giga Gagagigo" in M-3 to DEF
            # Changed "Caius the Shadow Monarch" in M-3 to ATK
            pattern = r'^Changed\s+"([^"]+)"\s+in\s+(\S+)\s+to\s+(ATK|DEF)$'
            m = re.search(pattern, log)

            if not m:
                print(f"⚠️ Could not parse To ATK/DEF log: {log!r}")
            else:
                card_name = m.group(1)
                zone = m.group(2)              # e.g. M-3
                new_pos = m.group(3)           # "ATK" or "DEF"

                mover_is_me = (play.get("username") == player_1)
                field = persistent_state["me_field"] if mover_is_me else persistent_state["op_field"]

                card_obj = field.get(zone)

                # STRICT: do not create anything, only update if it exists
                if card_obj is None:
                    print(f'❌ POS ERROR: {zone} is empty (wanted "{card_name}" -> {new_pos})')
                elif not isinstance(card_obj, dict):
                    print(f'❌ POS ERROR: {zone} is not a card dict: {card_obj!r}')
                elif card_obj.get("name") != card_name:
                    print(f'❌ POS ERROR: name mismatch at {zone}: found "{card_obj.get("name")}", expected "{card_name}"')
                else:
                    card_obj["battle_position"] = new_pos
                    # (optional) ensure it's face-up when switching positions
                    card_obj["face_up"] = True
                    field[zone] = card_obj

        elif play_type == "Summon Token":
            username = play["username"]
            log = get_log_text(play)

            match = re.search(r"(M-\d)", log)
            if not match:
                print(f"Could not find monster zone in log: {log}")
                continue

            zone = match.group(1)

            # extract real token name from replay data
            token_name = play.get("card", {}).get("name", "Token")

            owner = "p1" if username == player_1 else "p2"

            token_card = {
                "name": token_name,
                "object_id": f"token_{play['id']}",
                "battle_position": "DEF",
                "face_up": True,
                "owner": owner
            }

            if owner == "p1":
                persistent_state["me_field"][zone] = token_card
            else:
                persistent_state["op_field"][zone] = token_card

            print(f'{username} summoned "{token_name}" in {zone} (face-up DEF)')

        elif play_type == "Remove Token":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")

            log = get_log_text(play)
            m = re.search(r'^Removed\s+"([^"]+)"\s+from\s+(M-\d+)$', log)

            if not m:
                print(f"⚠️ Could not parse Remove Token log: {log!r}")
            else:
                token_name = m.group(1)   # usually "Token"
                zone = m.group(2)         # M-4, M-5, ...

                remover_is_me = (play.get("username") == player_1)
                field = persistent_state["me_field"] if remover_is_me else persistent_state["op_field"]

                card_obj = field.get(zone)

                # Only remove if it looks like a token (avoid deleting real monsters by accident)
                if isinstance(card_obj, dict) and (
                    str(card_obj.get("object_id", "")).startswith("token_")
                    or card_obj.get("name") == token_name
                    or card_obj.get("name", "").lower().endswith("token")
                ):
                    field[zone] = None
                else:
                    print(f'❌ REMOVE TOKEN ERROR: no token found at {zone}; found={card_obj!r}')

        elif play_type in ("Banish", "Banish FD"):
            print(f"✅ Processing play: {play_type} - {play.get("username")}")

            # Prefer private_log because public_log can hide names for face-down banishes
            log = get_log_text(play)

            # Face-down flag (Banish FD sets face_down=True in your replay)
            face_down = bool(play.get("face_down", False)) or (play_type == "Banish FD")

            # Card info from replay (best source for name/object_id)
            replay_card = play.get("card", {}) or {}
            target_oid = replay_card.get("object_id")
            card_name_from_payload = replay_card.get("name")

            # Examples supported:
            # Banished "X" from M-2
            # Banished Set "X" from S-3
            # Banished "X" from GY
            # Banished "X" from Deck
            # Banished "X" from Extra Deck
            # Banished Set "X" from Field Spell Zone
            # Banished "X" from hand (4/5)
            #
            # Note: public log may be "Banished card from hand (4/4) face-down" (no name)
            pat_named = r'^Banished(?: Set)?\s+"([^"]+)"\s+from\s+(.+?)$'
            pat_anon  = r'^Banished\s+card\s+from\s+(.+?)\s+face-down$'

            m_named = re.search(pat_named, log)
            m_anon  = re.search(pat_anon, log)

            if m_named:
                card_name = m_named.group(1)
                source_raw = m_named.group(2).strip()
            elif m_anon:
                card_name = card_name_from_payload or "UNKNOWN"
                source_raw = m_anon.group(1).strip()
            else:
                # fallback if formats vary
                card_name = card_name_from_payload or "UNKNOWN"
                # try to grab "from ..."
                m_from = re.search(r'\sfrom\s+(.+)$', log)
                source_raw = m_from.group(1).strip() if m_from else "UNKNOWN"

            # Normalize common sources
            if source_raw.startswith("hand"):
                source = "hand"
            elif source_raw.startswith("Deck"):
                source = "Deck"
            elif source_raw.startswith("Extra Deck"):
                source = "Extra Deck"
            elif source_raw.startswith("GY"):
                source = "GY"
            elif source_raw.startswith("Field Spell Zone"):
                source = "Field Spell Zone"
            else:
                source = source_raw  # M-#, S-#, etc.

            actor_is_me = (play.get("username") == player_1)
            default_owner = "p1" if actor_is_me else "p2"

            # Convenience: references for both sides
            me_hand, op_hand = persistent_state["me_hand"], persistent_state["op_hand"]
            me_gy,   op_gy   = persistent_state["me_GY"],   persistent_state["op_GY"]
            me_field, op_field = persistent_state["me_field"], persistent_state["op_field"]

            def find_and_remove_from_list(lst, *, oid=None, name=None):
                """Remove and return the first matching card dict from a list."""
                if oid is not None:
                    for i, c in enumerate(lst):
                        if isinstance(c, dict) and c.get("object_id") == oid:
                            return lst.pop(i)
                if name is not None:
                    for i, c in enumerate(lst):
                        if isinstance(c, dict) and c.get("name") == name:
                            return lst.pop(i)
                return None

            card_object = None

            # ---------------- remove from HAND ----------------
            if source == "hand":
                # First try actor's hand, then opponent (covers rare cases)
                primary = me_hand if actor_is_me else op_hand
                secondary = op_hand if actor_is_me else me_hand

                card_object = find_and_remove_from_list(primary, oid=target_oid, name=card_name)
                if card_object is None:
                    card_object = find_and_remove_from_list(secondary, oid=target_oid, name=card_name)

            # ---------------- remove from FIELD (M-#/S-#) ----------------
            elif re.fullmatch(r'[MS]-\d', source):
                # Try to remove from actor's field first
                primary_field = me_field if actor_is_me else op_field
                secondary_field = op_field if actor_is_me else me_field

                existing = primary_field.get(source)
                if isinstance(existing, dict) and (
                    (target_oid is not None and existing.get("object_id") == target_oid) or existing.get("name") == card_name
                ):
                    card_object = existing
                    primary_field[source] = None
                else:
                    existing2 = secondary_field.get(source)
                    if isinstance(existing2, dict) and (
                        (target_oid is not None and existing2.get("object_id") == target_oid) or existing2.get("name") == card_name
                    ):
                        card_object = existing2
                        secondary_field[source] = None

            # ---------------- remove from FIELD SPELL ZONE ----------------
            elif source == "Field Spell Zone":
                if actor_is_me:
                    existing = persistent_state.get("me_field_spell")
                    if isinstance(existing, dict) and (
                        (target_oid is not None and existing.get("object_id") == target_oid) or existing.get("name") == card_name
                    ):
                        card_object = existing
                        persistent_state["me_field_spell"] = None
                else:
                    existing = persistent_state.get("op_field_spell")
                    if isinstance(existing, dict) and (
                        (target_oid is not None and existing.get("object_id") == target_oid) or existing.get("name") == card_name
                    ):
                        card_object = existing
                        persistent_state["op_field_spell"] = None

                # If not found on actor side, try the other side (safety)
                if card_object is None:
                    existing = persistent_state.get("op_field_spell") if actor_is_me else persistent_state.get("me_field_spell")
                    if isinstance(existing, dict) and (
                        (target_oid is not None and existing.get("object_id") == target_oid) or existing.get("name") == card_name
                    ):
                        card_object = existing
                        if actor_is_me:
                            persistent_state["op_field_spell"] = None
                        else:
                            persistent_state["me_field_spell"] = None

            # ---------------- remove from GY ----------------
            elif source == "GY":
                primary = me_gy if actor_is_me else op_gy
                secondary = op_gy if actor_is_me else me_gy

                card_object = find_and_remove_from_list(primary, oid=target_oid, name=card_name)
                if card_object is None:
                    card_object = find_and_remove_from_list(secondary, oid=target_oid, name=card_name)

            # ---------------- banish from DECK (not enumerated) ----------------
            elif source == "Deck":
                card_object = {
                    "name": card_name_from_payload or card_name,
                    "object_id": target_oid,
                    "battle_position": None,
                    "face_up": (not face_down),
                    "owner": default_owner,
                }
                if actor_is_me:
                    persistent_state["me_cards_in_deck"] = max(0, persistent_state["me_cards_in_deck"] - 1)
                else:
                    persistent_state["op_cards_in_deck"] = max(0, persistent_state["op_cards_in_deck"] - 1)

            # ---------------- banish from EXTRA DECK (not enumerated) ----------------
            elif source == "Extra Deck":
                card_object = {
                    "name": card_name_from_payload or card_name,
                    "object_id": target_oid,
                    "battle_position": None,
                    "face_up": (not face_down),
                    "owner": default_owner,
                }
                if actor_is_me:
                    persistent_state["me_cards_in_extra_deck"] = max(0, persistent_state["me_cards_in_extra_deck"] - 1)
                else:
                    persistent_state["op_cards_in_extra_deck"] = max(0, persistent_state["op_cards_in_extra_deck"] - 1)

            else:
                print(f"⚠️ BANISH: unhandled source {source_raw!r} parsed as {source!r} (log={log!r})")

            # ---------------- fallback: create card if we couldn't find it ----------------
            if card_object is None:
                card_object = {
                    "name": card_name_from_payload or card_name,
                    "object_id": target_oid,
                    "battle_position": None,
                    "face_up": (not face_down),
                    "owner": default_owner,
                }

            # ---------------- normalize banish card fields ----------------
            card_object["battle_position"] = None
            card_object["face_up"] = (not face_down)
            card_object.setdefault("owner", default_owner)

            # ---------------- add to correct banish pile (by owner) ----------------
            if card_object.get("owner") == "p1":
                persistent_state["me_banish"].append(card_object)
            else:
                persistent_state["op_banish"].append(card_object)

        elif play_type == "To T Deck":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            log = get_log_text(play)

            # Examples:
            # Returned Set "A Legendary Ocean" from Field Spell Zone to top of deck
            # Returned "Warrior of Atlantis" from M-3 to top of deck
            # Returned "Terraforming" from S-4 to top of deck
            # Returned "Brain Control" from GY to top of deck
            # Returned "Warrior of Atlantis" from hand (1/7) to top of deck
            pattern = r'^Returned(?: Set)?\s+"([^"]+)"\s+from\s+(.+?)\s+to\s+top\s+of\s+deck$'
            m = re.search(pattern, log)

            card_name = None
            source_raw = None
            if m:
                card_name = m.group(1)
                source_raw = m.group(2).strip()
            else:
                # public log may hide the name; fall back to play["card"]
                card_name = play.get("card", {}).get("name")
                # try to at least capture the source
                m2 = re.search(r'^Returned(?: Set)?\s+(?:card|"[^"]+")\s+from\s+(.+?)\s+to\s+top\s+of\s+deck$', log)
                source_raw = m2.group(1).strip() if m2 else None

            target_oid = play.get("card", {}).get("object_id")  # may be missing for hidden logs
            is_me = (play.get("username") == player_1)

            # pick side refs
            hand = persistent_state["me_hand"] if is_me else persistent_state["op_hand"]
            field = persistent_state["me_field"] if is_me else persistent_state["op_field"]
            gy = persistent_state["me_GY"] if is_me else persistent_state["op_GY"]
            ban = persistent_state["me_banish"] if is_me else persistent_state["op_banish"]
            fspell_key = "me_field_spell" if is_me else "op_field_spell"

            # normalize source
            source = None
            if source_raw:
                if source_raw.startswith("hand"):
                    source = "hand"
                elif source_raw == "GY":
                    source = "GY"
                elif source_raw == "BANISH" or source_raw == "Banished":
                    source = "BANISH"
                elif source_raw == "Field Spell Zone":
                    source = "Field Spell Zone"
                else:
                    source = source_raw  # M-3 / S-4 / Deck / etc.

            card_object = None

            # ---- remove from indicated source first ----
            if source == "hand":
                if target_oid is not None:
                    for i, c in enumerate(hand):
                        if c.get("object_id") == target_oid:
                            card_object = hand.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(hand):
                        if c.get("name") == card_name:
                            card_object = hand.pop(i); break

            elif source == "GY":
                if target_oid is not None:
                    for i, c in enumerate(gy):
                        if c.get("object_id") == target_oid:
                            card_object = gy.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(gy):
                        if c.get("name") == card_name:
                            card_object = gy.pop(i); break

            elif source == "BANISH":
                if target_oid is not None:
                    for i, c in enumerate(ban):
                        if c.get("object_id") == target_oid:
                            card_object = ban.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(ban):
                        if c.get("name") == card_name:
                            card_object = ban.pop(i); break

            elif source == "Field Spell Zone":
                fs = persistent_state.get(fspell_key)
                if isinstance(fs, dict) and (
                    (target_oid is not None and fs.get("object_id") == target_oid) or (card_name and fs.get("name") == card_name)
                ):
                    card_object = fs
                    persistent_state[fspell_key] = None

            elif isinstance(source, str) and source in field:
                c = field.get(source)
                if isinstance(c, dict) and (
                    (target_oid is not None and c.get("object_id") == target_oid) or (card_name and c.get("name") == card_name)
                ):
                    card_object = c
                    field[source] = None

            # ---- fallback search (if source missing/hidden) ----
            if card_object is None:
                # hand
                if target_oid is not None:
                    for i, c in enumerate(hand):
                        if c.get("object_id") == target_oid:
                            card_object = hand.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(hand):
                        if c.get("name") == card_name:
                            card_object = hand.pop(i); break

            if card_object is None:
                # field
                for z, c in field.items():
                    if isinstance(c, dict) and (
                        (target_oid is not None and c.get("object_id") == target_oid) or (card_name and c.get("name") == card_name)
                    ):
                        card_object = c
                        field[z] = None
                        break

            if card_object is None:
                # GY
                if target_oid is not None:
                    for i, c in enumerate(gy):
                        if c.get("object_id") == target_oid:
                            card_object = gy.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(gy):
                        if c.get("name") == card_name:
                            card_object = gy.pop(i); break

            if card_object is None:
                # banish
                if target_oid is not None:
                    for i, c in enumerate(ban):
                        if c.get("object_id") == target_oid:
                            card_object = ban.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(ban):
                        if c.get("name") == card_name:
                            card_object = ban.pop(i); break

            if card_object is None:
                # field spell zone
                fs = persistent_state.get(fspell_key)
                if isinstance(fs, dict) and (
                    (target_oid is not None and fs.get("object_id") == target_oid) or (card_name and fs.get("name") == card_name)
                ):
                    card_object = fs
                    persistent_state[fspell_key] = None

            # ---- increment deck count (your requirement) ----
            if is_me:
                persistent_state["me_cards_in_deck"] += 1
            else:
                persistent_state["op_cards_in_deck"] += 1

        elif play_type == "To ED":
            print(f"✅ Processing play: {play_type} - {play.get("username")}")
            log = get_log_text(play)

            # Examples:
            # Returned banished "Elemental HERO Gaia" (1/1) to Extra Deck
            # Returned "Elemental HERO Absolute Zero" from GY to Extra Deck
            # Returned "Elemental HERO Absolute Zero" from M-3 to Extra Deck
            pattern = r'^Returned\s+(?:banished\s+)?\"([^\"]+)\"(?:\s+\(\d+/\d+\))?\s+from\s+(.+?)\s+to\s+Extra\s+Deck$'
            m = re.search(pattern, log)

            card_name = None
            source_raw = None
            if m:
                card_name = m.group(1)
                source_raw = m.group(2).strip()
            else:
                # Some logs omit "from X" (banished case can be weird); fall back:
                card_name = play.get("card", {}).get("name")
                m2 = re.search(r'^Returned\s+(?:banished\s+)?\"([^\"]+)\"(?:\s+\(\d+/\d+\))?\s+to\s+Extra\s+Deck$', log)
                if m2:
                    card_name = m2.group(1)
                # if still no source, assume BANISH first then search elsewhere
                source_raw = None

            target_oid = play.get("card", {}).get("object_id")
            is_me = (play.get("username") == player_1)

            # side refs
            hand = persistent_state["me_hand"] if is_me else persistent_state["op_hand"]
            field = persistent_state["me_field"] if is_me else persistent_state["op_field"]
            gy = persistent_state["me_GY"] if is_me else persistent_state["op_GY"]
            ban = persistent_state["me_banish"] if is_me else persistent_state["op_banish"]
            fspell_key = "me_field_spell" if is_me else "op_field_spell"

            # normalize source
            source = None
            if source_raw:
                if source_raw.startswith("hand"):
                    source = "hand"
                elif source_raw == "GY":
                    source = "GY"
                elif source_raw == "BANISH" or source_raw == "Banished":
                    source = "BANISH"
                elif source_raw == "Field Spell Zone":
                    source = "Field Spell Zone"
                else:
                    source = source_raw  # M-3 / S-2 / etc.

            card_object = None

            # ---- remove from indicated source first ----
            if source == "BANISH":
                if target_oid is not None:
                    for i, c in enumerate(ban):
                        if c.get("object_id") == target_oid:
                            card_object = ban.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(ban):
                        if c.get("name") == card_name:
                            card_object = ban.pop(i); break

            elif source == "GY":
                if target_oid is not None:
                    for i, c in enumerate(gy):
                        if c.get("object_id") == target_oid:
                            card_object = gy.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(gy):
                        if c.get("name") == card_name:
                            card_object = gy.pop(i); break

            elif source == "hand":
                if target_oid is not None:
                    for i, c in enumerate(hand):
                        if c.get("object_id") == target_oid:
                            card_object = hand.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(hand):
                        if c.get("name") == card_name:
                            card_object = hand.pop(i); break

            elif source == "Field Spell Zone":
                fs = persistent_state.get(fspell_key)
                if isinstance(fs, dict) and (
                    (target_oid is not None and fs.get("object_id") == target_oid) or (card_name and fs.get("name") == card_name)
                ):
                    card_object = fs
                    persistent_state[fspell_key] = None

            elif isinstance(source, str) and source in field:
                c = field.get(source)
                if isinstance(c, dict) and (
                    (target_oid is not None and c.get("object_id") == target_oid) or (card_name and c.get("name") == card_name)
                ):
                    card_object = c
                    field[source] = None

            # ---- fallback search (banish -> field -> gy -> hand -> field spell) ----
            if card_object is None:
                if target_oid is not None:
                    for i, c in enumerate(ban):
                        if c.get("object_id") == target_oid:
                            card_object = ban.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(ban):
                        if c.get("name") == card_name:
                            card_object = ban.pop(i); break

            if card_object is None:
                for z, c in field.items():
                    if isinstance(c, dict) and (
                        (target_oid is not None and c.get("object_id") == target_oid) or (card_name and c.get("name") == card_name)
                    ):
                        card_object = c
                        field[z] = None
                        break

            if card_object is None:
                if target_oid is not None:
                    for i, c in enumerate(gy):
                        if c.get("object_id") == target_oid:
                            card_object = gy.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(gy):
                        if c.get("name") == card_name:
                            card_object = gy.pop(i); break

            if card_object is None:
                if target_oid is not None:
                    for i, c in enumerate(hand):
                        if c.get("object_id") == target_oid:
                            card_object = hand.pop(i); break
                if card_object is None and card_name:
                    for i, c in enumerate(hand):
                        if c.get("name") == card_name:
                            card_object = hand.pop(i); break

            if card_object is None:
                fs = persistent_state.get(fspell_key)
                if isinstance(fs, dict) and (
                    (target_oid is not None and fs.get("object_id") == target_oid) or (card_name and fs.get("name") == card_name)
                ):
                    card_object = fs
                    persistent_state[fspell_key] = None

            # ---- increment extra deck count (your requirement) ----
            if is_me:
                persistent_state["me_cards_in_extra_deck"] += 1
            else:
                persistent_state["op_cards_in_extra_deck"] += 1
                    
        else:
            print(f"❌ Processing play: {play_type} - {play.get('username')}")
            # print(json.dumps(play, indent=2))

        ACTION = f"{play.get('username', '')}, {play['play']}"
        STATE_ACTION_PAIRS.append({
            "state": copy.deepcopy(persistent_state),
            "action": ACTION
        }) 

    
    run_replay_viewer(STATE_ACTION_PAIRS)
    input("Replay viewer finished. Press Enter to go to next replay...")

