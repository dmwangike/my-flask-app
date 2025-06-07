CREATE OR REPLACE FUNCTION handle_transaction_insert()
RETURNS TRIGGER AS $$
DECLARE
    savings_account_no TEXT;
    savings_balance NUMERIC;
    deposit_acct TEXT;
    deposit_bal NUMERIC;
    mem_no TEXT;
BEGIN
    -- Process only for non-SYSTEM inserts
    IF NEW.entered_by <> 'SYSTEM' AND NEW.account_number LIKE '%SV' THEN
        savings_account_no := NEW.account_number;
        savings_balance := NEW.amount;
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
            INSERT INTO transactions(account_number, narrative, amount, running_balance, entered_by, posted)
            VALUES (savings_account_no, 'Deposits', savings_balance * -1, 0, 'SYSTEM', 'Y');

            -- Move money into deposit account
            INSERT INTO transactions(account_number, narrative, amount, running_balance, entered_by, posted)
            VALUES (deposit_acct, 'Deposits', savings_balance, deposit_bal + savings_balance, 'SYSTEM', 'Y');

            -- Update balances
            UPDATE portfolio
            SET balance = balance + savings_balance
            WHERE membership_number = mem_no AND account_type = 'Deposits';

        ELSE
            -- If account is linked to a due loan, execute procedure
            CALL collect_due_instalments();
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
