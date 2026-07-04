CREATE TABLE branches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  username TEXT UNIQUE,
  password_hash TEXT,
  role TEXT NOT NULL CHECK (role IN ('admin', 'sales', 'stock', 'accounting', 'manager')),
  branch_id INTEGER REFERENCES branches(id)
);

CREATE TABLE customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  surname TEXT,
  nickname TEXT,
  how_to_call TEXT,
  phone TEXT,
  address TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE motorcycles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  branch_id INTEGER NOT NULL REFERENCES branches(id),
  model_code TEXT,
  model TEXT NOT NULL,
  color_code TEXT,
  color TEXT,
  engine_no TEXT NOT NULL UNIQUE,
  frame_no TEXT NOT NULL UNIQUE,
  cost REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK (status IN ('available', 'hold', 'sold', 'written_off')) DEFAULT 'available',
  received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE model_prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  cc REAL,
  model_year INTEGER,
  cost REAL NOT NULL,
  vat REAL NOT NULL DEFAULT 0,
  total REAL NOT NULL DEFAULT 0,
  retail_price REAL NOT NULL
);

CREATE TABLE sales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  motorcycle_id INTEGER NOT NULL UNIQUE REFERENCES motorcycles(id),
  customer_id INTEGER REFERENCES customers(id),
  sale_price REAL NOT NULL,
  payment_method TEXT NOT NULL DEFAULT 'cash',
  salesperson TEXT,
  finance_company TEXT,
  finance_status TEXT NOT NULL DEFAULT 'none',
  registration_status TEXT NOT NULL DEFAULT 'ขายแล้ว',
  sold_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  branch_id INTEGER NOT NULL REFERENCES branches(id),
  category TEXT NOT NULL,
  amount REAL NOT NULL,
  note TEXT,
  paid_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stock_movements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  motorcycle_id INTEGER REFERENCES motorcycles(id),
  branch_id INTEGER REFERENCES branches(id),
  movement_type TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customer_cases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  branch_id INTEGER NOT NULL REFERENCES branches(id),
  first_name TEXT NOT NULL,
  surname TEXT,
  nickname TEXT,
  how_to_call TEXT,
  phone TEXT NOT NULL,
  salesperson TEXT,
  case_status TEXT NOT NULL CHECK (case_status IN ('ปิดการขายได้', 'ลูกค้าสนใจ', 'ลูกค้าไม่สนใจ', 'ติด finance')),
  note TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE registration_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_id INTEGER REFERENCES sales(id),
  branch_id INTEGER NOT NULL REFERENCES branches(id),
  first_name TEXT NOT NULL,
  surname TEXT,
  nickname TEXT,
  how_to_call TEXT,
  phone TEXT NOT NULL,
  registration_status TEXT NOT NULL CHECK (registration_status IN ('จดทะเบียน', 'รอจดทะเบียน')),
  submitted_at TEXT NOT NULL,
  registered_at TEXT,
  note TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE service_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_id INTEGER REFERENCES sales(id),
  customer_id INTEGER REFERENCES customers(id),
  motorcycle_id INTEGER REFERENCES motorcycles(id),
  service_at TEXT,
  oil_change_at TEXT,
  note TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE receipt_prints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_id INTEGER NOT NULL REFERENCES sales(id),
  authorized_by INTEGER NOT NULL REFERENCES users(id),
  requested_by INTEGER REFERENCES users(id),
  printed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE parts_sales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  branch_id INTEGER NOT NULL REFERENCES branches(id),
  part_name TEXT NOT NULL,
  part_code TEXT,
  quantity INTEGER NOT NULL DEFAULT 1,
  unit_price REAL NOT NULL DEFAULT 0,
  gross_amount REAL NOT NULL DEFAULT 0,
  discount_amount REAL NOT NULL DEFAULT 0,
  sale_total REAL NOT NULL DEFAULT 0,
  cost_total REAL NOT NULL DEFAULT 0,
  profit REAL NOT NULL DEFAULT 0,
  customer_name TEXT,
  salesperson TEXT,
  note TEXT,
  sold_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
