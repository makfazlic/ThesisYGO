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

