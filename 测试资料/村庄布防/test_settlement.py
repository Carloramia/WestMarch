from copy import deepcopy
from settlement import Settlement
from campaign import prepare, player_frame
from simulate import STOCK, field


def reach_raid(settlement, units):
    for _ in range(12):
        encounter = settlement.advance(units)
        if encounter:
            return encounter
    raise AssertionError('raid did not arrive')


def test_production_and_training():
    village = Settlement('stock', 7)
    units = deepcopy(village.map['units'])
    yard = next(site for site in village.sites if site['id']=='GWmaterials')
    village.queue('D0','scout')
    village.queue('GN','tower')
    village.advance(units)
    village.advance(units)
    assert village.resources=={'materials':4,'supplies':5}
    assert not village.skills['D0']
    units[0]['pos']=yard['pos']
    village.advance(units)
    village.advance(units)
    assert village.skills['D0']==['scout']
    assert village.resources['materials']==6
    village.advance(units)
    assert village.upgrades['GN']==['tower']
    village.economy([tuple(yard['pos'])],[tuple(yard['pos'])])
    assert yard['status']=='争夺中'
    assert village.resources['materials']==6


def test_persistence_and_raid_clock():
    village=Settlement('gate', 13)
    units=deepcopy(village.map['units'])
    while village.clock+1<village.next_raid:
        assert village.advance(units) is None
    village.queue('D0','guard')
    battle,_=reach_raid(village,units)
    assert village.phase=='conflict' and battle.history[-1]['round']==0
    gate=battle.structures[0]
    gate['hp']=0
    battle.sync_gate_blocks()
    battle.byid['D0'].wound=2
    battle.record('heal','test',actor='D1')
    village.step(battle,1)
    assert village.phase=='safe' and village.gate_hp[gate['id']]==0
    assert village.jobs[0]['left']==3 and village.jobs[0]['paused']
    assert village.xp['D0']==0 and village.xp['D1']==2
    village.queue(gate['id'],'repair')
    for _ in range(3):
        assert village.advance(units) is None
    assert village.gate_hp[gate['id']]==8
    assert village.skills['D0']==['guard']
    battle,_=reach_raid(village,units)
    assert battle.structures[0]['hp']==8 and list(battle.byid['D0'].skills)==['guard']
    village.step(battle,1)
    battle,_=reach_raid(village,units)
    assert battle.byid['D1'].veteran==1 and battle.byid['D1'].morale_threshold==4
    village.step(battle,1)
    assert village.phase=='won'


def test_invalid_deployment_does_not_advance_time():
    village=Settlement('split', 101)
    units=deepcopy(village.map['units'])
    units[0]['pos']=units[1]['pos']
    rng=village.rng.getstate()
    try:
        village.advance(units)
    except ValueError:
        assert village.clock==0 and village.rng.getstate()==rng
    else:
        raise AssertionError('overlap accepted')


def test_regional_map_and_local_reports():
    for level in ('gate','split','stock'):
        village=Settlement(level, 7)
        units=deepcopy(village.map['units'])
        east=next(site for site in village.sites if site['id']=='eastworks')
        units[0]['pos']=east['pos']
        assert village.public()['safe_left']==5
        battle,_=reach_raid(village,units)
        assert (battle.width,battle.height)==(44,34)
        assert battle.byid['D0'].pos==tuple(east['pos'])
        assert tuple(east['pos']) in field((43,12),battle.blocked)
        assert (44,12) not in field((43,12),battle.blocked)
        assert (37,25) in field((43,12),battle.blocked)
        assert not player_frame(battle.history[-1])['intel']['D']
        village.economy([], [tuple(east['pos'])], battle)
        frame=player_frame(battle.step())
        assert any(e['kind']=='site_contested' and e['pos']==east['pos'] and 'actor' not in e for e in frame['events'])
        normal,_=prepare({'level':level,'units':village.map['units']},7)
        assert (36,12) not in field(STOCK,normal.blocked)


if __name__=='__main__':
    test_production_and_training()
    test_persistence_and_raid_clock()
    test_invalid_deployment_does_not_advance_time()
    test_regional_map_and_local_reports()
    print('PASS settlement production, exposure, training, damage, repair, experience and three-raid settlement')
