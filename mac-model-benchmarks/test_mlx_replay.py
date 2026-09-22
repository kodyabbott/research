import unittest
from mlx_replay import extract_answer


class ChannelParsingTests(unittest.TestCase):
    def test_only_final_channel_is_scored(self):
        raw='<|meta_sep|>analysis<|im_sep|>{"answer":999}<|im_end|><|im_start|>assistant<|meta_sep|>final<|im_sep|>{"answer":42}'
        result=extract_answer(raw,True)
        self.assertEqual(result['content'],'{"answer":42}')
        self.assertIn('999',result['thinking'])
        self.assertIsNone(result['parseError'])

    def test_missing_or_duplicate_final_fails_closed(self):
        self.assertIsNotNone(extract_answer('{"answer":42}',True)['parseError'])
        marker='<|meta_sep|>final<|im_sep|>'
        self.assertIsNotNone(extract_answer(marker+'one'+marker+'two',True)['parseError'])

    def test_plain_answer_is_not_cleaned_to_make_it_pass(self):
        raw='```json\n{"answer":42}\n```'
        self.assertEqual(extract_answer(raw,False)['content'],raw)
        self.assertTrue(extract_answer('<think>reason</think>answer',False)['unexpectedThinking'])


if __name__=='__main__':unittest.main()
