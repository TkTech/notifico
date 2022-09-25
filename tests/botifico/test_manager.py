from notifico.botifico.manager import Manager, Plugin


def test_plugin_event_registration():
    """
    Test registering events on a plugin works.
    """
    plugin = Plugin()

    @plugin.on('test')
    def on_test():
        pass

    assert on_test in plugin.event_receivers['test']

    # Ensure merging a plugin with the manager works.
    manager = Manager('botifico')
    manager.register_plugin(plugin)

    assert on_test in manager.event_receivers['test']
