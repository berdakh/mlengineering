# audit_before_move

The audit entry is written before the pointer moves. If the move fails, the audit log claims a promotion that never happened, and rollback will later act on it.
