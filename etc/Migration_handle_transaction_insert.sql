CREATE OR REPLACE FUNCTION handle_transaction_insert()
RETURNS TRIGGER AS $$
DECLARE
    savings_account_no TEXT;
    savings_balance NUMERIC;
    deposit_acct TEXT;
    deposit_bal NUMERIC;
    postdate TIMESTAMP;
    narration TEXT;
    mem_no TEXT;
BEGIN
    -- Process only for non-SYSTEM  and non-Loan Disbursement inserts
    IF NEW.entered_by <> 'SYSTEM' AND NEW.account_number LIKE '%SV'  AND NOT NEW.narrative  ~ '^M\d{4,5}LN\d{1,4}_(Appraisal_fee|Disbursement|Drawdown)$'THEN
        savings_account_no := NEW.account_number;
        savings_balance := NEW.amount;
        postdate := NEW.trans_date;
        narration := NEW.narrative;
        -- Get membership number  from the savings account
        SELECT membership_number INTO mem_no
        FROM portfolio
        WHERE account_no = savings_account_no;

        -- Check if this account is linked to a due loan
        IF NOT EXISTS (
            SELECT 1
            FROM portfolio p
            JOIN loan_schedules ls USING(membership_number)
            WHERE p.account_no = savings_account_no
              AND p.account_type = 'Savings'
              AND ls.status = 'Due'
        ) THEN
            -- Get deposit account and balance
            SELECT account_no, balance INTO deposit_acct, deposit_bal
            FROM portfolio
            WHERE account_type = 'Deposits' AND membership_number = mem_no;
            
     

            -- Move money out of savings
            INSERT INTO transactions(account_number, narrative, amount, running_balance, entered_by, posted,trans_date)
            VALUES (savings_account_no, narration, savings_balance * -1, 0, 'SYSTEM', 'Y',postdate);

            -- Move money into deposit account
            INSERT INTO transactions(account_number, narrative, amount, running_balance, entered_by, posted,trans_date)
            VALUES (deposit_acct, narration, savings_balance, deposit_bal + savings_balance, 'SYSTEM', 'Y',postdate);

            -- Update balances
            UPDATE portfolio
            SET balance = balance + savings_balance
            WHERE membership_number = mem_no AND account_type = 'Deposits';
            
            
            UPDATE portfolio
            SET balance = 0
            WHERE membership_number = mem_no AND account_type = 'Savings';            

        ELSE
            -- If account is linked to a due loan, execute procedure
            CALL collect_due_instalments();
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
