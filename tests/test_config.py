import pytest

from watchpost.config import ConfigError, load_config


def write_config(tmp_path, content):
    p = tmp_path / "config.yaml"
    p.write_text(content)
    return p


def test_loads_minimal_config(tmp_path):
    path = write_config(tmp_path, """
endpoints:
  - name: test-api
    url: https://example.com
""")
    endpoints = load_config(path)
    assert len(endpoints) == 1
    ep = endpoints[0]
    assert ep.name == "test-api"
    assert ep.url == "https://example.com"
    # defaults
    assert ep.method == "GET"
    assert ep.expected_status == 200
    assert ep.timeout == 5.0
    assert ep.interval == 60
    assert ep.latency_threshold_ms is None


def test_overrides_defaults(tmp_path):
    path = write_config(tmp_path, """
endpoints:
  - name: slow-api
    url: https://example.com/slow
    expected_status: 204
    timeout: 15
    interval: 300
    latency_threshold_ms: 2000
""")
    ep = load_config(path)[0]
    assert ep.expected_status == 204
    assert ep.timeout == 15
    assert ep.interval == 300
    assert ep.latency_threshold_ms == 2000


def test_name_defaults_to_url(tmp_path):
    path = write_config(tmp_path, """
endpoints:
  - url: https://example.com/no-name
""")
    ep = load_config(path)[0]
    assert ep.name == "https://example.com/no-name"


def test_multiple_endpoints(tmp_path):
    path = write_config(tmp_path, """
endpoints:
  - name: a
    url: https://example.com/a
  - name: b
    url: https://example.com/b
""")
    endpoints = load_config(path)
    assert [e.name for e in endpoints] == ["a", "b"]


def test_missing_url_raises(tmp_path):
    path = write_config(tmp_path, """
endpoints:
  - name: broken
""")
    with pytest.raises(ConfigError, match="missing 'url'"):
        load_config(path)


def test_duplicate_names_raise(tmp_path):
    path = write_config(tmp_path, """
endpoints:
  - name: dupe
    url: https://example.com/a
  - name: dupe
    url: https://example.com/b
""")
    with pytest.raises(ConfigError, match="duplicate"):
        load_config(path)


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_empty_endpoints_key_raises(tmp_path):
    path = write_config(tmp_path, "endpoints:\n")
    with pytest.raises(ConfigError, match="no 'endpoints'"):
        load_config(path)


def test_no_endpoints_key_at_all_raises(tmp_path):
    path = write_config(tmp_path, "something_else: true\n")
    with pytest.raises(ConfigError, match="no 'endpoints'"):
        load_config(path)
