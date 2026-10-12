import copy
import sys
import unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/"src/python"))
from signal_control.protocol import FIELDS,encode_presence,decode_presence,parse_status
from signal_control.config import load_config,validate,ConfigurationError
from signal_control.roi import Detection,aggregate_presence,inside_polygon
from signal_control.transport import SerialTransport


class ProtocolTests(unittest.TestCase):
    def test_each_field_and_all_empty_roundtrip(self):
        for chosen in (None,*FIELDS):
            with self.subTest(field=chosen):
                values={field:field==chosen for field in FIELDS}
                packet=encode_presence(values)
                self.assertEqual(len(packet),24)
                self.assertEqual(decode_presence(packet),values)
                self.assertEqual(decode_presence(packet[:-1]+b'\r\n'),values)

    def test_strict_validation(self):
        good=encode_presence(dict.fromkeys(FIELDS,0))
        for bad in (good[:-1],good.replace(b'0',b'2',1),b'0,0\n',good[:-1]+b',0\n',b' '+good,good.replace(b',',b';',1)):
            with self.subTest(packet=bad):
                with self.assertRaises(ValueError):decode_presence(bad)
        values=dict.fromkeys(FIELDS,0);values[FIELDS[0]]=0.0
        with self.assertRaises(ValueError):encode_presence(values)

    def test_status_and_human_logs(self):
        self.assertEqual(parse_status(b'STATUS,3,RUNNING,FRESH,2,500\r\n').phase,3)
        for line in (b'3',b'I2C transmission success',b'ERROR,FRAME',b'STATUS,5,RUNNING,FRESH,0,0',b'STATUS,1,BAD,FRESH,0,0',b'\xff'):
            self.assertIsNone(parse_status(line))


class RoiTests(unittest.TestCase):
    def setUp(self):
        self.config=load_config(PROJECT/'src/config/signal.json')
        # Artificial class IDs and pedestrian polygon ONLY for unit tests.
        self.config['classes']={'vehicle_ids':[1000],'pedestrian_ids':[1001]}
        for field in FIELDS[8:]:self.config['roi'][field]=[]
        self.config['roi']['C_ped']=[[[1000,1000],[1010,1000],[1010,1010],[1000,1010]]]

    def test_vehicle_regions(self):
        for field in FIELDS[:8]:
            polygon=self.config['roi'][field][0]
            cx=sum(p[0] for p in polygon)/len(polygon);cy=sum(p[1] for p in polygon)/len(polygon)
            result=aggregate_presence([Detection(1000,cx,cy)]*10,self.config)
            self.assertTrue(result[field],field)
            self.assertEqual(sum(result.values()),1,field)

    def test_category_separation_and_pedestrian_changes(self):
        result=aggregate_presence([Detection(1001,1005,1005),Detection(1000,1005,1005)],self.config)
        self.assertTrue(result['C_ped']);self.assertEqual(sum(result.values()),1)
        self.assertFalse(any(aggregate_presence([],self.config).values()))
        self.assertFalse(any(aggregate_presence([Detection(999,1005,1005)],self.config).values()))

    def test_edges_and_nonfinite_coordinates(self):
        polygon=[[0,0],[10,0],[10,10],[0,10]]
        self.assertFalse(inside_polygon((0,5),polygon))
        self.assertFalse(inside_polygon((11,5),polygon))
        self.assertTrue(inside_polygon((5,5),polygon))
        self.assertFalse(any(aggregate_presence([Detection(1000,float('nan'),2)],self.config).values()))

    def test_vision_requires_existing_model_files(self):
        config=load_config(PROJECT/'src/config/signal.json')
        config['serial']['port']='MOCK'
        with self.assertRaisesRegex(ConfigurationError,'Missing required model files') as caught:validate(config,vision=True)
        self.assertIn('vision.weights',str(caught.exception))
        self.assertIn('vision.yolo_root',str(caught.exception))

    def test_imports_need_no_hardware_or_yolo(self):
        import importlib
        for name in ('detect','signal_control.vision','signal_control.mock'):
            importlib.import_module(name)
        self.assertNotIn('serial',sys.modules)
        self.assertNotIn('torch',sys.modules)
        self.assertNotIn('cv2',sys.modules)


class FakePort:
    def __init__(self):self.written=[];self.input=bytearray();self.fail=False;self.closed=False
    @property
    def in_waiting(self):return len(self.input)
    def write(self,data):
        if self.fail:raise OSError('test disconnect')
        self.written.append(data);return len(data)
    def read(self,size):data=bytes(self.input[:size]);del self.input[:size];return data
    def close(self):self.closed=True


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.now=0.0;self.ports=[];self.opens=0
        config=load_config(PROJECT/'src/config/signal.json')['serial']
        config['port']='MOCK';config['settle_seconds']=0
        def factory(*args,**kwargs):
            self.opens+=1;port=FakePort();self.ports.append(port);return port
        self.transport=SerialTransport(config,factory,clock=lambda:self.now,report=lambda _:None)
        self.presence=dict.fromkeys(FIELDS,False)

    def test_lazy_open_rate_limit_and_close(self):
        self.assertEqual(self.opens,0)
        self.assertTrue(self.transport.send(self.presence))
        self.assertFalse(self.transport.send(self.presence))
        self.now=0.5;self.assertTrue(self.transport.send(self.presence))
        self.assertEqual(len(self.ports[0].written),2)
        self.transport.close();self.assertTrue(self.ports[0].closed)

    def test_reconnect_after_error(self):
        self.transport.send(self.presence);self.ports[0].fail=True
        self.now=0.5;self.assertFalse(self.transport.send(self.presence))
        self.now=1;self.assertFalse(self.transport.send(self.presence))
        self.now=2.5;self.assertTrue(self.transport.send(self.presence));self.assertEqual(self.opens,2)

    def test_stale_detection_not_sent_as_empty(self):
        self.now=3;self.assertFalse(self.transport.send(self.presence,captured_at=0))
        self.assertEqual(self.opens,0)

    def test_fragmented_status_and_logs(self):
        self.transport.send(self.presence);port=self.ports[0]
        port.input.extend(b'ERROR,FRAME\nSTATUS,2,RUN');self.assertEqual(self.transport.poll(),[])
        port.input.extend(b'NING,FRESH,0,0\r\n');statuses=self.transport.poll()
        self.assertEqual(len(statuses),1);self.assertEqual(statuses[0].phase,2)


if __name__=='__main__':unittest.main()
