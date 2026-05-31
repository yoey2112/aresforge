from aresforge.operator.example_source_patch import classify_example


def test_classify_example() -> None:
    assert classify_example()["local_only"] is True
