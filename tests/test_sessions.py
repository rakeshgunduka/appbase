# -*- coding: utf-8 -*-
import appbase.users.sessions as sessionslib


def test_sessions():
    uid, groups, k, v = 98765, ['admin', 'member'], 'foo', 'bar'
    sid = sessionslib.create(uid, groups)
    assert len(sid) == 43
    sid_new = sessionslib.create(uid, groups)
    assert sid == sid_new
    sessionslib.update(sid, {k: v})
    d = sessionslib.get(sid)
    assert d[k] == v
    sessionslib.remove_from_session(sid, k)
    d = sessionslib.get(sid)
    assert k not in d
    sessionslib.destroy(sid)
    assert sessionslib.get(sid) == {}


def test_session_lookups():
    uids = range(10000, 10010)
    groups = ['grp1', 'grp2']
    for uid in uids:
        sid = sessionslib.create(uid, groups)
        assert sessionslib.sid2uidgroups(sid) == (uid, groups)
        sessionslib.destroy(sid)
        assert sessionslib.get(sid) == {}
