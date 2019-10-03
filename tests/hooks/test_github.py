import textwrap
from notifico.services.hooks import github
from notifico.services.hooks import HookService


test_push_payload = {
    'commits': [{
        'id': '0123456789abcdef',
        'sha': '0123456789abcdef',
        'url': 'https://github.com/test/test',
        'distinct': True,
        'committer': {
            'name': 'Test Committer',
            'email': 'committer@example.com'
        },
        'author': {
            'name': 'Test Author',
            'email': 'author@example.com'
        },
        'message': textwrap.dedent("""\
            This is a summary of my changes.

            This is a really really long description that no one
            cares about too much, hopefully it will get truncated
            so notifico doesn't spam the channel with a few dozen lines
            of text.
        """) + (100 * "Spam spam spam spam!\n")
    }]
}


def test_create_commit_summary_title_only():
    config = {
        'title_only': True
    }
    summary_generator = github._create_commit_summary(
        'test/project', {'original': test_push_payload}, config
    )
    # Strip out the colors, we only care about the content of the message.
    summary_lines = [HookService.strip_colors(l) for l in summary_generator]
    # Make sure only the title made it
    assert summary_lines == [
        '[test/project] Test Author 0123456 - This is a summary of my changes.'
    ]


def test_create_commit_summary_really_long_message():
    config = {
        'title_only': False
    }
    summary_generator = github._create_commit_summary(
        'test/project', {'original': test_push_payload}, config
    )
    # Strip out the colors, we only care about the content of the message.
    summary_lines = [HookService.strip_colors(l) for l in summary_generator]

    # Make sure the commit message was truncated to 1000 characters
    truncated_message = test_push_payload['commits'][0]['message'][:1000]
    assert summary_lines == [
        '[test/project] Test Author 0123456 - {}...'.format(truncated_message)
    ]
