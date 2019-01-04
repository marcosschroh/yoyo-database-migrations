from yoyo import utils


class TestChangeParamStyle:
    def test_changes_to_qmark(self):
        sql = "SELECT :a, :b, :a"
        assert utils.change_param_style("qmark", sql, {"a": 1, "b": 2}) == (
            "SELECT ?, ?, ?",
            (1, 2, 1),
        )

    def test_changes_to_numeric(self):
        sql = "SELECT :a, :b, :a"
        assert utils.change_param_style("numeric", sql, {"a": 1, "b": 2}) == (
            "SELECT :1, :2, :3",
            (1, 2, 1),
        )

    def test_changes_to_format(self):
        sql = "SELECT :a, :b, :a"
        assert utils.change_param_style("format", sql, {"a": 1, "b": 2}) == (
            "SELECT %s, %s, %s",
            (1, 2, 1),
        )

    def test_changes_to_pyformat(self):
        sql = "SELECT :a, :b, :a"
        assert utils.change_param_style("pyformat", sql, {"a": 1, "b": 2}) == (
            "SELECT %(a)s, %(b)s, %(a)s",
            {"a": 1, "b": 2},
        )

    def test_changes_to_named(self):
        sql = "SELECT :a, :b, :a"
        assert utils.change_param_style("named", sql, {"a": 1, "b": 2}) == (
            "SELECT :a, :b, :a",
            {"a": 1, "b": 2},
        )
