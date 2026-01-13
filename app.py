import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

DB_PATH = "sales.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL,
            total REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )
    conn.commit()
    conn.close()


def fetch_df(query, params=None):
    conn = get_conn()
    df = pd.read_sql_query(query, conn, params=params or [])
    conn.close()
    return df


def execute(query, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params or [])
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def execute_many(query, rows):
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(query, rows)
    conn.commit()
    conn.close()


def get_or_create_walkin_customer_id():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM customers WHERE name = ? LIMIT 1", ("Khách lẻ",))
    row = cur.fetchone()
    if row:
        conn.close()
        return int(row["id"])
    cur.execute(
        "INSERT INTO customers (name, phone, email, address, created_at) VALUES (?, ?, ?, ?, ?)",
        ("Khách lẻ", None, None, None, date.today().isoformat()),
    )
    conn.commit()
    customer_id = cur.lastrowid
    conn.close()
    return int(customer_id)


st.set_page_config(page_title="Quản lý bán hàng", layout="wide")
init_db()

st.markdown(
    """
<style>
body { background: #f6f7fb; }
.block-container { padding-top: 1.5rem; }
.section-card {
  background: #ffffff;
  padding: 18px;
  border-radius: 12px;
  border: 1px solid #e7e9f0;
  margin-bottom: 16px;
}
.section-title {
  font-weight: 700;
  letter-spacing: 0.2px;
  margin-bottom: 6px;
}
.tone-blue { border-left: 6px solid #2f6fed; }
.tone-green { border-left: 6px solid #2bb673; }
.tone-orange { border-left: 6px solid #f39c12; }
.tone-purple { border-left: 6px solid #8e44ad; }
.tone-red { border-left: 6px solid #e74c3c; }
.tone-teal { border-left: 6px solid #18a2a5; }
.tone-gold { border-left: 6px solid #c49a00; }
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: #ffffff;
  vertical-align: middle;
}
.badge-blue { background: #2f6fed; }
.badge-green { background: #2bb673; }
.badge-orange { background: #f39c12; }
.badge-purple { background: #8e44ad; }
.badge-red { background: #e74c3c; }
.badge-teal { background: #18a2a5; }
.badge-gold { background: #c49a00; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🧾 Quản lý bán hàng")

tabs = st.tabs(
    ["Sản phẩm", "Tồn kho", "Khách hàng", "Đơn hàng", "Hóa đơn", "Báo cáo", "Nhập Excel"]
)


with tabs[0]:
    st.markdown(
        '<div class="section-card tone-blue"><div class="section-title">'
        '<span class="badge badge-blue">Sản phẩm</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Thêm sản phẩm")
    with st.form("add_product"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            name = st.text_input("Tên sản phẩm")
        with col2:
            sku = st.text_input("SKU")
        with col3:
            price = st.number_input("Giá bán", min_value=0.0, step=1000.0)
        with col4:
            stock = st.number_input("Tồn kho", min_value=0, step=1)
        submitted = st.form_submit_button("Lưu sản phẩm")
        if submitted:
            if not name.strip():
                st.warning("Vui lòng nhập tên sản phẩm.")
            else:
                execute(
                    "INSERT INTO products (name, sku, price, stock, created_at) VALUES (?, ?, ?, ?, ?)",
                    (name.strip(), sku.strip() or None, price, int(stock), date.today().isoformat()),
                )
                st.success("Đã thêm sản phẩm.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Danh sách sản phẩm")
    products_df = fetch_df(
        "SELECT id, name, sku, price, stock, created_at FROM products ORDER BY id DESC"
    )
    st.dataframe(products_df, use_container_width=True)

    if not products_df.empty:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Xóa sản phẩm")
        product_map = (
            products_df["id"].astype(str)
            + " - "
            + products_df["name"].astype(str)
        ).tolist()
        selected = st.selectbox("Chọn sản phẩm", product_map)
        if st.button("Xóa"):
            product_id = int(selected.split(" - ")[0])
            execute("DELETE FROM products WHERE id = ?", (product_id,))
            st.success("Đã xóa sản phẩm.")
        st.markdown("</div>", unsafe_allow_html=True)


with tabs[1]:
    st.markdown(
        '<div class="section-card tone-green"><div class="section-title">'
        '<span class="badge badge-green">Tồn kho</span></div></div>',
        unsafe_allow_html=True,
    )
    st.subheader("Tồn kho hiện tại")
    inventory_df = fetch_df(
        "SELECT name AS 'Sản phẩm', sku AS 'SKU', price AS 'Giá bán', stock AS 'Tồn kho' FROM products"
    )
    st.dataframe(inventory_df, use_container_width=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Cảnh báo tồn kho thấp")
    threshold = st.number_input("Ngưỡng cảnh báo", min_value=1, value=10, step=1)
    low_stock_df = fetch_df(
        "SELECT name AS 'Sản phẩm', sku AS 'SKU', stock AS 'Tồn kho' FROM products WHERE stock <= ?",
        (int(threshold),),
    )
    st.dataframe(low_stock_df, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


with tabs[2]:
    st.markdown(
        '<div class="section-card tone-orange"><div class="section-title">'
        '<span class="badge badge-orange">Khách hàng</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Thêm khách hàng")
    with st.form("add_customer"):
        col1, col2, col3 = st.columns(3)
        with col1:
            cname = st.text_input("Họ tên")
        with col2:
            phone = st.text_input("Số điện thoại")
        with col3:
            email = st.text_input("Email")
        address = st.text_input("Địa chỉ")
        submitted = st.form_submit_button("Lưu khách hàng")
        if submitted:
            if not cname.strip():
                st.warning("Vui lòng nhập tên khách hàng.")
            else:
                execute(
                    "INSERT INTO customers (name, phone, email, address, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        cname.strip(),
                        phone.strip() or None,
                        email.strip() or None,
                        address.strip() or None,
                        date.today().isoformat(),
                    ),
                )
                st.success("Đã thêm khách hàng.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Danh sách khách hàng")
    customers_df = fetch_df(
        """
        SELECT id, name, phone, email, address, created_at
        FROM customers
        WHERE name != 'Khách lẻ'
        ORDER BY id DESC
        """
    )
    st.dataframe(customers_df, use_container_width=True)

    if not customers_df.empty:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Xóa khách hàng")
        customer_map = (
            customers_df["id"].astype(str) + " - " + customers_df["name"].astype(str)
        ).tolist()
        selected = st.selectbox("Chọn khách hàng", customer_map)
        if st.button("Xóa khách hàng"):
            customer_id = int(selected.split(" - ")[0])
            execute("DELETE FROM customers WHERE id = ?", (customer_id,))
            st.success("Đã xóa khách hàng.")
        st.markdown("</div>", unsafe_allow_html=True)


with tabs[3]:
    st.markdown(
        '<div class="section-card tone-purple"><div class="section-title">'
        '<span class="badge badge-purple">Đơn hàng</span></div></div>',
        unsafe_allow_html=True,
    )
    st.subheader("Tạo đơn hàng")
    customers_df = fetch_df("SELECT id, name FROM customers ORDER BY name")
    products_df = fetch_df("SELECT id, name, price, stock FROM products ORDER BY name")

    if products_df.empty:
        st.info("Cần có sản phẩm trước khi tạo đơn hàng.")
    else:
        if "order_items" not in st.session_state:
            st.session_state.order_items = []

        col1, col2 = st.columns(2)
        with col1:
            customer_options = ["Khách lẻ"]
            customer_map = {}
            if not customers_df.empty:
                for _, row in customers_df.iterrows():
                    label = f'{row["name"]} (ID {row["id"]})'
                    customer_options.append(label)
                    customer_map[label] = int(row["id"])
            selected_customer = st.selectbox("Khách hàng", customer_options)
        with col2:
            order_date = st.date_input("Ngày bán", value=date.today())

        st.markdown("#### Thêm sản phẩm vào đơn")
        colp1, colp2, colp3 = st.columns([2, 1, 1])
        with colp1:
            product_id = st.selectbox(
                "Sản phẩm",
                products_df["id"],
                format_func=lambda x: products_df.set_index("id").loc[x, "name"],
            )
        with colp2:
            qty = st.number_input("Số lượng", min_value=1, value=1, step=1)
        with colp3:
            if st.button("Thêm vào đơn"):
                product_row = products_df.set_index("id").loc[product_id]
                if qty > product_row["stock"]:
                    st.warning("Tồn kho không đủ.")
                else:
                    st.session_state.order_items.append(
                        {
                            "product_id": int(product_id),
                            "name": product_row["name"],
                            "price": float(product_row["price"]),
                            "qty": int(qty),
                        }
                    )

        if st.session_state.order_items:
            items_df = pd.DataFrame(st.session_state.order_items)
            items_df["Thành tiền"] = items_df["price"] * items_df["qty"]
            st.dataframe(
                items_df[["name", "price", "qty", "Thành tiền"]],
                use_container_width=True,
            )
            total = float(items_df["Thành tiền"].sum())
            st.write(f"Tổng cộng: **{total:,.0f}**")

            colc1, colc2 = st.columns(2)
            with colc1:
                if st.button("Xóa danh sách"):
                    st.session_state.order_items = []
            with colc2:
                if st.button("Tạo đơn hàng"):
                    if selected_customer == "Khách lẻ":
                        customer_id = get_or_create_walkin_customer_id()
                    else:
                        customer_id = customer_map[selected_customer]
                    order_id = execute(
                        "INSERT INTO orders (customer_id, order_date, status, total) VALUES (?, ?, ?, ?)",
                        (int(customer_id), order_date.isoformat(), "Đã tạo", total),
                    )
                    rows = [
                        (order_id, item["product_id"], item["qty"], item["price"])
                        for item in st.session_state.order_items
                    ]
                    execute_many(
                        "INSERT INTO order_items (order_id, product_id, qty, price) VALUES (?, ?, ?, ?)",
                        rows,
                    )
                    for item in st.session_state.order_items:
                        execute(
                            "UPDATE products SET stock = stock - ? WHERE id = ?",
                            (item["qty"], item["product_id"]),
                        )
                    st.session_state.order_items = []
                    st.success("Đã tạo đơn hàng và cập nhật tồn kho.")

    st.subheader("Danh sách đơn hàng")
    orders_df = fetch_df(
        """
        SELECT o.id, o.order_date, o.status, o.total,
               c.name AS customer
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        ORDER BY o.id DESC
        """
    )
    st.dataframe(orders_df, use_container_width=True)


with tabs[4]:
    st.markdown(
        '<div class="section-card tone-red"><div class="section-title">'
        '<span class="badge badge-red">Hóa đơn</span></div></div>',
        unsafe_allow_html=True,
    )
    st.subheader("Hóa đơn")
    orders_df = fetch_df(
        """
        SELECT o.id, o.order_date, o.total, o.status, c.name AS customer
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        ORDER BY o.id DESC
        """
    )
    if orders_df.empty:
        st.info("Chưa có hóa đơn.")
    else:
        order_map = (
            orders_df["id"].astype(str)
            + " - "
            + orders_df["customer"].astype(str)
            + " ("
            + orders_df["order_date"].astype(str)
            + ")"
        ).tolist()
        selected = st.selectbox("Chọn hóa đơn", order_map)
        order_id = int(selected.split(" - ")[0])
        invoice_df = fetch_df(
            """
            SELECT p.name AS 'Sản phẩm', i.qty AS 'Số lượng',
                   i.price AS 'Đơn giá', (i.qty * i.price) AS 'Thành tiền'
            FROM order_items i
            JOIN products p ON i.product_id = p.id
            WHERE i.order_id = ?
            """,
            (order_id,),
        )
        st.dataframe(invoice_df, use_container_width=True)
        total = float(invoice_df["Thành tiền"].sum()) if not invoice_df.empty else 0
        st.markdown(
            f"**Tổng tiền:** {total:,.0f} | **Trạng thái:** "
            f"{orders_df.set_index('id').loc[order_id, 'status']}"
        )


with tabs[5]:
    st.markdown(
        '<div class="section-card tone-teal"><div class="section-title">'
        '<span class="badge badge-teal">Báo cáo</span></div></div>',
        unsafe_allow_html=True,
    )
    st.subheader("Báo cáo doanh thu")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Từ ngày", value=date.today())
    with col2:
        end_date = st.date_input("Đến ngày", value=date.today())

    sales_df = fetch_df(
        """
        SELECT order_date AS 'Ngày', SUM(total) AS 'Doanh thu'
        FROM orders
        WHERE order_date BETWEEN ? AND ?
        GROUP BY order_date
        ORDER BY order_date
        """,
        (start_date.isoformat(), end_date.isoformat()),
    )
    st.dataframe(sales_df, use_container_width=True)

    st.subheader("Top sản phẩm bán chạy")
    top_df = fetch_df(
        """
        SELECT p.name AS 'Sản phẩm', SUM(i.qty) AS 'Số lượng bán',
               SUM(i.qty * i.price) AS 'Doanh thu'
        FROM order_items i
        JOIN products p ON i.product_id = p.id
        GROUP BY p.id
        ORDER BY SUM(i.qty) DESC
        LIMIT 10
        """
    )
    st.dataframe(top_df, use_container_width=True)


with tabs[6]:
    st.markdown(
        '<div class="section-card tone-gold"><div class="section-title">'
        '<span class="badge badge-gold">Nhập Excel</span></div></div>',
        unsafe_allow_html=True,
    )
    st.subheader("Nhập dữ liệu từ Excel")
    st.caption("Hỗ trợ nhập Sản phẩm và Khách hàng từ file .xlsx")

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Nhập Sản phẩm")
    product_file = st.file_uploader("Chọn file Excel sản phẩm", type=["xlsx"], key="import_products")
    if product_file is not None:
        try:
            prod_df = pd.read_excel(product_file, dtype=str).fillna("")
        except Exception as exc:
            st.error(f"Không đọc được file Excel: {exc}")
        else:
            st.dataframe(prod_df, use_container_width=True)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                name_col = st.selectbox("Cột Tên sản phẩm", prod_df.columns, key="p_name")
            with col2:
                sku_col = st.selectbox("Cột SKU", prod_df.columns, key="p_sku")
            with col3:
                price_col = st.selectbox("Cột Giá", prod_df.columns, key="p_price")
            with col4:
                stock_col = st.selectbox("Cột Tồn kho", prod_df.columns, key="p_stock")
            if st.button("Nhập sản phẩm"):
                rows = []
                for _, r in prod_df.iterrows():
                    name_val = str(r[name_col]).strip()
                    if not name_val:
                        continue
                    rows.append(
                        (
                            name_val,
                            str(r[sku_col]).strip() or None,
                            float(str(r[price_col]).strip() or 0),
                            int(float(str(r[stock_col]).strip() or 0)),
                            date.today().isoformat(),
                        )
                    )
                if rows:
                    execute_many(
                        "INSERT INTO products (name, sku, price, stock, created_at) VALUES (?, ?, ?, ?, ?)",
                        rows,
                    )
                    st.success(f"Đã nhập {len(rows)} sản phẩm.")
                else:
                    st.warning("Không có dữ liệu hợp lệ để nhập.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### Nhập Khách hàng")
    customer_file = st.file_uploader("Chọn file Excel khách hàng", type=["xlsx"], key="import_customers")
    if customer_file is not None:
        try:
            cust_df = pd.read_excel(customer_file, dtype=str).fillna("")
        except Exception as exc:
            st.error(f"Không đọc được file Excel: {exc}")
        else:
            st.dataframe(cust_df, use_container_width=True)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                cname_col = st.selectbox("Cột Họ tên", cust_df.columns, key="c_name")
            with col2:
                phone_col = st.selectbox("Cột SĐT", cust_df.columns, key="c_phone")
            with col3:
                email_col = st.selectbox("Cột Email", cust_df.columns, key="c_email")
            with col4:
                addr_col = st.selectbox("Cột Địa chỉ", cust_df.columns, key="c_addr")
            if st.button("Nhập khách hàng"):
                rows = []
                for _, r in cust_df.iterrows():
                    name_val = str(r[cname_col]).strip()
                    if not name_val:
                        continue
                    rows.append(
                        (
                            name_val,
                            str(r[phone_col]).strip() or None,
                            str(r[email_col]).strip() or None,
                            str(r[addr_col]).strip() or None,
                            date.today().isoformat(),
                        )
                    )
                if rows:
                    execute_many(
                        "INSERT INTO customers (name, phone, email, address, created_at) VALUES (?, ?, ?, ?, ?)",
                        rows,
                    )
                    st.success(f"Đã nhập {len(rows)} khách hàng.")
                else:
                    st.warning("Không có dữ liệu hợp lệ để nhập.")
    st.markdown("</div>", unsafe_allow_html=True)
