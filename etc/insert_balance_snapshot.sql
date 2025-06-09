CREATE OR REPLACE PROCEDURE insert_balance_snapshot()
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO BALANCE_SNAPSHOT (
        EOM,
        DEPOSIT_ACCOUNT,
        DEPOSITS,
        LOAN_ACCOUNT,
        LOAN,
        INTEREST_ACCOUNT,
        INTEREST
    )
    SELECT 
        current_date::DATE AS EOM,
        a.account_no AS deposit_account,
        a.balance AS deposits,
        COALESCE(b.loan_account, 'None') AS loan_account,
        COALESCE(b.pending_amount, 0) AS loan,
        COALESCE(c.interest_account, 'None') AS interest_account,
        COALESCE(c.interest_due, 0) AS interest
    FROM portfolio a
    LEFT OUTER JOIN loan_accounts b 
        ON b.member_number = a.membership_number AND b.pending_amount <> 0
    LEFT OUTER JOIN interest_accounts c 
        ON c.membership_number = a.membership_number AND c.interest_due <> 0
    WHERE a.account_type = 'Deposits';
END;
$$;
