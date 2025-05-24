def sqlextract(params):
    from jinjasql import JinjaSql
    jtemp = """
    SELECT acct_name, foracid,PSTD_DATE,VALUE_DATE,TRAN_CODE,REFERENCE,TRAN_PARTICULAR,ACCTRANSCOUNTER,DTH_INIT_SOL_ID AS SOURCEBRANCH,TRAN_RMKS,AMOUNT,nvl( lag(RUNNING_BAL)  over(order by ACCTRANSCOUNTER desc),bookbalance) as Running_bal
    from(
    SELECT x.*,bookbalance - SUM(AMOUNT) over(order by ACCTRANSCOUNTER desc)  as RUNNING_BAL from(
    SELECT b.acct_name,a.*, b.CLR_BAL_AMT + b.FUTURE_BAL_AMT BOOKBALANCE,b.FORACID,row_number() over (order by PSTD_DATE, REFERENCE) ACCTRANSCOUNTER from (
    select PSTD_DATE,VALUE_DATE,nvl(USER_PART_TRAN_CODE,SYS_PART_TRAN_CODE) as TRAN_CODE,DTH_INIT_SOL_ID,TRAN_RMKS,TRIM(TRAN_ID)||'_'||TRIM(PART_TRAN_SRL_NUM) AS REFERENCE,TRAN_PARTICULAR, case when PART_TRAN_TYPE = 'D' then TRAN_AMT * -1 else TRAN_AMT end AMOUNT,ACID from TBAADM.HTD@finstby
    WHERE PSTD_FLG = 'Y' AND DEL_FLG = 'N'
    UNION ALL
    select PSTD_DATE,VALUE_DATE,nvl(USER_PART_TRAN_CODE,SYS_PART_TRAN_CODE) as TRAN_CODE,DTH_INIT_SOL_ID,TRAN_RMKS,TRIM(TRAN_ID)||'_'||TRIM(PART_TRAN_SRL_NUM) AS REFERENCE,TRAN_PARTICULAR, case when PART_TRAN_TYPE = 'D' then TRAN_AMT * -1 else TRAN_AMT end AMOUNT,ACID from TBAADM.DTD@finstby
    WHERE PSTD_FLG = 'Y' AND DEL_FLG = 'N' ) a JOIN TBAADM.GAM@fINSTBY b ON a.ACID = b.ACID and foracid = '{{accountid}}') x)
    """
    j = JinjaSql(param_style='pyformat')
    query, bind_params = j.prepare_query(jtemp, params)
    return query % bind_params
    
def arfasset(params):
    from jinjasql import JinjaSql
    xtemp = """
	SELECT * FROM (
	with loandetails as (SELECT b.ACCT_NAME, b.FORACID, b.CIF_ID,b.acid, b.schm_code,b.FREE_TEXT,b.ACCT_OPN_DATE,b.clr_bal_AMT,
	  CAST(CASE WHEN TO_DATE(TO_CHAR(b.ACCT_OPN_DATE,'DD-MON')||'-'||TO_CHAR(SYSDATE,'YYYY')) > TRUNC(SYSDATE) THEN
	ADD_MONTHS( TO_DATE(TO_CHAR(b.ACCT_OPN_DATE,'DD-MON')||'-'||TO_CHAR(SYSDATE,'YYYY')) ,-12)
	ELSE TO_DATE(TO_CHAR(b.ACCT_OPN_DATE,'DD-MON')||'-'||TO_CHAR(SYSDATE,'YYYY')) END AS DATE)
	  AS CURRENT_ANNIVERSARY,ACCT_MGR_USER_ID
	FROM TBAADM.GAM@FINSTBY b
	WHERE b.SOL_ID = '{{solid}}' AND
	b.SCHM_CODE IN ('MSMER','MORTA', 'MORTC', 'MORTE', 'MORTI', 'MORTN', 'MORTP', 'MORTS','COWCL')AND ACCT_CLS_FLG = 'N')
	SELECT
	b.*,E.EOD_DATE as LAST_EOD_DATE, E.TRAN_DATE_BAL AS BAL_ON_ASSESSMENT, a.FEE_TYPE, a.ASSESSMENT_DATE,a.SYS_CALC_FEE_AMT,
	RANK() OVER (PARTITION BY E.ACID ORDER BY E.EOD_DATE DESC) AS RWN FROM loandetails b
	LEFT OUTER JOIN TBAADM.FEE_ASSMNT_HISTORY_TABLE@FINSTBY a  on a.entity_id = b.acid AND a.ASSESSMENT_DATE >= b.CURRENT_ANNIVERSARY
	LEFT OUTER join tbaadm.eab@finstby E ON b.acid = E.ACID AND E.EOD_DATE <=b.CURRENT_ANNIVERSARY
	WHERE ASSESSMENT_DATE IS NULL )
	WHERE RWN = 1 AND  TO_CHAR(CURRENT_ANNIVERSARY ,'YYYY-MM-DD')> = '{{startdate}}'
    """
    j = JinjaSql(param_style='pyformat')
    query, bind_params = j.prepare_query(xtemp, params)
    return query % bind_params 
    
def arfcoll(params):
    from jinjasql import JinjaSql
    rtemp = """
        SELECT aa.*
        FROM (
	SELECT /*+ PARALLEL(16) */b.acct_name,b.foracid,b.SOL_ID,b.SCHM_CODE,b.CIF_ID,
	a.ENTITY_id,a.entity_type,a.assessment_date,E.EOD_DATE as LAST_EOD_DATE, E.TRAN_DATE_BAL AS BAL_ON_ASSESSMENT,
	ROUND(a.sys_calc_fee_amt *(5/6),2) AS ASSESSEDFEE_ONLY,
	a.sys_calc_fee_amt AS ASSESSEDFEE_WITHTAX,
	c.SYSTEM_CALC_AMT AS COLLECTEDFEE_ONLY,c.CHRG_TRAN_DATE,
	a.fee_status_flg,c.COMP_B2KID,c.EVENT_TYPE,c.EVENT_ID,c.SERVICE_SOL_ID,
	c.ACTUAL_AMT_COLL,c.TRAN_PARTICULAR,c.TRAN_RMKS,c.CUST_ID,D.FORACID CHRG_ACCT,c.LCHG_USER_ID,
	ROW_NUMBER() OVER (PARTITION BY E.ACID ORDER BY E.EOD_DATE DESC) AS RWN
	FROM TBAADM.FEE_ASSMNT_HISTORY_TABLE@FINSTBY a join tbaadm.gam@finstby b on a.entity_id = b.acid
	LEFT OUTER JOIN tbaadm.CXL@finstby c on b.acid = c.TARGET_ACID AND c.EVENT_TYPE ='MISC6'
	and SUBSTR(c.EVENT_ID,1,17) = 'ANNUAL REVIEW FEE' AND
	TO_CHAR(a.assessment_date,'YYYY') = TO_CHAR(c.CHRG_TRAN_DATE,'YYYY')
	LEFT OUTER JOIN tbaadm.gam@finstby D ON D.ACID = C.CHRG_ACID
	LEFT OUTER join tbaadm.eab@finstby E ON a.entity_id = E.ACID AND E.EOD_DATE <=a.assessment_date
	WHERE b.sol_id = '{{solid}}' AND TO_CHAR(a.assessment_date ,'YYYY-MM-DD') >=  '{{startdate}}' AND a.FEE_TYPE = 'MISC6' AND b.SCHM_CODE IN ('MSMER','MORTA', 'MORTC', 'MORTE', 'MORTI', 'MORTN', 'MORTP', 'MORTS','COWCL'))aa
	where aa.rwn =1
    """
    j = JinjaSql(param_style='pyformat')
    query, bind_params = j.prepare_query(rtemp, params)
    return query % bind_params 
    
def Spool_statement(Statement):
	return(f'C:\\Users\\dkamande\\oikonomos\\DATA\\{Statement}.xlsx')

def txnextract(params):
    from jinjasql import JinjaSql
    ttemp = """
    SELECT UBVALUEDTTM VALUEDATE,UBTRANSACTIONREFERENCE TRANSACTIONID, UBNARRATIVE NARRATION, to_char(UBTRANSACTIONAMOUNT,'999,999,999,999,999,999.99') AMOUNT,UBPRODUCTID, UBACCOUNTID, UBSTATUS STATUS 
    FROM WASADMIN.UBTB_INTERNALPOSTINGAUDIT WHERE UBSTATUS = 'N' AND UBTRANSACTIONREFERENCE = '{{transactionid}}'
    """
    j = JinjaSql(param_style='pyformat')
    query, bind_params = j.prepare_query(ttemp, params)
    return query % bind_params 
 


