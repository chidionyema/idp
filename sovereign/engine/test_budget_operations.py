from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pytest
from sovereign import config
from sovereign.engine import budget

@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'BUDGET_DB', tmp_path / 'budget.db')


def test_lost_ack_replays_original_receipt_not_second_debit():
    budget.apply_operation('allocate', 's', 'allocate', 100)
    first = budget.apply_operation('spend', 's', 'spend', 30)
    budget.apply_operation('other', 's', 'spend', 10)
    assert budget.apply_operation('spend', 's', 'spend', 30, retry=True) == first
    assert budget.read('s').remaining == 60


def test_lost_ack_cannot_mint_second_refill():
    budget.allocate('s', 0)
    first = budget.apply_operation('refill', 's', 'refill', 50)
    assert budget.apply_operation('refill', 's', 'refill', 50, retry=True) == first
    assert budget.read('s').remaining == 50


def test_concurrent_duplicate_operation():
    budget.allocate('s', 100)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: budget.apply_operation('same', 's', 'spend', 7), range(24)))
    assert len(set(results)) == 1
    assert budget.read('s').remaining == 93


def test_concurrent_distinct_operations_conserve_balance():
    budget.allocate('s', 100)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda i: budget.apply_operation(f'op{i}', 's', 'spend', 7), range(24)))
    assert sum(x.spent for x in results) == 100
    assert budget.read('s').remaining == 0


@pytest.mark.parametrize('session,op,tokens', [('x','spend',30),('s','refill',30),('s','spend',31)])
def test_conflicting_replay_refused(session, op, tokens):
    budget.allocate('s', 100)
    budget.apply_operation('same', 's', 'spend', 30)
    with pytest.raises(budget.BudgetOperationRejected):
        budget.apply_operation('same', session, op, tokens)
    assert budget.read('s').remaining == 70


def test_unrecorded_retry_fails_closed():
    budget.allocate('s', 100)
    with pytest.raises(budget.BudgetOperationRejected):
        budget.apply_operation('legacy', 's', 'spend', 30, retry=True)
    assert budget.read('s').remaining == 100


@pytest.mark.parametrize('op,tokens', [('unknown',1),('refill',-1),('spend',True),('allocate',1.5)])
def test_unknown_or_invalid_mutation_refused(op, tokens):
    with pytest.raises(budget.BudgetOperationRejected):
        budget.apply_operation('bad', 's', op, tokens)
    assert budget.read('s').halted


def test_receipt_failure_rolls_back_balance():
    budget.allocate('s', 100)
    with sqlite3.connect(config.BUDGET_DB) as conn:
        conn.execute(budget._OPERATION_SCHEMA)
        conn.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON budget_operations BEGIN SELECT RAISE(ABORT, 'fault'); END")
    with pytest.raises(sqlite3.IntegrityError):
        budget.apply_operation('fails', 's', 'spend', 30)
    assert budget.read('s').remaining == 100
    with sqlite3.connect(config.BUDGET_DB) as conn:
        assert conn.execute('SELECT count(*) FROM budget_operations').fetchone()[0] == 0


def test_existing_allocate_idempotency_preserved():
    budget.allocate('s', 100)
    budget.spend('s', 60)
    assert budget.allocate('s', 100).remaining == 40
