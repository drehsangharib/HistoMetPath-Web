import pandas as pd
from PIL import Image

from histometpath_web.model_diagnostics import (
    append_diagnostic_columns, duplicate_summary, image_morphology_metrics,
    model_contract_receipt, score_diagnostics, threshold_distance_band,
)


def test_score_diagnostics_saturation_and_near_threshold():
    frame = pd.DataFrame({'score': [0.99, 0.96, 0.51, 0.10]})
    result = score_diagnostics(frame)
    assert result['valid_scores'] == 4
    assert result['fraction_at_least_0_95'] == 0.5
    assert result['fraction_at_least_0_99'] == 0.25
    assert result['near_threshold_fraction'] == 0.25
    assert result['saturation_warning'] is True


def test_empty_scores_are_safe():
    result = score_diagnostics(pd.DataFrame({'score': [None]}))
    assert result['valid_scores'] == 0
    assert result['fraction_at_least_0_99'] is None


def test_duplicate_summary_counts_extra_records():
    result = duplicate_summary(pd.DataFrame({'image_sha256': ['a', 'a', 'a', 'b']}))
    assert result == {'unique_hashes': 2, 'duplicate_records': 2, 'duplicate_groups': 1}


def test_threshold_distance_bands():
    assert threshold_distance_band(0.51) == 'near_threshold'
    assert threshold_distance_band(0.25) == 'intermediate_distance'
    assert threshold_distance_band(0.90) == 'far_from_threshold'


def test_append_columns_preserves_rows():
    out = append_diagnostic_columns(pd.DataFrame({'score': [0.99, None]}))
    assert len(out) == 2
    assert out.loc[0, 'score_at_least_0_99']
    assert out.loc[1, 'threshold_distance_band'] == 'not_scored'


def test_morphology_metrics_are_bounded():
    metrics = image_morphology_metrics(Image.new('RGB', (96, 96), (255, 255, 255))).to_dict()
    for key in ('tissue_fraction', 'open_space_fraction', 'edge_density', 'nuclear_like_fraction', 'he_like_purple_fraction'):
        assert 0.0 <= metrics[key] <= 1.0
    assert metrics['open_space_fraction'] == 1.0


def test_model_contract_detects_threshold_mismatch():
    result = model_contract_receipt(expected_sha256='a', observed_sha256='a', code_threshold=.5, artifact_threshold=.4, architecture='resnet18', input_size=[96, 96])
    assert result['model_hash_match'] is True
    assert result['threshold_match'] is False
    assert result['contract_pass'] is False
