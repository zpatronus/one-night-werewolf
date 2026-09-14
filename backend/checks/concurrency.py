"""Standalone SQLite race checks; only uses a temporary database.

Run: backend/.venv/bin/python backend/checks/concurrency.py
"""
import sys, json, tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from django.conf import settings
with tempfile.TemporaryDirectory() as tmp:
    settings.configure(SECRET_KEY='tests', INSTALLED_APPS=['room'], USE_TZ=True,
        DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':tmp+'/test.sqlite3','OPTIONS':{'timeout':10}}})
    import django
    django.setup()
    from django.db import connection, connections
    from django.test import RequestFactory
    from room.models import Room, Player
    from room import views, game
    with connection.schema_editor() as schema:
        schema.create_model(Room); schema.create_model(Player)
    def call(fn, body, gate):
        try:
            gate.wait()
            request=RequestFactory().post('/',data=json.dumps(body),content_type='application/json')
            return json.loads(fn(request).content)
        finally:
            connections.close_all()
    def race(jobs):
        gate=Barrier(len(jobs))
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures=[pool.submit(call,fn,body,gate) for fn,body in jobs]
            return [f.result() for f in futures]
    for i in range(20):
        name=f'R{i}'
        r=Room.objects.create(roomid=name,board={'werewolf':1,'seer':1,'robber':1,'troublemaker':1,'villager':2})
        owner=Player.objects.create(room=r,userid='A',userpsw='pw')
        r.owner=owner;r.save()
        for uid in 'BC':Player.objects.create(room=r,userid=uid,userpsw='pw')
        auth={'roomid':name,'userid':'A','userpsw':'pw'}
        results=race([(views.start_game,auth),(views.join_room,{**auth,'userid':'D'})])
        r.refresh_from_db()
        if r.phase=='op':
            assert r.players.count()==3 and not r.players.filter(role=None).exists(), results
        else:
            assert r.players.count()==4 and any(x.get('error')=='bad_board' for x in results), results
        name=f'J{i}'
        r=Room.objects.create(roomid=name)
        auth={'roomid':name,'userid':'X','userpsw':'pw'}
        results=race([(views.join_room,auth),(views.join_room,auth)])
        assert all(x['ok'] for x in results) and r.players.count()==1, results
        name=f'C{i}'
        auth={'roomid':name,'userid':'X','userpsw':'pw'}
        results=race([(views.create_room,auth),(views.create_room,auth)])
        assert sum(x['ok'] for x in results)==1 and any(x.get('error')=='roomid_taken' for x in results), results
        name=f'F{i}'
        r=Room.objects.create(roomid=name)
        for j in range(9): Player.objects.create(room=r,userid=f'P{j}',userpsw='pw')
        auth={'roomid':name,'userid':'X','userpsw':'pw'}
        results=race([(views.join_room,auth),(views.join_room,{**auth,'userid':'Y'})])
        assert r.players.count()==10 and sum(x['ok'] for x in results)==1, results
        assert any(x.get('error')=='room_full' for x in results), results
    print('80 concurrent scenarios passed: join/start, duplicate joins, duplicate creates, capacity.')
