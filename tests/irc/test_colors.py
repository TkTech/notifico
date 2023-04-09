from notifico.util import irc


def test_stripping():
    """
    Ensure we strip mIRC color (and other controls) properly.
    """
    samples = [
        (
            "[\u000312haiku/haiku\u000f] \u000307waddlesplash\u000f pushed"
            " \u0003091\u000f commit to \u000309master\u000f [hrev56911] -"
            " https://git.haiku-os.org/haiku/log/?qt=range&q=2b65e2d808b3+"
            "%5E33dd436f25ae",
            "[haiku/haiku] waddlesplash pushed 1 commit to master [hrev56911]"
            " - https://git.haiku-os.org/haiku/log/?qt=range&q=2b65e2d808b3+"
            "%5E33dd436f25ae",
        ),
        (
            "\u0003[\u000302notifico\u0003] \u000307TkTech\u0003 pushed"
            " \u0003031\u0003 commit to \u000303logging\u0003 [+1/-0/±5]"
            " \u000313https:github.com/TkTech/notifico/compare/b4d631d2b74"
            "b66ef69183bf4\u0003",
            "[notifico] TkTech pushed 1 commit to logging [+1/-0/±5]"
            " https:github.com/TkTech/notifico/compare/b4d631d2b74b66ef69183bf"
            "4",
        ),
    ]

    for source, target in samples:
        assert irc.strip_mirc_colors(source) == target


def test_to_html():
    """
    Ensure we convert mIRC color codes to HTML properly.
    """
    samples = [
        (
            "[\u000312haiku/haiku\u000f] \u000307waddlesplash\u000f pushed"
            " \u0003091\u000f commit to \u000309master\u000f [hrev56911] -"
            " https://git.haiku-os.org/haiku/log/?qt=range&q=2b65e2d808b3+"
            "%5E33dd436f25ae",
            '[<span style="color: lightblue;">haiku/haiku</span>] <span'
            ' style="color: orange;">waddlesplash</span> pushed <span'
            ' style="color: lightgreen;">1</span> commit to <span style='
            '"color: lightgreen;">master</span> [hrev56911] - https://git.'
            "haiku-os.org/haiku/log/?qt=range&q=2b65e2d808b3+%5E33dd436f25ae",
        ),
        (
            "\u0003[\u000302notifico\u0003] \u000307TkTech\u0003 pushed"
            " \u0003031\u0003 commit to \u000303logging\u0003 [+1/-0/±5]"
            " \u000313https:github.com/TkTech/notifico/compare/b4d631d2b74"
            "b66ef69183bf4\u0003",
            '\u0003[<span style="color: #7FA5EB;">notifico</span>] <span '
            'style="color: orange;">TkTech</span> pushed <span style="color: '
            'green;">1</span> commit to <span style="color: '
            'green;">logging</span> [+1/-0/±5] <span style="color: '
            '#E36FB8;">https:github.com/TkTech/notifico/compare'
            "/b4d631d2b74b66ef69183bf4</span>",
        ),
    ]

    for source, target in samples:
        assert str(irc.to_html(source)) == target
