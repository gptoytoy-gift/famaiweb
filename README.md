# Famai Motor Real Starter System

This is the first real version of the Famai motorcycle dealer dashboard.

It uses:

- Python backend
- SQLite database
- Browser frontend
- Real saved records for receiving, stock, selling, expenses, and reports

## Run

From this folder:

```bash
python3 server.py
```

Then open:

```text
http://127.0.0.1:8787
```

## What Works Now

- Login with starter staff roles
- Role permissions for stock, sales, accounting, manager, and admin
- Backup button for the SQLite database
- Yamaha model/price dropdown loaded from `yamaha_model_prices.json`
- CSV import for old motorcycle stock, old sales, and old expenses
- Management dashboard: Today/MTD KPIs, branch comparison, salesperson ranking, finance, registration, aging stock, top models, stock alerts
- Receive motorcycle into stock
- Track each unit by `เลขเครื่อง / engine_no`
- Track each unit by `เลขถัง / frame_no`
- Auto-fill cost from the Yamaha price list when receiving stock
- Suggest retail sale price from the Yamaha price list when selling matching units
- Sell an exact motorcycle unit
- Clear sold unit from available stock
- Add expenses such as booth rental or employee payment
- See net cash, sales, expenses, stock risk
- See stock report and movement logs

## Database File

The app creates this file automatically:

```text
famai_motor.db
```

That file is the real local database.

## Starter Login Accounts

Use these for testing:

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin123` |
| Sales | `sales` | `sales123` |
| Stock | `stock` | `stock123` |
| Accounting | `accounting` | `accounting123` |
| Manager | `manager` | `manager123` |

Permissions:

- Admin: all actions and backup
- Sales: sell motorcycles and add customer case reports
- Stock: receive and adjust stock
- Accounting: add expenses and backup
- Manager: view reports and backup

## Backups

Click **Backup DB** in the top bar. Backup files are saved here:

```text
backups/
```

Example:

```text
backups/famai_motor_backup_20260622-101500.db
```

Keep copies of backup files outside this computer when using real data.

## Import Old Data

Log in as `admin`, then use **Import Old Data**.

Motorcycle stock CSV:

```csv
branch,model,model_code,color_code,color,engine_no,frame_no,cost,status,received_at,note
Famai Motor,NMAX,BTF200,010B,Black,E-OLD-001,F-OLD-001,85000,available,2026-06-01,Opening stock
```

Old sales CSV:

```csv
branch,model,model_code,color_code,color,engine_no,frame_no,cost,customer_name,customer_phone,customer_address,sale_price,payment_method,salesperson,finance_company,finance_status,registration_status,received_at,sold_at
Famai Motor,NMAX,BTF200,010B,Black,E-SOLD-001,F-SOLD-001,85000,Somchai,0812345678,Bangkok,98500,finance,เซลล์สนุ๊กเกอร์,กรุงศรี,approved,รอทะเบียน,2026-05-20,2026-06-10
```

Old expenses CSV:

```csv
branch,category,amount,note,paid_at
Famai Motor,Employee payment,15000,June salary,2026-06-15
```

Every motorcycle must have unique `engine_no` and `frame_no`.

## Customer Case Reports

Use **รายงานเคส** for salesperson follow-up customers that are not finished sales yet.

Statuses:

- `ปิดการขายได้`
- `ลูกค้าสนใจ`
- `ลูกค้าไม่สนใจ`
- `ติด finance`

These records are separate from the sales report and do not change stock, revenue, or profit.

## Registration Records

Use **ทะเบียน** for customers who already bought motorcycles.

- `วันที่เริ่มจดทะเบียน`: the date registration work started.
- `วันที่ได้รับทะเบียน`: fill this only after registration is received.
- `รอจดทะเบียน`: report shows how many days the customer has been waiting.
- `จดทะเบียน`: report shows how many total days registration took.

## Receipt Print Authorization

Use **Receipt Print** after a sale. Every print and reprint requires an authorized username/password.

Authorized roles:

- Admin
- Manager
- Accounting

Each successful print is saved in `receipt_prints`.

## Customer Dashboard

Use **Customer Dashboard** to see each customer with all motorcycles bought, engine number, frame number, purchase date, registration received date, service dates, and oil-change dates.

Use **Service / Oil Change** to add service and oil-change history for a sold motorcycle.

## Parts Sales

Use **Sale Parts / อะไหล่** to record spare-parts sales.

The system saves:

- ส่วนลด / discount
- ยอดขาย after discount
- ต้นทุน
- กำไร

## Next Production Steps

1. Change starter passwords.
2. Add customer detail pages.
3. Add registration workflow and document uploads.
4. Add payment tracking for cash, transfer, finance, and deposits.
5. Add Excel export.
6. Move from SQLite to Supabase/PostgreSQL when you want online access from multiple branches.
