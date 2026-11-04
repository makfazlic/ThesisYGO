# %%
import json, os, sys, re, copy
sys.path.append(os.path.abspath(".."))
from pathlib import Path

PROJECT_ROOT = Path.cwd().resolve()
if not (PROJECT_ROOT / "replay_manager").is_dir():
    PROJECT_ROOT = PROJECT_ROOT.parent
if not (PROJECT_ROOT / "replay_manager").is_dir():
    raise FileNotFoundError("Run this notebook from the project root or its parser directory.")

game_file_name = "42.json"
game_path = PROJECT_ROOT / "replay_manager" / "100_goat_games" / game_file_name
with game_path.open(encoding="utf-8") as file:
    game_log = json.load(file)
print(f"Game link: https://www.duelingbook.com/replay?id={game_log['id']}")


# %%
# Each parse_replay() call constructs a completely fresh game state.
# The old persistent_example/persistent_state dictionaries are no longer needed.


# %%
# Drop-in notebook replay parser. Standard library only.

class CardTracker:
    """Canonical card records; replay engine IDs are replaceable aliases."""

    def __init__(self, game):
        self.game = game
        self.players = {game[f'player{i}']['username']: f'p{i}' for i in (1, 2)}
        self.cards, self.aliases, self.locations = {}, {}, {}
        self.owners, self.origins, self.by_object = {}, {}, {}
        for i in (1, 2):
            owner = f'p{i}'
            for key, zone in (('main', 'deck'), ('extra', 'extra')):
                for handle in game[f'player{i}'].get(key, []):
                    if handle in self.owners and self.owners[handle] != owner:
                        raise ValueError(f'Initial engine handle {handle!r} has two owners')
                    self.owners[handle] = owner
                    self.origins[handle] = (owner, zone)

    def actor(self, play):
        return self.players.get(play.get('username'))

    def register(self, handle, payload, owner=None, *, token=False):
        payload = payload or {}
        owner = self.owners.get(handle, owner)
        uid = self.aliases.get(handle)
        oid = payload.get('object_id')
        name = payload.get('name')
        if uid is None and oid is not None and owner is not None:
            uid = self.by_object.get((owner, oid))
        if uid is None:
            if owner not in ('p1', 'p2'):
                raise ValueError(f'Unknown original owner for engine handle {handle!r}')
            uid = f'card_{len(self.cards) + 1}'
            self.cards[uid] = {
                'uid': uid, 'name': name, 'object_id': oid, 'owner': owner,
                'battle_position': None, 'face_up': None, 'is_token': token,
            }
            self.locations[uid] = self.origins.get(handle)
        card = self.cards[uid]
        if owner is not None and card['owner'] != owner:
            raise ValueError(f'Ownership conflict for {uid}: {card["owner"]} vs {owner}')
        for key, value in (('name', name), ('object_id', oid)):
            if value is not None and card.get(key) is not None and card[key] != value:
                raise ValueError(f'{key} conflict for engine handle {handle!r}: {card[key]!r} vs {value!r}')
            if value is not None:
                card[key] = value
        if oid is not None:
            self.by_object[(card['owner'], oid)] = uid
        if handle is not None:
            self.aliases[handle] = uid
            self.owners[handle] = card['owner']
        return uid

    def seed_pick_first(self, play):
        result = []
        cards = play.get('cards', [])
        for i in (1, 2):
            owner = f'p{i}'
            for handle, payload in zip(self.game[f'player{i}'].get('main', [])[:5], cards[(i-1)*5:i*5]):
                uid = self.register(handle, payload, owner)
                self.locations[uid] = (owner, 'hand')
                result.append((uid, owner))
        return result

    def observe(self, play, owner_hint=None):
        handle = play.get('id')
        payload = play.get('card') or {}
        if play.get('play') == 'Summon Token':
            return self.register(handle, {'name': payload.get('name', 'Token')}, self.actor(play), token=True)
        if play.get('play') == 'Add proxy':
            return self.register(handle, payload, self.actor(play))
        if payload:
            return self.register(handle, payload, owner_hint)
        return self.aliases.get(handle)

    def resolve(self, play, candidates=(), owner_hint=None, name=None):
        """Resolve an exact identity, or a unique compatible source candidate."""
        uid = self.observe(play, owner_hint)
        if uid is not None:
            if name and self.cards[uid].get('name') not in (None, name):
                raise ValueError(f'Event name {name!r} conflicts with {self.cards[uid]["name"]!r}')
            return uid
        payload = play.get('card') or {}
        oid = payload.get('object_id')
        name = payload.get('name') or name
        matches = [candidate for candidate in candidates
                   if (oid is None or self.cards[candidate].get('object_id') == oid)
                   and (name is None or self.cards[candidate].get('name') == name)]
        if len(matches) != 1:
            raise ValueError(f'Cannot uniquely identify {name!r}: {len(matches)} source candidates')
        uid = matches[0]
        handle = play.get('id')
        if handle is not None:
            self.aliases[handle] = uid
            self.owners[handle] = self.cards[uid]['owner']
        return uid

    def remap_hand(self, play):
        if 'prev' not in play or 'hand' not in play:
            return
        previous, current = play['prev'], play['hand']
        if len(previous) != len(current):
            raise ValueError('Hand alias remapping has unequal previous/current lengths')
        aliases = {new: self.aliases[old] for old, new in zip(previous, current) if old in self.aliases}
        owners = {new: self.owners[old] for old, new in zip(previous, current) if old in self.owners}
        origins = {new: self.origins[old] for old, new in zip(previous, current) if old in self.origins}
        for old in previous:
            self.aliases.pop(old, None)
            self.owners.pop(old, None)
            self.origins.pop(old, None)
        self.aliases.update(aliases)
        self.owners.update(owners)
        self.origins.update(origins)

    def shuffle_deck(self, play):
        owner = self.actor(play)
        if owner is None:
            raise ValueError('Deck shuffle has unknown player')
        # A deck shuffle exposes new handles, but no old-to-new permutation.
        for handle in list(set(self.origins) | set(self.aliases)):
            origin = self.origins.get(handle)
            uid = self.aliases.get(handle)
            location = self.locations.get(uid) if uid is not None else origin
            if location == (owner, 'deck'):
                self.aliases.pop(handle, None)
                self.owners.pop(handle, None)
                self.origins.pop(handle, None)
        for handle in play.get('deck', []):
            self.owners[handle] = owner
            self.origins[handle] = (owner, 'deck')


"""Normalize replay movement text without changing game state."""
import re

_METADATA = {
    'Pick first', 'Begin next duel', 'Admit defeat', 'Life points',
    'Enter DP', 'Enter SP', 'Enter M1', 'Enter BP', 'Enter M2', 'Enter EP',
    'Start turn', 'End turn', 'Good', 'Stop good', 'Shuffle hand', 'Shuffle deck',
    'RPS', 'Attack directly', 'View deck', 'Stop viewing', 'Declare', 'View GY',
    'View GY 2', 'Duel message', 'Attack', 'Edit stats', 'Thinking', 'View ED',
    'View ED 2', 'Target card', 'View Banished 2', 'Reveal', 'Done siding',
    'Add counter', 'Remove counter', 'View Banished', 'Siding', 'Add watcher',
    'Show hand', 'Left duel', 'Countdown', 'Rejoin duel', 'Resume game',
    'Quit duel', 'Remove watcher', 'Die', 'Coin', 'Watcher message', 'Call admin',
    'Cancel call', 'Pause game', 'Match loss', 'Offer draw', 'Accept draw', 'Back to RPS',
}
_ZONE = re.compile(r'[MS]2?-[1-5]$')

def log_text(play):
    log = play.get('log') or {}
    if not isinstance(log, dict):
        return ''
    return (log.get('private_log') or log.get('public_log') or '').strip()

def _location(text):
    text = re.sub(r'\s+\(\d+/\d+\)', '', text).strip()
    if _ZONE.fullmatch(text):
        return text
    result = {
        'hand': 'hand', 'GY': 'GY', 'Deck': 'deck', 'Extra Deck': 'extra',
        'Field Spell Zone': 'fieldspell', 'BANISH': 'banish', 'Banished': 'banish',
        'banished': 'banish', 'top of deck': 'deck', 'bottom of deck': 'deck',
    }.get(text)
    if result is None:
        raise ValueError(f'Unrecognized location: {text!r}')
    return result

def normalize(play):
    """Return a movement dict, None for known metadata, or raise on unknown text.

    `source` is relative to actor for field zones; exact identity may determine
    another player's GY/hand/banish pile. Destinations with `owner_` refer to the
    card's original owner, while `other_hand` means opponent of the actor.
    `position`/`face_up` are omitted when unchanged (e.g. Move), and may be None
    when explicitly cleared (e.g. a card returned to hand).
    """
    action = play['play']
    if action in _METADATA:
        return None
    text = log_text(play)
    result = {'operation': 'transfer'}
    named = re.search(r'"([^"]+)"', text)
    result['name'] = (named.group(1) if named else
                      (play.get('card') or {}).get('name'))
    face_down = bool(play.get('face_down')) or action == 'Banish FD'
    if text.endswith(' face-down'):
        face_down = True
        text = text[:-10].rstrip()
    text = re.sub(r'\s+\((ATK|DEF)\)$', '', text)

    if action == 'Draw card':
        return {**result, 'operation': 'draw', 'source': 'deck',
                'destination': 'hand', 'position': None, 'face_up': None}
    if action == 'Summon Token':
        zone = play.get('zone') or next(iter(re.findall(r'\b[MS]2?-[1-5]\b', text)), None)
        if not zone or not _ZONE.fullmatch(zone):
            raise ValueError(f'Cannot locate token summon: {text!r}')
        return {**result, 'operation': 'token', 'source': None,
                'destination': zone, 'position': None, 'face_up': True}
    if action == 'Remove Token':
        source = re.search(r'\sfrom\s+(.+)$', text)
        if not source:
            raise ValueError(f'Cannot locate removed token: {text!r}')
        return {**result, 'operation': 'remove_token',
                'source': _location(source.group(1)), 'destination': None}
    if action == 'Add proxy':
        if not text.startswith('Added ') or not text.endswith(' to Extra Deck'):
            raise ValueError(f'Unrecognized Add proxy: {text!r}')
        return {**result, 'operation': 'proxy', 'source': None,
                'destination': 'owner_extra', 'position': None, 'face_up': None}

    if action in ('Flip', 'Flip Summon', 'To ATK', 'To DEF'):
        zone_match = re.search(r'\sin\s+([MS]2?-[1-5])(?:\s+to\s+(?:ATK|DEF))?$', text)
        if not zone_match:
            raise ValueError(f'Missing in-place zone: {text!r}')
        zone = zone_match.group(1)
        return {**result, 'operation': 'update', 'source': zone,
                'destination': zone, 'face_up': True,
                'position': 'DEF' if action in ('Flip', 'To DEF') else 'ATK'}

    # All other supported actions name a source, an in-place zone, or banishment.
    tail = text[named.end():] if named else text
    source_match = re.search(r'\sfrom\s+(.+?)(?:\s+to\s+|$)', tail)
    source = (_location(source_match.group(1)) if source_match else
              'banish' if re.search(r'\bbanished\s+"', text) else None)
    in_match = re.search(r'\sin\s+(.+)$', tail)
    to_match = re.search(r'\sto\s+(.+)$', tail)
    inplace = _location(in_match.group(1)) if in_match else None
    destination = _location(to_match.group(1)) if to_match else None
    result['source'] = source
    result['destination'] = destination

    if action in ('Set ST', 'Set monster', 'Set Field Spell', 'Activate ST',
                  'Activate Field Spell', 'Normal Summon', 'To ST', 'SS ATK', 'SS DEF'):
        if action in ('Set Field Spell', 'Activate Field Spell'):
            result['destination'] = 'fieldspell'
        elif destination is None:
            result['destination'] = inplace
        if source is None:
            if inplace is None:
                raise ValueError(f'Missing source/in-place zone: {text!r}')
            result['source'] = inplace
            result['operation'] = 'update'
        if result['destination'] is None:
            raise ValueError(f'Missing destination: {text!r}')
        result['face_up'] = action not in ('Set ST', 'Set monster', 'Set Field Spell')
        result['position'] = ('DEF' if action in ('Set monster', 'SS DEF') else
                              'ATK' if action in ('Normal Summon', 'SS ATK') else None)
    elif action in ('Flip', 'Flip Summon', 'To ATK', 'To DEF'):
        # To ATK/DEF text ends in 'to ATK/DEF', which is not a location.
        if inplace is None:
            raise ValueError(f'Missing in-place zone: {text!r}')
        result.update(operation='update', source=inplace, destination=inplace,
                      face_up=True, position='DEF' if action in ('Flip', 'To DEF') else 'ATK')
    elif action == 'Move':
        if source is None or destination is None:
            raise ValueError(f'Unrecognized Move: {text!r}')
    elif action in ('To GY', 'To hand', 'To hand 2', 'To T Deck', 'To B Deck', 'To ED'):
        if source is None:
            raise ValueError(f'Missing source: {text!r}')
        target = {'To GY': 'owner_GY', 'To hand': 'owner_hand',
                  'To hand 2': 'other_hand', 'To T Deck': 'owner_deck',
                  'To B Deck': 'owner_deck', 'To ED': 'owner_extra'}[action]
        result.update(destination=target, position=None,
                      face_up=True if action == 'To GY' else None)
    elif action in ('Banish', 'Banish FD'):
        if source is None:
            raise ValueError(f'Missing banish source: {text!r}')
        result.update(destination='owner_banish', position=None, face_up=not face_down)
    elif action == 'Mill':
        # 'Milled "..." from top of deck' has no destination phrase.
        result.update(source='deck', destination='owner_GY', position=None, face_up=True)
    else:
        raise ValueError(f'Unsupported action: {action!r}')
    return result


import copy
import re

_UNCHANGED = object()

def get_log_text(play):
    log = play.get('log') or {}
    return (log.get('private_log') or log.get('public_log') or '').strip() if isinstance(log, dict) else ''


class ReplayParser:
    def __init__(self, game):
        self.game = game
        self.tracker = CardTracker(game)
        self.counts = {(f'p{i}', zone): game[f'player{i}'].get(key, 0)
                       for i in (1, 2) for zone, key in (('deck', 'main_total'), ('extra', 'extra_total'))}
        self.life = {'p1': 8000, 'p2': 8000}
        self.phases = {'p1': None, 'p2': None}
        self.turn = 1
        self.started = False

    def contents(self, side, zone):
        return [uid for uid, location in self.tracker.locations.items() if location == (side, zone)]

    @staticmethod
    def other(side):
        return 'p2' if side == 'p1' else 'p1'

    def address(self, zone, actor, owner=None):
        if zone.startswith('owner_'):
            return owner, zone[6:]
        if zone == 'other_hand':
            return self.other(actor), 'hand'
        if zone.startswith(('M2-', 'S2-')):
            return self.other(actor), zone.replace('2-', '-')
        return actor, zone

    def snapshot(self):
        state = {'turn': self.turn}
        for owner, prefix in (('p1', 'me'), ('p2', 'op')):
            def card_at(uid):
                return copy.deepcopy(self.tracker.cards[uid])
            for zone, key in (('hand', 'hand'), ('GY', 'GY'), ('banish', 'banish')):
                state[f'{prefix}_{key}'] = [card_at(uid) for uid in self.contents(owner, zone)]
            state[f'{prefix}_field'] = {
                zone: next((card_at(uid) for uid in self.contents(owner, zone)), None)
                for zone in [f'{kind}-{i}' for kind in ('M', 'S') for i in range(1, 6)]
            }
            state[f'{prefix}_field_spell'] = next((card_at(uid) for uid in self.contents(owner, 'fieldspell')), None)
            state[f'{prefix}_cards_in_deck'] = self.counts[(owner, 'deck')]
            state[f'{prefix}_cards_in_extra_deck'] = self.counts[(owner, 'extra')]
            state[f'{prefix}_life'] = self.life[owner]
            state[f'{prefix}_phase'] = self.phases[owner]
        return state

    def validate(self):
        occupied, identities = set(), set()
        for uid, location in self.tracker.locations.items():
            if location is None:
                continue
            owner, zone = location
            card = self.tracker.cards[uid]
            if card['owner'] not in ('p1', 'p2') or owner not in ('p1', 'p2'):
                raise ValueError(f'Unknown ownership/location for {uid}')
            if zone not in ('hand', 'GY', 'banish', 'deck', 'extra', 'fieldspell') and not re.fullmatch(r'[MS]-[1-5]', zone):
                raise ValueError(f'Unknown zone {location}')
            if zone == 'fieldspell' or re.fullmatch(r'[MS]-[1-5]', zone):
                if location in occupied:
                    raise ValueError(f'Two cards occupy {location}')
                occupied.add(location)
            if card['object_id'] is not None:
                identity = (card['owner'], card['object_id'])
                if identity in identities:
                    raise ValueError(f'Duplicate physical identity {identity}')
                identities.add(identity)
        for (side, zone), count in self.counts.items():
            if count < 0 or len(self.contents(side, zone)) > count:
                raise ValueError(f'Invalid {side} {zone} count: {count}')

    def transfer(self, uid, source, destination, *, face_up=_UNCHANGED, position=_UNCHANGED):
        actual = self.tracker.locations.get(uid)
        if actual != source:
            raise ValueError(f'{self.tracker.cards[uid]["name"]!r}: expected source {source}, found {actual}')
        slot = destination and (destination[1] == 'fieldspell' or re.fullmatch(r'[MS]-[1-5]', destination[1]))
        if slot and any(other != uid for other in self.contents(*destination)):
            raise ValueError(f'Occupied destination {destination}')
        if source != destination:
            if source and source[1] in ('deck', 'extra'):
                if self.counts[source] <= 0:
                    raise ValueError(f'Cannot remove a card from empty {source}')
                self.counts[source] -= 1
            if destination and destination[1] in ('deck', 'extra'):
                self.counts[destination] += 1
            self.tracker.locations[uid] = destination
        card = self.tracker.cards[uid]
        if destination is None or destination[1] in ('hand', 'GY', 'banish', 'deck', 'extra', 'fieldspell'):
            card['battle_position'] = None
        if face_up is not _UNCHANGED:
            card['face_up'] = face_up
        if position is not _UNCHANGED:
            card['battle_position'] = position

    def apply(self, play):
        kind = play['play']
        actor = self.tracker.actor(play)
        if kind == 'Pick first':
            if self.started:
                raise ValueError('A second opening hand requires a new duel parser')
            for uid, owner in self.tracker.seed_pick_first(play):
                self.counts[(owner, 'deck')] -= 1
            self.started = True
            return 'applied'
        if kind == 'Begin next duel':
            raise ValueError('Parse each duel separately; next-duel metadata has not been initialized')
        if kind == 'Shuffle deck':
            self.tracker.shuffle_deck(play)
            return 'metadata'
        operation = normalize(play)
        observed = self.tracker.observe(play)
        if operation is not None:
            source_zone, destination_zone = operation['source'], operation['destination']
            if actor is None:
                raise ValueError(f'Unknown actor for {kind}')
            if source_zone is None:
                candidates = []
            else:
                candidates = self.contents(*self.address(source_zone, actor))
                if source_zone in ('GY', 'banish'):
                    candidates += self.contents(self.other(actor), source_zone)
            uid = self.tracker.resolve(play, candidates, name=operation['name'])
            card = self.tracker.cards[uid]
            source = None if source_zone is None else self.address(source_zone, actor)
            actual = self.tracker.locations.get(uid)
            # GY/banish references can explicitly identify an opponent-owned card.
            if source_zone in ('GY', 'banish') and actual and actual[1] == source_zone:
                source = actual
            # Deck and Extra Deck always belong to the original owner.
            if source_zone in ('deck', 'extra'):
                source = (card['owner'], source_zone)
            destination = None if destination_zone is None else self.address(destination_zone, actor, card['owner'])
            if operation['operation'] == 'remove_token' and not card['is_token']:
                raise ValueError(f'Cannot remove non-token {uid} as a token')
            self.transfer(uid, source, destination, face_up=operation.get('face_up', _UNCHANGED), position=operation.get('position', _UNCHANGED))
            outcome = 'applied'
        elif kind == 'Life points':
            if actor is None:
                raise ValueError('Unknown player for life-point change')
            self.life[actor] += play['amount']
            outcome = 'applied'
        elif kind.startswith('Enter '):
            self.phases[actor] = kind[6:]
            outcome = 'applied'
        elif kind == 'Start turn':
            self.phases[actor] = 'DP'
            self.phases[self.other(actor)] = "Opponent's turn"
            outcome = 'applied'
        elif kind == 'End turn':
            self.turn += 1
            self.phases[actor] = "Opponent's turn"
            self.phases[self.other(actor)] = 'DP'
            outcome = 'applied'
        else:
            outcome = 'metadata' if observed is not None or 'prev' in play else 'ignored'
        self.tracker.remap_hand(play)
        return outcome


def parse_replay(game_log, *, stop_at_defeat=True):
    """Parse a fresh first-duel state; stop at the first invalid event.

    `state` is the post-action viewer state, `before_state` the pre-action state.
    No failed transition is presented as an applied state.
    """
    if not stop_at_defeat:
        raise ValueError('This replacement supports one duel per replay; use stop_at_defeat=True')
    parser = ReplayParser(game_log)
    pairs, diagnostics = [], []
    previous = parser.snapshot()
    complete, stopped_reason = True, 'end_of_replay'
    for number, play in enumerate(game_log['plays'], 1):
        try:
            outcome = parser.apply(play)
            parser.validate()
            state = parser.snapshot()
        except (ValueError, KeyError, TypeError, IndexError) as error:
            diagnostic = {'kind': 'error', 'play_number': number, 'action': play['play'],
                          'message': str(error), 'error': str(error), 'play': copy.deepcopy(play)}
            diagnostics.append(diagnostic)
            complete, stopped_reason = False, 'error'
            pairs.append({'before_state': previous, 'state': copy.deepcopy(previous),
                          'action': f'{play.get("username", "")}, {play["play"]} (ERROR)',
                          'status': 'error', 'play_number': number})
            break
        pairs.append({'before_state': previous, 'state': state,
                      'action': f'{play.get("username", "")}, {play["play"]} ({outcome.upper()})',
                      'status': outcome, 'play_number': number})
        previous = state
        if play['play'] == 'Admit defeat':
            stopped_reason = 'admit_defeat'
            break
    return {'pairs': pairs, 'diagnostics': diagnostics, 'complete': complete,
            'final_state': previous, 'stopped_reason': stopped_reason,
            'unprocessed_plays': len(game_log['plays']) - len(pairs)}


# %%
result = parse_replay(game_log)
STATE_ACTION_PAIRS = result["pairs"]
persistent_state = result["final_state"]
PARSER_DIAGNOSTICS = result["diagnostics"]

print(f"Completed selected duel: {result['complete']}; snapshots: {len(STATE_ACTION_PAIRS)}")
print(f"Stopped at: {result['stopped_reason']}; later plays: {result['unprocessed_plays']}")
for diagnostic in PARSER_DIAGNOSTICS:
    print(f"❌ Play {diagnostic['play_number']} [{diagnostic['action']}]: {diagnostic['message']}")

print(f"Final state: {json.dumps(persistent_state, indent=2)}")




