
(() => {
  const UNKNOWN = "UNKNOWN";

  function get(obj, key) {
    try {
      return typeof obj?.data === "function"
        ? obj.data(key)
        : obj?.[key];
    } catch {
      return undefined;
    }
  }

  function ownerCode(owner) {
    const username =
      typeof owner === "string" ? owner : owner?.username;

    if (typeof username !== "string") return UNKNOWN;
    if (username === window.player1?.username) return "p1";
    if (username === window.player2?.username) return "p2";
    return UNKNOWN;
  }

  function cardInfo(card, zone) {
    if (card === null) return null;
    if (card === undefined) return UNKNOWN;

    const name = get(get(card, "cardfront"), "name")
      ?? get(card, "name");
    const faceDown = get(card, "face_down");
    const token = get(card, "is_token") ?? get(card, "token");

    const faceUp = zone === "hand"
      ? null
      : typeof faceDown === "boolean"
        ? !faceDown
        : UNKNOWN;

    const position = zone === "monster"
      ? get(card, "inATK") === true
        ? "ATK"
        : get(card, "inDEF") === true
          ? "DEF"
          : UNKNOWN
      : null;

    return {
      uid: UNKNOWN,
      name: typeof name === "string" ? name : UNKNOWN,
      object_id: UNKNOWN,
      owner: ownerCode(get(card, "owner")),
      battle_position: position,
      face_up: faceUp,
      is_token: typeof token === "boolean" ? token : UNKNOWN
    };
  }

  const zoneCards = (p, key, zone) =>
    Array.isArray(p?.[key])
      ? p[key].map(c => cardInfo(c, zone))
      : UNKNOWN;

  function spellCard(p) {
    if ("fieldSpell" in p)
      return cardInfo(p.fieldSpell, "spell");
    if ("field_spell" in p)
      return cardInfo(p.field_spell, "spell");
    return UNKNOWN;
  }

  function playerState(p, prefix) {
    const field = {};

    for (const kind of ["M", "S"]) {
      for (let i = 1; i <= 5; i++) {
        field[`${kind}-${i}`] = cardInfo(
          p[`${kind.toLowerCase()}${i}`],
          kind === "M" ? "monster" : "spell"
        );
      }
    }

    return {
      [`${prefix}_hand`]: zoneCards(p, "hand_arr", "hand"),
      [`${prefix}_GY`]: zoneCards(p, "grave_arr", "GY"),
      [`${prefix}_banish`]: zoneCards(
        p, "banished_arr", "banish"
      ),
      [`${prefix}_field`]: field,
      [`${prefix}_field_spell`]: spellCard(p),

      [`${prefix}_cards_in_deck`]:
        Array.isArray(p.main_arr) ? p.main_arr.length : UNKNOWN,

      [`${prefix}_cards_in_extra_deck`]:
        Array.isArray(p.extra_arr) ? p.extra_arr.length : UNKNOWN,

      [`${prefix}_life`]:
        typeof p.lifepoints === "number"
          ? p.lifepoints : UNKNOWN,

      [`${prefix}_phase`]: UNKNOWN
    };
  }

  // Remove any previous Capture button
  document.getElementById("db-capture-button")?.remove();

  const button = document.createElement("button");
  button.id = "db-capture-button";
  button.textContent = "Capture state";

  button.style.cssText = `
    position: fixed;
    top: 12px;
    left: 12px;
    z-index: 2147483647;
    background: #16a34a;
    color: white;
    border: 2px solid white;
    border-radius: 8px;
    padding: 12px 16px;
    font: bold 16px Arial;
    cursor: pointer;
  `;

  button.onclick = () => {
    if (!window.player1 || !window.player2) {
      alert("Players not found. Select the replay frame.");
      return;
    }

    const state = {
      turn: UNKNOWN,
      ...playerState(window.player1, "me"),
      ...playerState(window.player2, "op")
    };

    console.log("Captured game state:", state);

    // Send the state back to the Python receiver
    location.href =
      "http://127.0.0.1:8765/capture#" +
      encodeURIComponent(JSON.stringify(state));
  };

  document.body.appendChild(button);

  console.log("Parser-format Capture state button installed.");
})();
