import json
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, RequestFactory
from django.utils import timezone

from . import game, views
from .models import Room, Player


class GameChecks(TestCase):
    # The test suite exercises production semantics: op -> reveal advances on
    # the timeout alone (the anti-cheat rule), never on the dev-only
    # "timeout + everyone operated" gate. Pin IS_DEV off so the local
    # is-dev-machine marker can't silently change test behavior.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._orig_isdev = views.IS_DEV
        views.IS_DEV = False

    @classmethod
    def tearDownClass(cls):
        views.IS_DEV = cls._orig_isdev
        super().tearDownClass()

    def setUp(self):
        self.factory = RequestFactory()
        self.room = Room.objects.create(roomid='Test', phase='op',
            board={'werewolf':1,'seer':1,'robber':1,'troublemaker':1,'villager':2}, center=['seer', 'robber', 'troublemaker'],
            op_start_time=timezone.now())
        self.players = [Player.objects.create(room=self.room, userid=uid, userpsw='pw',
            role=role, fake_role=None if role in game.REAL_DISPLAY or role == 'werewolf' else 'seer')
            for uid, role in zip('ABC', ['werewolf', 'villager', 'villager'])]
        self.room.owner = self.players[0]
        self.room.save()

    def call(self, endpoint, player=None, **extra):
        p = player or self.players[0]
        body = {'roomid': self.room.roomid, 'userid': p.userid, 'userpsw': 'pw', **extra}
        request = self.factory.post('/', data=json.dumps(body), content_type='application/json')
        return json.loads(endpoint(request).content)

    def expire(self):
        self.room.op_start_time = timezone.now() - views.OPS_DURATION - timedelta(seconds=1)
        self.room.save()

    def test_body_and_methods(self):
        for body in ('[]', 'null', '"text"', '123', '{'):
            response = views.create_room(self.factory.post('/', data=body, content_type='application/json'))
            self.assertEqual(json.loads(response.content)['error'], 'bad_request')
        self.assertEqual(json.loads(views.create_room(self.factory.get('/')).content)['error'], 'method_not_allowed')
        for field in ('roomid', 'userid', 'userpsw'):
            self.assertEqual(self.call(views.room_state, **{field: []})['error'], 'bad_request')

    def test_choice_validation(self):
        invalid = [None, [], {'type':'none'}, {'type':'robber','target':'B'},
                   {'type':'wolf','target':[]}, {'type':'wolf','target':'center_3'},
                   {'type':'wolf','target':'center_0','peek':'werewolf'}]
        for choice in invalid:
            self.assertEqual(self.call(views.night_action, choice=choice)['error'], 'bad_choice')
        self.assertTrue(self.call(views.night_action, choice={'type':'wolf','target':'center_0'})['ok'])

    def test_seer_requires_two_distinct_integer_indices(self):
        p = self.players[0]; p.role = p.fake_role = 'seer'; p.save()
        for picks in ([0], [0,0], [0,3], [-1,1], [True,1], [0,1,2], ['0',1]):
            self.assertEqual(self.call(views.night_action, choice={'type':'seer','center_picks':picks})['error'], 'bad_choice')
        self.assertEqual(self.call(views.night_action, choice={'type':'seer','target':'B','center_picks':[0,1]})['error'], 'bad_choice')
        self.assertTrue(self.call(views.night_action, choice={'type':'seer','center_picks':[0,2]})['ok'])

    def test_self_and_duplicate_targets_rejected(self):
        for role, choice in [('seer', {'target':'A'}), ('robber', {'target':'A'}),
                             ('troublemaker', {'target':'B','target2':'B'}),
                             ('troublemaker', {'target':'A','target2':'B'})]:
            self.assertFalse(game.valid_choice(role, 'A', 'ABC', dict(type=role, **choice)))

    def test_fake_action_does_not_swap_cards(self):
        p = self.players[1]; p.fake_role='robber'; p.save()
        self.assertTrue(self.call(views.night_action, p, choice={'type':'robber','target':'A'})['ok'])
        self.expire(); self.call(views.room_state)
        p.refresh_from_db()
        self.assertEqual(game.final_cards(self.room.players.all())[p.userid], 'villager')
        reveal = self.call(views.reveal, p)
        self.assertEqual((reveal['role'], reveal['info']), ('villager', {}))

    def test_no_early_finish(self):
        self.room.players.update(choice={"type": "wolf", "target": "center_0"})
        self.assertEqual(self.call(views.room_state)['phase'], 'op')

    def test_late_action_preserves_existing_choice(self):
        self.call(views.night_action, choice={'type':'wolf','target':'center_0'})
        self.expire()
        self.assertEqual(self.call(views.night_action, choice={'type':'wolf','target':'center_2'})['phase'], 'reveal')
        p=self.players[0]; p.refresh_from_db()
        self.assertEqual(p.choice['target'], 'center_0')
        self.assertEqual(self.call(views.night_action, choice={})['phase'], 'reveal')

    def test_bad_stored_choice_defaults_and_settles_once(self):
        p=self.players[0]; p.choice={'type':'robber','target':'B'}; p.save()
        self.expire()
        self.assertEqual(self.call(views.room_state)['phase'], 'reveal')
        p.refresh_from_db(); self.assertEqual(p.choice["type"], "wolf")
        first=p.choice.copy()
        self.call(views.room_state); p.refresh_from_db()
        self.assertEqual(p.choice, first)

    def test_seer_default_has_two_cards(self):
        p=self.players[0]; p.role=p.fake_role='seer'; p.save()
        self.expire(); self.call(views.room_state); p.refresh_from_db()
        self.assertEqual(len(set(p.choice['center_picks'])), 2)
        self.assertEqual(len(self.call(views.reveal)['info']['peeked']), 2)

    def test_robber_memory_precedes_troublemaker(self):
        for p, role, choice in zip(self.players, ['robber','troublemaker','werewolf'],
            [{'type':'robber','target':'C'}, {'type':'troublemaker','target':'A','target2':'C'}, {'type':'wolf','target':'center_0'}]):
            p.role=p.fake_role=role; p.choice=choice; p.save()
        self.expire(); self.call(views.room_state)
        p=self.players[0]; p.refresh_from_db()
        self.assertEqual(self.call(views.reveal)['info']['new_role'], 'werewolf')
        self.assertEqual(game.final_cards(self.room.players.all())[p.userid], 'robber')
        self.assertNotIn('final_role', self.call(views.reveal)['info'])

    def test_votes_no_self_and_only_once(self):
        self.room.phase='reveal'; self.room.save()
        self.assertEqual(self.call(views.vote, target='A')['error'], 'bad_target')
        self.assertTrue(self.call(views.vote, target='')['ok'])
        self.assertEqual(self.call(views.vote, target='B')['error'], 'already_voted')
        self.call(views.vote, self.players[1], target='A')
        self.assertEqual(self.call(views.vote, self.players[2], target='A')['phase'], 'result')

    def test_result_only_exposes_raw_facts_after_voting(self):
        self.assertEqual(self.call(views.result)['error'], 'not_done')
        self.expire(); self.call(views.room_state)
        for p in self.players:
            self.call(views.vote, p, target='')
        result = self.call(views.result)
        self.assertEqual(set(result), {'ok', 'phase', 'center', 'players'})
        self.assertEqual(set(result['players'][0]), {'userid', 'avatar', 'role', 'choice', 'vote_target'})
        self.assertEqual(result['players'][0]['vote_target'], '')
        for p in result['players']:
            self.assertNotIn('peeked', p['choice'])
            self.assertNotIn('teammates', p['choice'])
            self.assertNotIn('new_role', p['choice'])

    def test_insomniac_derives_final_card_without_persisting_it(self):
        for p, role, choice in zip(self.players, ['robber','insomniac','werewolf'],
                [{'type':'robber','target':'B'}, {'type':'seer','center_picks':[0,1]}, {'type':'wolf','target':'center_0'}]):
            p.role=role; p.fake_role=None if role in game.REAL_DISPLAY or role == 'werewolf' else 'seer'
            p.choice=choice; p.save()
        self.expire(); self.call(views.room_state)
        reveal=self.call(views.reveal, self.players[1])
        self.assertEqual(reveal['info'], {'final_role':'robber'})
        self.assertNotIn('final_role', {f.name for f in Player._meta.fields})

    def test_board_validation(self):
        self.room.phase='waiting'; self.room.save()
        for board in ({'villager':True}, {'villager':-1}, {'unknown':1}, {'seer':1.5}):
            self.assertEqual(self.call(views.set_board, board=board)['error'], 'bad_board')
        self.assertTrue(self.call(views.set_board, board={'villager':2})['ok'])
        self.assertEqual(self.call(views.start_game)['error'], 'bad_board')
        self.assertFalse(game.validate_board({'villager':5,'seer':True},3))

    def test_start_recounts_after_lock(self):
        self.room.phase='waiting'; self.room.save()
        original=views._lock_room
        def joined(room):
            original(room)
            Player.objects.create(room=room, userid='D', userpsw='pw')
        with patch.object(views, '_lock_room', side_effect=joined):
            self.assertEqual(self.call(views.start_game)['error'], 'bad_board')
        self.room.refresh_from_db(); self.assertEqual(self.room.phase, 'waiting')

    def test_join_rechecks_phase_and_preserves_avatar(self):
        result=self.call(views.join_room, userid='D', avatar='../../bad')
        self.assertEqual(result['error'], 'room_started')
        self.room.phase='waiting'; self.room.save()
        result=self.call(views.join_room, userid='D', avatar=[])
        self.assertIn(result['avatar'], views.AVATARS)
        self.assertEqual(self.call(views.join_room, userid='D', avatar='bad')['avatar'], result['avatar'])

    def test_wolf_and_seer_share_ordered_center_positions(self):
        self.room.center = ['robber', 'minion', 'troublemaker']
        self.room.save()
        seer = self.players[1]; seer.role='seer'; seer.fake_role=None; seer.save()
        self.call(views.night_action, choice={'type':'wolf','target':'center_1'})
        self.call(views.night_action, seer, choice={'type':'seer','center_picks':[1,2]})
        self.expire(); self.call(views.room_state)
        wolf_info = self.call(views.reveal)['info']
        seer_info = self.call(views.reveal, seer)['info']
        self.assertEqual(wolf_info['peek'], 'minion')
        self.assertEqual(wolf_info['peek'], seer_info['peeked'][0])
        self.assertEqual(seer_info['peeked'][1], 'troublemaker')
        self.room.refresh_from_db()
        self.assertEqual(self.room.center, ['robber','minion','troublemaker'])


    def test_new_room_has_fixed_default_board(self):
        response = self.call(views.create_room, roomid='New')
        self.assertTrue(response['ok'])
        board = Room.objects.get(roomid='New').board
        self.assertEqual(board, dict(werewolf=2, villager=2, minion=1,
            seer=1, robber=1, troublemaker=1, insomniac=1))

    def test_full_room_rejects_new_players_but_allows_login(self):
        self.room.phase='waiting'; self.room.save()
        for i in range(7):
            Player.objects.create(room=self.room, userid=f'P{i}', userpsw='pw')
        self.assertEqual(self.call(views.join_room, userid='Extra')['error'], 'room_full')
        self.assertEqual(self.room.players.count(), 10)
        self.assertTrue(self.call(views.join_room)['ok'])

    def test_pack_wolves_get_template_decoys_with_no_real_effect(self):
        self.room.board = {'werewolf':2, 'seer':1, 'villager':3}
        self.room.save()
        def shuffle(bag):
            bag[:] = ['villager','villager','seer','werewolf','werewolf','villager']
        with patch.object(game.random, 'shuffle', side_effect=shuffle), patch.object(game.random, 'choice', return_value='seer') as choose:
            game.deal(self.room)
        self.assertEqual(choose.call_count, 3)
        self.assertEqual(set(choose.call_args.args[0]), {'seer','werewolf'})
        self.expire(); self.call(views.room_state)
        for p in self.players[:2]:
            p.refresh_from_db()
            self.assertEqual(p.fake_role, 'seer')
            result = self.call(views.reveal, p)
            self.assertTrue(result['action_was_fake'])
            self.assertEqual(result['role'], 'werewolf')
            self.assertEqual(result['info'], {'teammates': ['B' if p.userid == 'A' else 'A']})
        self.assertEqual(game.final_cards(self.room.players.all()), {'A':'werewolf','B':'werewolf','C':'villager'})

    def test_lone_wolf_and_active_roles_keep_real_operations(self):
        self.room.board = {'werewolf':2, 'seer':1, 'robber':1, 'villager':2}
        self.room.save()
        def shuffle(bag):
            bag[:] = ['werewolf','villager','villager','werewolf','seer','robber']
        with patch.object(game.random, 'shuffle', side_effect=shuffle):
            game.deal(self.room)
        for p in self.room.players.all():
            self.assertIsNone(p.fake_role)
            self.assertEqual(p.display_role, p.role)
        self.expire(); self.call(views.room_state)
        result = self.call(views.reveal)
        self.assertFalse(result['action_was_fake'])
        self.assertIn('peek', result['info'])

    def test_decoy_pool_uses_operable_template_roles(self):
        self.assertEqual(game.fake_pool({'werewolf':5,'robber':1,'minion':1}), ['robber','werewolf'])
        self.assertEqual(game.fake_pool({'seer':1,'villager':5}), ['seer'])
        self.assertEqual(game.fake_pool({'villager':6}), game.FAKE_POOL)
