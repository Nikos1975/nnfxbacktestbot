from pathlib import Path

from nnfx_crypto.tools.mql4_scaffold import parse_mql4_source, render_indicator_scaffold


def test_parse_mql4_source_extracts_inputs_and_buffers(tmp_path: Path):
    source = tmp_path / "Example.mq4"
    source.write_text(
        """
#property indicator_buffers 2
input int Period1 = 100; // Period 1
extern double Threshold = 50.0;
double MainBuffer[];
double SignalBuffer[];
""",
        encoding="utf-8",
    )

    meta = parse_mql4_source(source)

    assert meta.name == "Example"
    assert meta.indicator_buffers == 2
    assert meta.inputs["Period1"] == "100"
    assert meta.inputs["Threshold"] == "50.0"
    assert meta.buffers == ["MainBuffer", "SignalBuffer"]


def test_render_indicator_scaffold_marks_manual_translation_required(tmp_path: Path):
    source = tmp_path / "Example.mq4"
    source.write_text("input int Period1 = 100;\ndouble MainBuffer[];\n", encoding="utf-8")
    meta = parse_mql4_source(source)

    rendered = render_indicator_scaffold(meta, class_name="ExampleIndicator", signal_column="example_signal")

    assert "class ExampleIndicator" in rendered
    assert "Manual formula translation required" in rendered
    assert "example_signal" in rendered
