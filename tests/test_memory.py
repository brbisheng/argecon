from __future__ import annotations

from src.memory import DEFAULT_SESSION_STORE, SessionState, update_session_state



def setup_function() -> None:
    DEFAULT_SESSION_STORE.clear()



def test_update_session_state_extracts_minimal_slots_from_query() -> None:
    state = update_session_state(
        session_id="sess-1",
        query="我想借10万元养牛，去年还有一点没还完，想贷12个月。",
    )

    assert state.session_id == "sess-1"
    assert state.amount == "10万元"
    assert state.crop_or_activity == "养牛"
    assert state.duration == "12个月"
    assert state.existing_loan is True



def test_update_session_state_uses_current_evidence_and_persists_by_session_id() -> None:
    stored = SessionState(session_id="sess-2", purpose="经营周转")
    DEFAULT_SESSION_STORE.save(stored)

    state = update_session_state(
        session_id="sess-2",
        query="我不是合作社，也没有担保人。",
        evidence=["这个项目主要支持买饲料和养牛户申请。"],
    )

    assert state.purpose == "农业生产资料投入"
    assert state.crop_or_activity == "养牛"
    assert state.cooperative is False
    assert state.guarantor is False
    assert DEFAULT_SESSION_STORE.get("sess-2") is state
