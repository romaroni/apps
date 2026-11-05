"""Generate reproducible HTML fixtures; contains fictional data only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import clock_body, document, render_blocks


def block(kind, text, **extra):
    return {'type': kind, kind: {'rich_text': [{'plain_text': text}], **extra}}


root = Path(__file__).parent
blocks = [
    block('callout', 'SAMPLE CONTENT — fictional names and tasks for layout validation.'),
    block('heading_1', 'Today'),
    block('to_do', 'Review the launch timeline for Cedar Studio', checked=False),
    block('to_do', 'Send the revised proposal to Northstar', checked=True),
    block('heading_1', 'In progress'),
    block('bulleted_list_item', 'Cedar Studio — brand direction review on Friday'),
    block('bulleted_list_item', 'Northstar — waiting for feedback on the first draft'),
    block('heading_1', 'Waiting on'),
    block('bulleted_list_item', 'Willow & Co. — approval of the updated project scope and the final delivery dates before scheduling the next production stage.'),
    block('heading_1', 'Notes'),
    block('paragraph', 'Keep the next steps clear. Update this page from the phone or Mac; the desk display refreshes automatically.'),
]
(root / 'status.html').write_text(document('Status — sample', '<h1>Status</h1>' + render_blocks(blocks), 180, 'clock.html', 'Clock'))
(root / 'clock.html').write_text(document('New York clock', clock_body(), 60, 'status.html', 'Status'))
print('Generated sample Status and current New York clock HTML.')
