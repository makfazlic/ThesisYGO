# simulator/game_ui.py
import os
import sys
import pygame

def run_replay_viewer(
    state_action_pairs,
    *,
    window_size=(1100, 800),
    caption="Replay Viewer",
    image_dir=None,
    start_index=0,
    fps=60,
):
    """
    state_action_pairs: list[dict] where each item looks like:
        {
          "state": {...},
          "action": "optional text"
        }
    This function blocks until the user closes the window.
    """

    # --- basic validation ---
    if not isinstance(state_action_pairs, list) or not state_action_pairs:
        raise ValueError("state_action_pairs must be a non-empty list")

    # Resolve image directory relative to this file by default
    if image_dir is None:
        # default: ../images relative to this file (simulator/game_ui.py)
        image_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images"))

    pygame.init()

    # ---------------- window ----------------
    W, H = window_size
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption(caption)

    # ---------------- styling ----------------
    BG = (30, 30, 30)
    BORDER = (235, 235, 235)
    TEXT = (255, 255, 255)
    FILL_RGBA = (255, 255, 255, 14)
    OUTLINE = 1

    font_lp = pygame.font.SysFont(None, 44)
    font_lbl = pygame.font.SysFont(None, 22)
    font_phase = pygame.font.SysFont(None, 26)
    font_turn = pygame.font.SysFont(None, 26)
    

    ROWS, COLS = 4, 7

    # --- action bar (bottom) ---
    ACTION_BAR_H = 34
    ACTION_BAR_PAD = 10
    ACTION_BG = (20, 20, 20)
    ACTION_FG = (210, 210, 210)

    # ---------------- buttons ----------------
    BTN_W, BTN_H = 120, 38
    BTN_PAD = 10
    btn_prev = pygame.Rect(BTN_PAD, BTN_PAD, BTN_W, BTN_H)
    btn_next = pygame.Rect(W - BTN_PAD - BTN_W, BTN_PAD, BTN_W, BTN_H)

    def draw_button(rect, label, enabled=True):
        bg = (55, 55, 55) if enabled else (35, 35, 35)
        fg = TEXT if enabled else (160, 160, 160)
        pygame.draw.rect(screen, bg, rect, border_radius=10)
        pygame.draw.rect(screen, BORDER, rect, OUTLINE, border_radius=10)
        img = font_lbl.render(label, True, fg)
        screen.blit(img, img.get_rect(center=rect.center))

    def get_state_at(pairs, idx):
        return pairs[idx]["state"]

    def get_action_at(pairs, idx):
        return pairs[idx].get("action")

    # ---------------- images ----------------
    IMAGE_DIR = image_dir
    image_cache = {}

    def safe_filename(name: str) -> str:
        bad = '<>:"/\\|?*'
        for ch in bad:
            name = name.replace(ch, "_")
        return name.strip()

    def card_to_name(card):
        if card is None:
            return None
        if isinstance(card, dict):
            return card.get("name")
        if isinstance(card, str):
            return card
        return None

    # --- NEW: generate a placeholder card surface when image file is missing ---
    def make_text_card_surface(card_name: str, w: int = 421, h: int = 614):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((18, 18, 18, 255))

        # outer border
        pygame.draw.rect(surf, (235, 235, 235), pygame.Rect(0, 0, w, h), 6, border_radius=18)
        # inner area
        pygame.draw.rect(surf, (45, 45, 45), pygame.Rect(10, 10, w - 20, h - 20), 0, border_radius=14)

        # title bar
        title_bar = pygame.Rect(18, 18, w - 36, 70)
        pygame.draw.rect(surf, (25, 25, 25), title_bar, border_radius=10)
        pygame.draw.rect(surf, (90, 90, 90), title_bar, 2, border_radius=10)

        # wrapped name text
        name = str(card_name)
        f = pygame.font.SysFont(None, 34)
        max_w = title_bar.w - 16

        words = name.split()
        lines = []
        line = ""
        for word in words:
            test = (line + " " + word).strip()
            if f.size(test)[0] <= max_w:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)

        y = title_bar.y + 10
        for ln in lines[:2]:
            txt = f.render(ln, True, (255, 255, 255))
            surf.blit(txt, (title_bar.x + 8, y))
            y += txt.get_height() + 2

        # simple "art box"
        art = pygame.Rect(18, 100, w - 36, int((h - 140) * 0.55))
        pygame.draw.rect(surf, (28, 28, 28), art, border_radius=12)
        pygame.draw.rect(surf, (80, 80, 80), art, 2, border_radius=12)

        # text block area
        text_box = pygame.Rect(18, art.bottom + 14, w - 36, h - (art.bottom + 14) - 18)
        pygame.draw.rect(surf, (30, 30, 30), text_box, border_radius=12)
        pygame.draw.rect(surf, (80, 80, 80), text_box, 2, border_radius=12)

        small = pygame.font.SysFont(None, 24)
        hint = small.render("IMAGE NOT FOUND", True, (200, 200, 200))
        surf.blit(hint, hint.get_rect(center=text_box.center))

        return surf

    def load_card_image(card_name: str):
        if not card_name:
            return None
        if card_name in image_cache:
            return image_cache[card_name]

        base = safe_filename(str(card_name))
        jpg = os.path.join(IMAGE_DIR, f"{base}.jpg")
        png = os.path.join(IMAGE_DIR, f"{base}.png")
        path = jpg if os.path.exists(jpg) else (png if os.path.exists(png) else None)

        if not path:
            # --- CHANGED: instead of None, cache a generated placeholder image ---
            img = make_text_card_surface(card_name)
            image_cache[card_name] = img
            return img

        try:
            img = pygame.image.load(path).convert_alpha()
        except pygame.error:
            img = None

        if img is None:
            # --- CHANGED: if pygame fails to load, still return placeholder ---
            img = make_text_card_surface(card_name)

        image_cache[card_name] = img
        return img

    # ---------------- layout math ----------------
    ASPECT = 1.35  # card height = width * ASPECT

    PAD_X = 12
    GAP = 6

    HAND_PAD = 10
    HAND_GAP = 14
    LP_PAD = 12

    MIN_CELL_W = 70
    MAX_HAND_H_FRAC = 0.16

    lp_h = font_lp.get_height()

    HAND_H = int(H * MAX_HAND_H_FRAC)
    HAND_H = max(70, min(HAND_H, 160))

    TOP_RESERVED    = LP_PAD + lp_h + 10 + HAND_H + HAND_GAP
    BOTTOM_RESERVED = LP_PAD + lp_h + 10 + HAND_H + HAND_GAP + ACTION_BAR_H

    avail_w = W - 2 * PAD_X - (COLS - 1) * GAP
    avail_h = H - TOP_RESERVED - BOTTOM_RESERVED - (ROWS - 1) * GAP
    avail_w = max(1, avail_w)
    avail_h = max(1, avail_h)

    cell_w_from_w = avail_w // COLS
    cell_h_from_h = avail_h // ROWS
    cell_w_from_h = int(cell_h_from_h / ASPECT)

    cell_w = min(cell_w_from_w, cell_w_from_h)
    cell_w = max(MIN_CELL_W, cell_w)
    cell_h = int(cell_w * ASPECT)

    grid_w = COLS * cell_w + (COLS - 1) * GAP
    grid_h = ROWS * cell_h + (ROWS - 1) * GAP

    if grid_w > W - 2 * PAD_X or grid_h > avail_h:
        cell_w = max(1, min(cell_w_from_w, cell_w_from_h))
        cell_h = int(cell_w * ASPECT)
        grid_w = COLS * cell_w + (COLS - 1) * GAP
        grid_h = ROWS * cell_h + (ROWS - 1) * GAP

    grid_x0 = (W - grid_w) // 2
    grid_y0 = TOP_RESERVED + (avail_h - grid_h) // 2
    grid_center_y = grid_y0 + grid_h // 2

    op_hand_rect = pygame.Rect(grid_x0, grid_y0 - HAND_GAP - HAND_H, grid_w, HAND_H)
    me_hand_rect = pygame.Rect(grid_x0, grid_y0 + grid_h + HAND_GAP, grid_w, HAND_H)

    def zone_rect(r, c):
        x = grid_x0 + c * (cell_w + GAP)
        y = grid_y0 + r * (cell_h + GAP)
        return pygame.Rect(x, y, cell_w, cell_h)

    def draw_zone_box(rect):
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        surf.fill(FILL_RGBA)
        screen.blit(surf, rect.topleft)
        pygame.draw.rect(screen, BORDER, rect, OUTLINE, border_radius=10)

    def draw_text_center(rect, text):
        img = font_lbl.render(str(text), True, TEXT)
        screen.blit(img, img.get_rect(center=rect.center))

    def label_for_cell(r, c):
        if 1 <= c <= 5:
            return (f"S-{c}" if r in (0, 3) else f"M-{c}")
        if c == 0:
            return {0: "DECK", 1: "GY", 2: "FIELD", 3: "EXTRA"}[r]
        if c == 6:
            return {0: "EXTRA", 1: "FIELD", 2: "GY", 3: "DECK"}[r]
        return ""

    def gy_rect(owner: str) -> pygame.Rect:
        return zone_rect(1, 0) if owner == "op" else zone_rect(2, 6)
    
    def pretty_phase(p):
        if p is None:
            return "—"
        return str(p).replace("_", " ").title()

    def draw_phase_box(text, anchor="top"):
        # anchor: "top" or "bottom"
        pad = 10
        margin = 12

        label = f"PHASE: {text}"
        img = font_phase.render(label, True, TEXT)

        # background box around the text
        box = img.get_rect()
        box.w += pad * 2
        box.h += pad * 2

        if anchor == "top":
            box.topright = (W - margin, 5*margin)
        else:
            box.bottomright = (W - margin, H - 5*margin - ACTION_BAR_H)

        pygame.draw.rect(screen, (20, 20, 20), box, border_radius=10)
        pygame.draw.rect(screen, BORDER, box, OUTLINE, border_radius=10)

        # blit text centered in box
        screen.blit(img, img.get_rect(center=box.center))

    def draw_turn_box(turn_value):
        pad = 10
        margin = 12

        label = f"TURN: {turn_value if turn_value is not None else '—'}"
        img = font_turn.render(label, True, TEXT)

        box = img.get_rect()
        box.w += pad * 2
        box.h += pad * 2

        # bottom-left, above the action bar
        box.bottomleft = (margin, H - margin - ACTION_BAR_H)

        pygame.draw.rect(screen, (20, 20, 20), box, border_radius=10)
        pygame.draw.rect(screen, BORDER, box, OUTLINE, border_radius=10)

        screen.blit(img, img.get_rect(center=box.center))

    def banish_rect(owner: str) -> pygame.Rect:
        gy = gy_rect(owner)
        if owner == "op":
            x = gy.x - (cell_w + GAP)
            if x < 0:
                x = gy.right + GAP
            return pygame.Rect(x, gy.y, cell_w, cell_h)
        else:
            x = gy.right + GAP
            if x + cell_w > W:
                x = gy.x - (cell_w + GAP)
            return pygame.Rect(x, gy.y, cell_w, cell_h)

    def get_card_image_name(card):
        if card is None:
            return None
        if isinstance(card, dict):
            if card.get("face_up") is False:
                return "BACK"
            return card.get("name")
        if isinstance(card, str):
            return card
        return None

    def draw_card_image_in_rect(rect, card):
        name = get_card_image_name(card)
        if not name:
            return False

        img = load_card_image(name)
        if not img:
            return False

        pos = "ATK"
        if isinstance(card, dict):
            pos = str(card.get("battle_position", "ATK")).upper()

        pad = 6
        target = pygame.Rect(rect.x + pad, rect.y + pad, rect.w - 2*pad, rect.h - 2*pad)
        if target.w <= 0 or target.h <= 0:
            return False

        iw, ih = img.get_size()
        scale = min(target.w / iw, target.h / ih)
        new_w = max(1, int(iw * scale))
        new_h = max(1, int(ih * scale))
        scaled = pygame.transform.smoothscale(img, (new_w, new_h))

        draw_surf = scaled
        if pos == "DEF":
            draw_surf = pygame.transform.rotate(scaled, 90)

        dst = draw_surf.get_rect(center=target.center)
        screen.blit(draw_surf, dst.topleft)
        return True

    def draw_hand(rect, hand_list):
        fill = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        fill.fill((255, 255, 255, 14))
        screen.blit(fill, rect.topleft)
        pygame.draw.rect(screen, BORDER, rect, OUTLINE, border_radius=14)

        names = [card_to_name(c) for c in hand_list]
        names = [n for n in names if n]
        if not names:
            return

        thumb_h = rect.h - 2 * HAND_PAD
        thumb_w = int(thumb_h / 1.35)
        if thumb_w <= 0 or thumb_h <= 0:
            return

        n = len(names)
        step = 0 if n == 1 else min(
            thumb_w + 10,
            max(6, (rect.w - 2 * HAND_PAD - thumb_w) // (n - 1))
        )

        x = rect.x + HAND_PAD
        y = rect.y + HAND_PAD

        for name in names:
            card_r = pygame.Rect(x, y, thumb_w, thumb_h)
            img = load_card_image(name)
            if img:
                screen.blit(pygame.transform.smoothscale(img, card_r.size), card_r.topleft)
            else:
                pygame.draw.rect(screen, (35, 35, 35), card_r, border_radius=8)
                pygame.draw.rect(screen, BORDER, card_r, 2, border_radius=8)
                draw_text_center(card_r, name)
            x += step

    # ---------------- modal (GY / BANISH viewer) ----------------
    ui = {"open": False, "owner": None, "kind": None, "scroll": 0, "close_rect": None, "max_scroll": 0}

    def get_pile_list(state, owner: str, kind: str):
        if kind == "GY":
            return state.get("op_GY" if owner == "op" else "me_GY", [])
        if kind == "BANISH":
            return state.get("op_banish" if owner == "op" else "me_banish", [])
        return []

    def draw_pile_modal(state):
        owner = ui["owner"]
        kind = ui["kind"]
        pile = get_pile_list(state, owner, kind)

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(70, 70, W - 140, H - 140)
        pygame.draw.rect(screen, (20, 20, 20), panel, border_radius=16)
        pygame.draw.rect(screen, BORDER, panel, OUTLINE, border_radius=16)

        who = "Opponent" if owner == "op" else "Your"
        title = f"{who} {'Graveyard' if kind == 'GY' else 'Banished'}"
        timg = font_lp.render(title, True, TEXT)
        screen.blit(timg, (panel.x + 18, panel.y + 14))

        close_rect = pygame.Rect(panel.right - 54, panel.y + 14, 40, 40)
        pygame.draw.rect(screen, (40, 40, 40), close_rect, border_radius=10)
        pygame.draw.rect(screen, BORDER, close_rect, 2, border_radius=10)
        ximg = font_lbl.render("X", True, TEXT)
        screen.blit(ximg, ximg.get_rect(center=close_rect.center))

        content = pygame.Rect(panel.x + 18, panel.y + 64, panel.w - 36, panel.h - 82)
        pygame.draw.rect(screen, (15, 15, 15), content, border_radius=12)
        pygame.draw.rect(screen, BORDER, content, 2, border_radius=12)

        names = [card_to_name(c) for c in pile]
        names = [n for n in names if n]

        pad = 14
        thumb_w = 120
        thumb_h = int(thumb_w * 1.35)
        gap = 14

        cols = max(1, (content.w - 2 * pad + gap) // (thumb_w + gap))
        rows = (len(names) + cols - 1) // cols
        total_h = 2 * pad + rows * thumb_h + max(0, rows - 1) * gap

        max_scroll = max(0, total_h - content.h)
        ui["scroll"] = max(0, min(ui["scroll"], max_scroll))

        old_clip = screen.get_clip()
        screen.set_clip(content)

        start_x = content.x + pad
        start_y = content.y + pad - ui["scroll"]

        for i, name in enumerate(names):
            rr = i // cols
            cc = i % cols
            x = start_x + cc * (thumb_w + gap)
            y = start_y + rr * (thumb_h + gap)
            rect = pygame.Rect(x, y, thumb_w, thumb_h)

            img = load_card_image(name)
            if img:
                screen.blit(pygame.transform.smoothscale(img, rect.size), rect.topleft)
            else:
                pygame.draw.rect(screen, (35, 35, 35), rect, border_radius=8)
                draw_text_center(rect, name)

            pygame.draw.rect(screen, BORDER, rect, 2, border_radius=8)

        screen.set_clip(old_clip)
        ui["close_rect"] = close_rect
        ui["max_scroll"] = max_scroll

    # ---------------- render ----------------
    def render(state, action_text=None, idx=0, total=1):
        screen.fill(BG)

        draw_button(btn_prev, "Prev", enabled=(idx > 0))
        draw_button(btn_next, "Next", enabled=(idx < total - 1))
        step_img = font_lbl.render(f"{idx + 1} / {total}", True, TEXT)
        screen.blit(step_img, (btn_prev.right + 12, btn_prev.y + 10))

        op_lp = state.get("op_life", 8000)
        me_lp = state.get("me_life", 8000)
        op_img = font_lp.render(f"LP: {op_lp}", True, TEXT)
        me_img = font_lp.render(f"LP: {me_lp}", True, TEXT)
        screen.blit(op_img, op_img.get_rect(midtop=(W // 2, LP_PAD)))
        screen.blit(me_img, me_img.get_rect(midbottom=(W // 2, H - LP_PAD - 5 - ACTION_BAR_H)))

        op_phase = pretty_phase(state.get("op_phase"))
        me_phase = pretty_phase(state.get("me_phase"))

        draw_phase_box(op_phase, anchor="top")
        draw_phase_box(me_phase, anchor="bottom")

        draw_hand(op_hand_rect, state.get("op_hand", []))
        draw_hand(me_hand_rect, state.get("me_hand", []))

        draw_turn_box(state.get("turn"))

        for r in range(ROWS):
            for c in range(COLS):
                rect = zone_rect(r, c)
                draw_zone_box(rect)
                label = label_for_cell(r, c)

                if 1 <= c <= 5:
                    key = label
                    card = (state.get("op_field", {}).get(key) if r in (0, 1)
                            else state.get("me_field", {}).get(key))
                    if not draw_card_image_in_rect(rect, card):
                        draw_text_center(rect, label)
                else:
                    if label == "DECK":
                        n = state.get("op_cards_in_deck", 0) if r in (0, 1) else state.get("me_cards_in_deck", 0)
                        draw_text_center(rect, f"DECK ({n})")
                    elif label == "EXTRA":
                        n = state.get("op_cards_in_extra_deck", 0) if r in (0, 1) else state.get("me_cards_in_extra_deck", 0)
                        draw_text_center(rect, f"EXTRA ({n})")
                    elif label == "GY":
                        n = len(state.get("op_GY", [])) if r in (0, 1) else len(state.get("me_GY", []))
                        draw_text_center(rect, f"GY ({n})")
                    elif label == "FIELD":
                        fs = state.get("op_field_spell") if r in (0, 1) else state.get("me_field_spell")
                        if not draw_card_image_in_rect(rect, fs):
                            draw_text_center(rect, card_to_name(fs) or "FIELD")

        op_b = banish_rect("op")
        me_b = banish_rect("me")
        draw_zone_box(op_b)
        draw_zone_box(me_b)
        draw_text_center(op_b, f"BAN ({len(state.get('op_banish', []))})")
        draw_text_center(me_b, f"BAN ({len(state.get('me_banish', []))})")

        pygame.draw.line(screen, BORDER, (0, grid_center_y), (W, grid_center_y), OUTLINE)

        if ui["open"]:
            draw_pile_modal(state)

        bar = pygame.Rect(0, H - ACTION_BAR_H, W, ACTION_BAR_H)
        pygame.draw.rect(screen, ACTION_BG, bar)

        if action_text is not None:
            a = str(action_text)
            aimg = font_lbl.render(a[:160], True, ACTION_FG)
            screen.blit(aimg, (ACTION_BAR_PAD, bar.y + (ACTION_BAR_H - aimg.get_height()) // 2))

        pygame.display.flip()

    # ---------------- main loop ----------------
    current_index = max(0, min(int(start_index), len(state_action_pairs) - 1))
    state = get_state_at(state_action_pairs, current_index)

    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return  # exit viewer cleanly

            # modal controls
            if ui["open"]:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    ui["open"] = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 3:
                        ui["open"] = False
                    elif ui["close_rect"] and ui["close_rect"].collidepoint(event.pos):
                        ui["open"] = False
                if event.type == pygame.MOUSEWHEEL:
                    ui["scroll"] -= event.y * 40
                    ui["scroll"] = max(0, min(ui["scroll"], ui["max_scroll"]))
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_prev.collidepoint(event.pos) and current_index > 0:
                    current_index -= 1
                    state = get_state_at(state_action_pairs, current_index)
                    continue

                if btn_next.collidepoint(event.pos) and current_index < len(state_action_pairs) - 1:
                    current_index += 1
                    state = get_state_at(state_action_pairs, current_index)
                    continue

                if gy_rect("op").collidepoint(event.pos):
                    ui.update({"open": True, "owner": "op", "kind": "GY", "scroll": 0})
                elif gy_rect("me").collidepoint(event.pos):
                    ui.update({"open": True, "owner": "me", "kind": "GY", "scroll": 0})
                elif banish_rect("op").collidepoint(event.pos):
                    ui.update({"open": True, "owner": "op", "kind": "BANISH", "scroll": 0})
                elif banish_rect("me").collidepoint(event.pos):
                    ui.update({"open": True, "owner": "me", "kind": "BANISH", "scroll": 0})

        action = get_action_at(state_action_pairs, current_index)
        render(state, action_text=action, idx=current_index, total=len(state_action_pairs))
        clock.tick(fps)