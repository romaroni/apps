import base64
from datetime import datetime, timezone
import os
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import app


class DisplayTests(unittest.TestCase):
    def test_clock_dst_and_calendar(self):
        for hour, expected in [(5, '1:30 AM'), (6, '1:30 AM'), (7, '2:30 AM')]:
            output = app.clock_body(datetime(2026, 11, 1, hour, 30, tzinfo=timezone.utc))
            self.assertIn(expected, output)
            self.assertIn('Sunday, 1 November 2026', output)
            self.assertEqual(output.count('aria-current="date"'), 1)
        self.assertIn('29 February 2028', app.clock_body(datetime(2028, 2, 29, 17, tzinfo=timezone.utc)))

    def test_blocks_escape_and_nesting(self):
        output = app.render_blocks([
            {'type': 'bulleted_list_item', 'bulleted_list_item': {'rich_text': [{'plain_text': '<script>alert(1)</script>'}]},
             'children': [{'type': 'to_do', 'to_do': {'checked': True, 'rich_text': [{'plain_text': 'Done'}]}}]},
            {'type': 'heading_1', 'heading_1': {'rich_text': [{'plain_text': 'Clients'}]}}])
        self.assertIn('&lt;script&gt;', output)
        self.assertIn('&#9745;', output)
        self.assertIn('</ul><h2>Clients</h2>', output)

    def test_pagination(self):
        notion = app.Notion('fake', 'a' * 32)
        with patch.object(notion, 'get', side_effect=[
            {'results': [{'type': 'paragraph', 'id': 'one'}], 'has_more': True, 'next_cursor': 'next'},
            {'results': [{'type': 'paragraph', 'id': 'two'}], 'has_more': False},
        ]) as get:
            self.assertEqual(len(notion.blocks('a' * 32)), 2)
            self.assertIn('start_cursor=next', get.call_args.args[0])

    def test_http_protection_links_refresh_and_failure(self):
        env = {'DISPLAY_USER': 'juliana', 'DISPLAY_PASSWORD': 'test-password-123456789',
               'NOTION_TOKEN': 'fake-secret-notion', 'NOTION_PAGE_ID': 'a' * 32}
        with patch.dict(os.environ, env):
            server = app.create_server(('127.0.0.1', 0))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = 'http://127.0.0.1:%d' % server.server_port
        auth = 'Basic ' + base64.b64encode(b'juliana:test-password-123456789').decode()
        try:
            for path in ['/', '/clock', '/status', '/unknown']:
                with self.assertRaises(HTTPError) as error:
                    urlopen(url + path)
                self.assertEqual(error.exception.code, 401)
                error.exception.close()
            with urlopen(Request(url + '/clock', headers={'Authorization': auth})) as response:
                body = response.read().decode()
                self.assertIn('content="60"', body)
                self.assertIn('href="/status"', body)
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertNotIn('<script', body)
            with patch.object(server.notion, 'render', return_value='<h1>Client Status</h1>') as render:
                for _ in range(2):
                    with urlopen(Request(url + '/status', headers={'Authorization': auth})) as response:
                        body = response.read().decode()
                        self.assertIn('Client Status', body)
                        self.assertIn('content="180"', body)
                        self.assertIn('href="/clock"', body)
                        self.assertNotIn('fake-secret-notion', body)
                self.assertEqual(render.call_count, 1)
            server.fetched = float('-inf')
            with patch.object(server.notion, 'render', side_effect=RuntimeError('private detail')):
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(url + '/status', headers={'Authorization': auth}))
                self.assertEqual(error.exception.code, 503)
                body = error.exception.read().decode()
                self.assertIn('retry automatically', body)
                self.assertNotIn('private detail', body)
                error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
