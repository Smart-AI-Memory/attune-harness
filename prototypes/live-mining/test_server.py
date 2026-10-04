import copy,json,tempfile,unittest
from unittest.mock import patch
from server import Service,validate
ITEM={'kind':'opportunity','title':'Visible discoveries','proposal':'Show a review list','rationale':'People need to select work','quote':'Keep discoveries visible','draft_goal':'Review discoveries','draft_scope':'A local list','draft_done':'Pick a supported item'}
class Checks(unittest.TestCase):
 def test_exact_evidence(self):
  result={'summary':'Useful direction','items':[ITEM]}
  self.assertEqual(validate(result,'Keep discoveries visible'),result)
  altered=copy.deepcopy(result);altered['items'][0]['quote']='Invented evidence'
  with self.assertRaisesRegex(ValueError,'not present'):validate(altered,'Keep discoveries visible')
 def test_empty_result(self):
  self.assertEqual(validate({'summary':'No supported findings','items':[]},'Unrelated text')['items'],[])
 def test_missing_draft(self):
  result={'summary':'Draft','items':[dict(ITEM,draft_goal='')]}
  with self.assertRaisesRegex(ValueError,'incomplete'):validate(result,'Keep discoveries visible')
 def test_one_attempt_no_implicit_retry(self):
  with tempfile.TemporaryDirectory() as path:
   app=Service(path)
   with patch('server.threading.Thread') as worker:
    app.run('Keep discoveries visible')
    with self.assertRaises(RuntimeError):app.run('Second request')
    self.assertEqual(worker.call_count,1)
 def test_restart_preserves_attempt_limit(self):
  from pathlib import Path
  with tempfile.TemporaryDirectory() as path:
   (Path(path)/'request.json').write_text('{}')
   app=Service(path)
   self.assertEqual(app.state['phase'],'failed')
   with self.assertRaises(RuntimeError):app.run('Keep discoveries visible')
 def test_bad_input_does_not_consume_attempt(self):
  with tempfile.TemporaryDirectory() as path:
   app=Service(path)
   for text in ['', 'x'*6001, None]:
    with self.assertRaises(ValueError):app.run(text)
   self.assertEqual(app.state['attempts'],0)
if __name__=='__main__':unittest.main()
