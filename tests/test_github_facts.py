from integrations.github_facts import GitHubFactStore

def test_github_store_is_disabled_without_transport():
    assert GitHubFactStore('owner', 'repo').get('facts/a') is None

def test_github_store_uses_mock_transport_without_credentials():
    calls = []
    def mock(path, token):
        calls.append((path, token)); return {'path': path, 'ok': True}
    store = GitHubFactStore('owner', 'repo', transport=mock)
    assert store.get('facts/a') == {'path': 'facts/a', 'ok': True}
    assert calls == [('facts/a', None)]
