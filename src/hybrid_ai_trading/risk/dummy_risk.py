from __future__ import annotations


class DummyRiskMgr:
    """
    Minimal approve-all risk manager used by paper_quantcore smoke path.
    Returns a dict so wrappers that normalize approvals see the expected shape.
    """

    def approve_trade(self, *args, **kwargs):
        return {"approved": True, "reason": "stub"}
