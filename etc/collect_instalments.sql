CREATE OR REPLACE PROCEDURE collect_due_instalments()
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    interest_balance NUMERIC(20,2);
    interest_acct VARCHAR(20);
    savings_account_no VARCHAR(20);
    savings_balance NUMERIC(20,2);
    deposits_balance NUMERIC(20,2);
    inst_total NUMERIC(20,2);
    amount_remaining NUMERIC(20,2);
    remaining_inst_total NUMERIC(20,2);
    deposit_bal NUMERIC(20,2);
    deposit_acct VARCHAR(20);
    ls_rec RECORD;
BEGIN
    FOR rec IN
        SELECT DISTINCT
            ls.loan_account AS loan_account,
            ls.membership_number AS membership_number,
            ia.interest_due AS interest_due,
            ia.accrued_interest AS accrued_interest
        FROM loan_schedules ls
        JOIN loan_accounts la ON la.loan_account = ls.loan_account
        JOIN interest_accounts ia ON ia.loan_account = ls.loan_account
        WHERE ls.status = 'Due'
    LOOP
        -- Step 1: Get Savings and Interest Account Balances
        SELECT a.balance, a.account_no, b.balance, b.account_number
        INTO savings_balance, savings_account_no, interest_balance, interest_acct
        FROM portfolio a
        JOIN internal_accounts b ON b.account_number = '1003'
        WHERE a.membership_number = rec.membership_number AND a.account_type = 'Savings';

        IF savings_balance IS NULL THEN
            CONTINUE;  -- skip if no savings account
        END IF;

        -- Step 2: Collect Interest if possible
        IF savings_balance > 0 THEN
            IF savings_balance >= rec.interest_due THEN
                -- Full interest recovery
                INSERT INTO transactions(account_number, narrative, amount, running_balance,entered_by, posted)
                VALUES (savings_account_no, 'Interest Recovered', rec.interest_due , savings_balance + rec.interest_due,'SYSTEM', 'Y');

                INSERT INTO transactions(account_number, narrative, amount, running_balance,entered_by, posted)
                VALUES (interest_acct, savings_account_no, rec.interest_due* -1, interest_balance - rec.interest_due,'SYSTEM', 'Y');

                UPDATE internal_accounts
                SET balance = interest_balance - rec.interest_due
                WHERE account_number = interest_acct;

                UPDATE portfolio
                SET balance = savings_balance + rec.interest_due
                WHERE account_no = savings_account_no;

                UPDATE interest_accounts
                SET interest_due = 0,
                    accrued_interest = 0
                WHERE loan_account = rec.loan_account;

                savings_balance := savings_balance + rec.interest_due;

            ELSIF savings_balance < rec.accrued_interest THEN
                -- Partial interest recovery
                INSERT INTO transactions(account_number, narrative, amount, running_balance,entered_by, posted)
                VALUES (savings_account_no, 'Interest Recovered', savings_balance * -1, 0,'SYSTEM', 'Y');

                INSERT INTO transactions(account_number, narrative, amount, running_balance,entered_by, posted)
                VALUES (interest_acct, savings_account_no, savings_balance, interest_balance + savings_balance,'SYSTEM', 'Y');

                UPDATE internal_accounts
                SET balance = interest_balance + savings_balance
                WHERE account_number = interest_acct;

                UPDATE portfolio
                SET balance = 0
                WHERE account_no = savings_account_no;

                UPDATE interest_accounts
                SET interest_due = interest_due + savings_balance
                WHERE loan_account = rec.loan_account;

                savings_balance := 0;
            END IF;
        END IF;

        -- Step 3: Collect Instalments if balance remains
        IF savings_balance > 0 THEN
            SELECT COALESCE(SUM(instalment_amount), 0)
            INTO inst_total
            FROM loan_schedules
            WHERE loan_account = rec.loan_account AND status = 'Due';

            IF savings_balance >= inst_total THEN
                -- Full instalment recovery
                INSERT INTO transactions(account_number, narrative, amount, running_balance,entered_by, posted)
                VALUES (savings_account_no, 'Principal Instalment Recovered', inst_total * -1, savings_balance - inst_total,'SYSTEM', 'Y');

                INSERT INTO transactions(account_number, narrative, amount, running_balance,entered_by, posted)
                VALUES ('1001', savings_account_no, inst_total, interest_balance + inst_total,'SYSTEM', 'Y');

                UPDATE portfolio
                SET balance = savings_balance - inst_total
                WHERE account_no = savings_account_no;

                UPDATE internal_accounts 
                SET balance = balance + inst_total
                WHERE account_number = '1001'; 

                UPDATE loan_schedules
                SET pending_instalment = 0, status = 'Paid',last_updated = current_date::date
                WHERE loan_account = rec.loan_account AND status = 'Due';
				
		UPDATE loan_accounts 
		SET pending_amount = pending_amount + inst_total 
                WHERE  loan_account = rec.loan_account;

                savings_balance := savings_balance - inst_total;

            ELSE
                -- Partial instalment recovery
                remaining_inst_total := savings_balance;

                FOR ls_rec IN
                    SELECT * FROM loan_schedules
                    WHERE loan_account = rec.loan_account AND status = 'Due'
                    ORDER BY due_date
                LOOP
                    IF remaining_inst_total >= ls_rec.instalment_amount THEN
                        UPDATE loan_schedules
                        SET pending_instalment = 0, status = 'Paid',last_updated = current_date::date
                        WHERE loan_account = ls_rec.loan_account AND due_date = ls_rec.due_date;

                        remaining_inst_total := remaining_inst_total - ls_rec.instalment_amount;
                    ELSE
                        UPDATE loan_schedules
                        SET pending_instalment = instalment_amount - remaining_inst_total,last_updated = current_date::date
                        WHERE loan_account = ls_rec.loan_account AND due_date = ls_rec.due_date;

                        remaining_inst_total := 0;
                        EXIT;
                    END IF;
                END LOOP;

                INSERT INTO transactions(account_number, narrative, amount, running_balance, entered_by,posted)
                VALUES (savings_account_no, 'Partial Instalment Recovered', savings_balance * -1, 0, 'SYSTEM','Y');

                INSERT INTO transactions(account_number, narrative, amount, running_balance,entered_by, posted)
                VALUES ('1001', savings_account_no, savings_balance, interest_balance + savings_balance,'SYSTEM', 'Y');

                UPDATE portfolio
                SET balance = 0
                WHERE account_no = savings_account_no;

                UPDATE internal_accounts 
                SET balance = balance + savings_balance
                WHERE account_number = '1001'; 
				
		UPDATE loan_accounts 
		SET pending_amount = pending_amount + savings_balance
                WHERE loan_account = rec.loan_account;

                savings_balance := 0;
            END IF;
        END IF;

        -- Step 4: Transfer remaining to Deposits
        IF savings_balance > 0 THEN
            SELECT account_no, balance
            INTO deposit_acct, deposit_bal
            FROM portfolio
            WHERE account_type = 'Deposits' AND membership_number = rec.membership_number;

            INSERT INTO transactions(account_number, narrative, amount, running_balance,entered_by, posted)
            VALUES (savings_account_no, 'Deposits', savings_balance * -1, 0,'SYSTEM', 'Y');

            INSERT INTO transactions(account_number, narrative, amount, running_balance,entered_by, posted)
            VALUES (deposit_acct, 'Deposits', savings_balance, deposit_bal + savings_balance,'SYSTEM', 'Y');

            UPDATE portfolio
            SET balance = balance + savings_balance
            WHERE membership_number = rec.membership_number AND account_type = 'Deposits';

            UPDATE portfolio
            SET balance = 0
            WHERE account_no = savings_account_no;
        END IF;
    END LOOP;
END;
$$;