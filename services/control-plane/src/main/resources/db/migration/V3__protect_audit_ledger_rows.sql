CREATE FUNCTION reject_audit_ledger_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_ledger is append-only';
END;
$$;

CREATE TRIGGER audit_ledger_reject_update_delete
BEFORE UPDATE OR DELETE ON audit_ledger
FOR EACH ROW
EXECUTE FUNCTION reject_audit_ledger_mutation();
