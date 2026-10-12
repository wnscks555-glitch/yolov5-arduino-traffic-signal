import os
import sys
import unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src/python'))
from signal_control.mock import FirmwareHarness
from signal_control.protocol import FIELDS,encode_presence


class FirmwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('SIGNAL_NATIVE_AVAILABLE')=='0':raise unittest.SkipTest('Native build unavailable')

    def setUp(self):
        self.harness=FirmwareHarness(PROJECT/'build/firmware_harness.exe')
        self.addCleanup(self.harness.close)
        self.presence=dict.fromkeys(FIELDS,False)

    def frame(self,values=None):
        if values is not None:
            self.presence=dict.fromkeys(FIELDS,False);self.presence.update(values)
        return self.harness.command('FRAME,'+encode_presence(self.presence).hex())

    def advance(self,duration):
        while duration:
            self.frame()
            delta=min(duration,500)
            snapshot=self.harness.command(f'STEP,{delta}');duration-=delta
        return snapshot

    def settled(self):
        # The loop activates the newly selected phase on the next iteration.
        return self.harness.command('SNAPSHOT')

    def assert_lights(self,snapshot):
        phase=snapshot['phase'];yellow=snapshot['state']=='YELLOW'
        active={1:{0,1},2:{0,1},3:{2},4:{3}}[phase]
        for i in range(4):
            actual=tuple(snapshot['car_pins'][3*i:3*i+3])
            if i in active:
                expected=(0,1,0) if yellow else (1,int(phase!=1),0)
            else:expected=(0,0,1)
            self.assertEqual(actual,expected,(phase,i))
        allowed=set() if yellow else {1:{0,1},2:set(),3:{2},4:{3}}[phase]
        for i in range(4):
            self.assertEqual(tuple(snapshot['ped_pins'][2*i:2*i+2]),(int(i in allowed),int(i not in allowed)))
        self.assertEqual(snapshot['ped_phase'],0 if yellow else phase)

    def test_exact_two_second_wait_and_one_step(self):
        self.frame()
        before=self.advance(4999);self.assertEqual((before['phase'],before['state']),(1,'RUNNING'))
        start=self.advance(1);self.assertEqual((start['phase'],start['state']),(1,'YELLOW'));self.assert_lights(start)
        held=self.advance(1999);self.assertEqual((held['phase'],held['ped_phase']),(1,0));self.assert_lights(held)
        done=self.advance(1);self.assertEqual((done['phase'],done['state']),(2,'RUNNING'))
        self.assert_lights(self.settled())

    def test_all_four_phases_and_pedestrian_mapping(self):
        self.frame()
        for phase in (1,2,3,4):
            self.assert_lights(self.settled())
            yellow=self.advance(5000);self.assertEqual((yellow['phase'],yellow['state']),(phase,'YELLOW'));self.assert_lights(yellow)
            held=self.advance(1990);self.assertEqual((held['phase'],held['ped_phase']),(phase,0))
            self.advance(10)
            done=self.settled();self.assertEqual(done['phase'],phase%4+1);self.assert_lights(done)

    def test_new_phase_gets_full_five_second_count(self):
        self.frame();self.advance(7000)
        done=self.settled();self.assertEqual((done['phase'],done['ticks']),(2,0))
        held=self.advance(4999);self.assertEqual((held['state'],held['ticks']),('RUNNING',0))
        self.assertEqual(self.advance(1)['state'],'YELLOW')

    def test_serial_reception_continues_during_yellow(self):
        self.frame();self.advance(5000)
        snapshot=self.frame({'C_st':1})
        self.assertTrue(snapshot['presence'][5])
        self.assertEqual((snapshot['phase'],snapshot['state'],snapshot['ped_phase']),(1,'YELLOW',0))
        self.assertEqual(self.advance(1999)['phase'],1)
        self.advance(1);self.assertEqual(self.settled()['phase'],2)

    def test_each_phase_current_demand_preserved(self):
        fields={1:'B_st',2:'B_left',3:'C_st',4:'A_st'}
        self.frame()
        for phase in (1,2,3,4):
            self.frame({fields[phase]:1})
            held=self.advance(5000);self.assertEqual((held['phase'],held['state']),(phase,'RUNNING'));self.assert_lights(held)
            self.frame({});self.assertEqual(self.advance(5000)['state'],'YELLOW')
            self.advance(2000);self.settled()

    def test_pedestrian_demand_preserved(self):
        self.frame({'C_ped':1})
        self.assertEqual(self.advance(5000)['state'],'RUNNING')
        self.frame({});self.assertEqual(self.advance(5000)['state'],'YELLOW')

    def test_other_demand_and_maximum_conditions(self):
        self.frame({'B_st':1,'B_left':1})
        self.assertEqual(self.advance(14999)['state'],'RUNNING')
        self.assertEqual(self.advance(1)['state'],'YELLOW')

    def test_maximum_six_ticks(self):
        self.frame({'B_st':1})
        self.assertEqual(self.advance(29999)['state'],'RUNNING')
        self.assertEqual(self.advance(1)['state'],'YELLOW')
        self.advance(2000);self.assertEqual((self.settled()['phase']),2)

    def test_boolean_extension_keeps_existing_pedestrian_phase(self):
        self.assertEqual(self.harness.command('I2C,0300')['ped_phase'],3)
        self.assertEqual(self.harness.command('I2C,0401')['ped_phase'],3)
        zero=self.harness.command('I2C,0000')
        self.assertEqual(zero['ped_pins'],[0,1,0,1,0,1,0,1])

    def test_each_presence_field_matches_car_variable(self):
        for field in FIELDS:
            with self.subTest(field=field):
                snapshot=self.frame({field:1})
                self.assertEqual(snapshot['presence'],[name==field for name in FIELDS])


if __name__=='__main__':unittest.main()
