# Famai Motor ERP - Real Life Checklist

This file explains what you already have, what each file is for, and what is still needed before using the system for real shop operations.

## 1. Files You Already Have

### Main App

`server.py`

The backend. It runs the local web system, saves data into SQLite, checks login permissions, creates backups, imports CSV files, and sends dashboard data to the browser.

`static/index.html`

The screen layout. This contains the forms and page sections: login, receive motorcycle, sell motorcycle, expenses, import old data, stock reports, and logs.

`static/app.js`

The browser logic. This sends form data to the backend, loads reports, fills the Yamaha model dropdown, handles login/logout, backup, and CSV import.

`static/styles.css`

The design. This controls colors, sidebar, cards, tables, forms, mobile layout, and status labels.

### Database

`famai_motor.db`

The real local database file. This stores branches, users, motorcycles, customers, sales, expenses, stock movements, and Yamaha model prices.

`schema.sql`

The database design. This is the structure you can later move to PostgreSQL or Supabase.

### Model Price Data

`yamaha_model_prices.json`

The Yamaha model and price list extracted from your PDF. The app uses this for model dropdown, cost, and suggested retail price.

### Backup And Reset

`backups/`

Backup database files are saved here when you click **Backup DB**.

`reset_database.py`

Resets the local database back to starter data. Use carefully, because it removes real records.

### Instructions

`README.md`

Basic run instructions, login accounts, backup instructions, and CSV import templates.

## 2. What Works Now

- Login with staff roles
- Admin, sales, stock, accounting, manager permissions
- Receive motorcycle stock
- Store `เลขเครื่อง / engine_no`
- Store `เลขถัง / frame_no`
- Store model code
- Use Yamaha model dropdown
- Auto-fill cost from Yamaha price list
- Suggest sale price from Yamaha price list
- Sell exact motorcycle unit
- Clear sold unit from available stock
- Add expenses
- Backup database
- Import old stock CSV
- Import old sales CSV
- Import old expenses CSV
- View stock report
- View sales log
- View expense log
- View stock movement audit trail
- Management dashboard for daily/MTD KPIs
- Branch comparison with best/lowest branch markers
- Salesperson ranking
- Registration tracking
- Aging stock report
- Finance dashboard
- Top models and stock alerts

## 3. What You Need Before Real Shop Use

### Must Have

1. Change default passwords.
2. Make a daily backup rule.
3. Import old stock, sales, and expenses.
4. Test with real staff workflow for several days.
5. Add Excel export for reports.
6. Add edit/cancel functions with admin approval.
7. Add customer detail page.
8. Add registration document tracking.

### Should Have

1. Search by customer phone.
2. Search by `เลขเครื่อง`.
3. Search by `เลขถัง`.
4. Filter stock by branch/model/status.
5. Daily close cash report.
6. Payment method report: cash, transfer, finance, deposit.
7. Profit report: sale price minus cost minus expenses.
8. Branch report for all 3 branches.

### Later For Multi-Branch Online Use

1. Move database from SQLite to Supabase/PostgreSQL.
2. Host app online.
3. Add secure HTTPS.
4. Add stronger password hashing.
5. Add automatic cloud backup.
6. Add file upload for ID card, registration, and sale documents.

## 4. Real Daily Workflow

### Morning

1. Log in.
2. Check dashboard.
3. Check stock risk.
4. Check pending registrations or payments.

### When New Motorcycles Arrive

1. Go to Product Receiving.
2. Select branch.
3. Select model.
4. Enter color.
5. Enter `เลขเครื่อง`.
6. Enter `เลขถัง`.
7. Confirm cost.
8. Save.

### When Selling

1. Go to Registration Sales.
2. Choose exact motorcycle unit.
3. Enter customer info.
4. Enter sale price.
5. Select payment method.
6. Save sale.
7. The motorcycle becomes sold automatically.

### When Paying Expenses

1. Go to Finance & Accounting.
2. Select branch.
3. Choose expense category.
4. Enter amount and note.
5. Save.

### End Of Day

1. Check sales log.
2. Check expense log.
3. Check net cash.
4. Click Backup DB.
5. Copy backup file somewhere safe.

## 5. CSV Import Files You Need

### Old Motorcycle Stock

```csv
branch,model,model_code,color_code,color,engine_no,frame_no,cost,status,received_at,note
Famai Motor,NMAX,BTF200,010B,Black,E-OLD-001,F-OLD-001,85000,available,2026-06-01,Opening stock
```

### Old Sales

```csv
branch,model,model_code,color_code,color,engine_no,frame_no,cost,customer_name,customer_phone,customer_address,sale_price,payment_method,salesperson,finance_company,finance_status,registration_status,received_at,sold_at
Famai Motor,NMAX,BTF200,010B,Black,E-SOLD-001,F-SOLD-001,85000,Somchai,0812345678,Bangkok,98500,finance,เซลล์สนุ๊กเกอร์,กรุงศรี,approved,รอทะเบียน,2026-05-20,2026-06-10
```

### Old Expenses

```csv
branch,category,amount,note,paid_at
Famai Motor,Employee payment,15000,June salary,2026-06-15
```

## 6. Real-Life Safety Rules

1. Never reuse the same `เลขเครื่อง`.
2. Never reuse the same `เลขถัง`.
3. Backup before importing old data.
4. Backup before making big edits.
5. Keep one copy of backups outside the computer.
6. Give each staff member their own login later.
7. Do not let normal staff delete records.
8. Use cancel/void records instead of deleting business history.

## 7. Best Next Build Order

1. Change password page.
2. Excel export.
3. Search page.
4. Customer detail page.
5. Registration tracking.
6. Payment tracking.
7. Edit/cancel with admin approval.
8. Move online for all branches.
