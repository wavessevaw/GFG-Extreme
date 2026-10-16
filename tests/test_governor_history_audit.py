import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from governor_history_audit import run,analyze


class HistoricalAuditTests(unittest.TestCase):
    def test_duplicate_bytes_are_collapsed_without_conflating_same_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'inputs';root.mkdir();out=Path(tmp)/'out'
            def archive(value):
                b=io.BytesIO()
                with zipfile.ZipFile(b,'w') as z:z.writestr('timeline.jsonl',json.dumps({'t':1,'real':value,'output':90}))
                return b.getvalue()
            first=archive(30)
            (root/'a.zip').write_bytes(first);(root/'alias.zip').write_bytes(first)
            (root/'b.zip').write_bytes(archive(45))
            r=run([root],out)
            self.assertEqual(r['unique_archives'],2)
            self.assertEqual(r['unique_contents'],2)
            self.assertEqual(sum('duplicate_of' in x for x in r['sources']),1)

    def test_unknown_telemetry_remains_unknown_and_bad_rows_are_retained(self):
        a=analyze(b'{"t":1,"real":30,"output":90}\ntruncated {\n','x.jsonl')
        self.assertEqual(a['parse_error_lines'],[2]);self.assertNotIn('tdp',a['fields'])
        self.assertIsNone(a['metrics']['mean_draw_w'])
        self.assertFalse(a['anomalies'])

    def test_anomaly_is_an_observation_with_original_line_references(self):
        data='\n'.join(json.dumps(x) for x in [
            {'t':1,'real':30,'output':90,'tdp':10,'target':90},
            {'t':2,'real':30,'output':90,'tdp':7,'target':90},
            {'t':4,'real':15,'output':45,'tdp':7,'target':90}])
        a=analyze(data.encode(),'timeline.jsonl');f=a['anomalies'][0]
        self.assertEqual((f['start_line'],f['end_line']),(2,3))
        self.assertFalse(f['root_cause_confirmed'])


if __name__=='__main__':unittest.main()
