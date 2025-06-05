CREATE OR REPLACE PROCEDURE update_due_loans()
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    int_due NUMERIC(20,4);
BEGIN
    FOR rec IN
        SELECT ls.loan_account, ls.due_date, ls.status, la.interest_rate, la.pending_amount
        FROM loan_schedules ls
        JOIN loan_accounts la ON la.loan_account = ls.loan_account
        WHERE ls.due_date <= CURRENT_DATE
          AND ls.status = 'Not Due'
    LOOP
        -- Step 1: Update the status to 'Due'
        UPDATE loan_schedules
        SET status = 'Due'
        WHERE loan_account = rec.loan_account AND due_date = rec.due_date;

        -- Step 2: Calculate interest due
        int_due := (rec.interest_rate / 1200) * rec.pending_amount;

        -- Step 3: Update Interest_accounts
        UPDATE interest_accounts
        SET accrued_interest = int_due,
            total_loan_interest = total_loan_interest + int_due,
            interest_due = interest_due + int_due
        WHERE loan_account = rec.loan_account;
    END LOOP;
END;
$$;
