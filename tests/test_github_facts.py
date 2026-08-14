from integrations.github_facts import GitHubFactStore


def test_github_store_is_disabled_without_transport(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert GitHubFactStore.from_environment("owner", "repo").get("facts/a") is None


def test_github_store_uses_mock_transport_without_credentials():
    calls = []

    def mock(path, token):
        calls.append((path, token))
        return {"path": path, "ok": True}

    store = GitHubFactStore("owner", "repo", transport=mock)
    assert store.get("facts/a") == {"path": "facts/a", "ok": True}
    assert calls == [("facts/a", None)]


def test_environment_token_enables_http_transport(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    store = GitHubFactStore.from_environment("owner", "repo")
    assert store.enabled and store.token == "test-token"


def test_repository_traversal_is_rejected():
    store = GitHubFactStore("owner", "repo", transport=lambda p, t: {})
    try:
        store.get("facts/../secret")
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal was accepted")
