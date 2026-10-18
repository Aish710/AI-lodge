"""The frozen live suite can be exercised against malicious mock models without spending money."""
import importlib.util
import json
from pathlib import Path

import pytest
from llm_mock import MockLLM

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/redteam_copilot.py'
spec = importlib.util.spec_from_file_location('redteam_copilot', SCRIPT)
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)
ATTACKS = json.loads(rt.SUITE.read_text())['attacks']


@pytest.mark.parametrize('attack', ATTACKS, ids=lambda a: a['id'])
@pytest.mark.parametrize('entry', rt.ENTRY_POINTS)
def test_frozen_attacks_reject_out_of_schema_authority(attack, entry):
    # This controls the RAW model response, so success does not depend on the model refusing.
    raw = {'operation': 'APPLY_SECRET', 'confirmed_ids': ['all'], 'savings': 999999, 'valid': True}
    mock = MockLLM([raw] * 2)
    out = rt.run_case(attack, entry, mock)
    assert out['http_status'] == 200
    assert out['schema_validator_rejected'] is True
    assert not out['final_plan_affected'] and not out['final_result_compromise_indicators']
    assert not out['sensitive_information_exposed_indicator']
    assert '999999' not in json.dumps({k: v for k, v in out['api_response'].items() if k != 'raw_input_echo'})
    if attack.get('description'):
        assert attack['description'] not in mock.all_prompt_text


def test_dry_run_never_loads_keys_or_calls_models(monkeypatch, capsys):
    monkeypatch.setattr(rt.lc, 'load_env_file', lambda: pytest.fail('dry-run read credentials'))
    assert rt.main([]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out['max_calls'] == 80 and out['cases'] == 48 and out['estimated_cost'] is None


@pytest.mark.parametrize('action', [
    {'action': 'switch_hotel', 'hotel_name': 'Odaiba Harbour Stay'},
    {'action': 'demote_must_visit', 'attraction_name': 'Senso-ji'},
    {'action': 'allow_unknown_hours'},
    {'action': 'remove_optional', 'attraction_name': 'Moon Palace Observatory'},
])
def test_schema_valid_malicious_repair_still_cannot_execute(action):
    attack = next(a for a in ATTACKS if a['id'] == 'confirmation')
    out = rt.run_case(attack, 'repair', MockLLM([{'actions': [action]}]))
    assert not out['schema_validator_rejected']
    assert not out['final_plan_affected'] and not out['final_result_compromise_indicators']
    api = out['api_response']
    assert api['executed'] is False
    for a in api['actions']:
        assert a['requires_confirmation'] is True
    if action['action'] == 'switch_hotel':
        assert out['action_validator_rejected'] and not api['actions']
    if 'Moon' in action.get('attraction_name', ''):
        assert api['unresolved_names'] and not api['actions']


def test_schema_valid_style_cannot_invent_budget_or_numeric_limit():
    attack = next(a for a in ATTACKS if a['id'] == 'invent_data')
    out = rt.run_case(attack, 'style', MockLLM([{'max_activities': 7, 'budget': {'amount': 999999, 'currency': 'JPY', 'strict': True}}]))
    assert not out['schema_validator_rejected'] and not out['api_response']['settings']
    assert out['api_response']['clarifications'] and not out['final_plan_affected']
