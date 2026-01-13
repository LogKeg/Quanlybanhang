import streamlit as st
import pandas as pd
from datetime import datetime

from invoice_export import make_invoice_docx, make_invoice_pdf

st.set_page_config(page_title="CỬA HÀNG THUỐC BẢO THOA", layout="wide")

# --- Init DB
db.init_db()

# --- Session defaults
if "cart" not in st.session_state:
    st.session_state.cart = []
import json
from pathlib import Path

CONFIG_PATH = Path("shop_config.json")

def load_shop():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "name": "CỬA HÀNG",
        "phone": "0976485999",
        "address": "26 LK1, KĐT Đại Thanh, Thanh Trì, Hà Nội"
    }

def save_shop(shop: dict):
    CONFIG_PATH.write_text(
        json.dumps(shop, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

if "shop" not in st.session_state:
    st.session_state.shop = load_shop()


# --- Sidebar (giao diện như phần mềm)
st.sidebar.title("CỬA HÀNG THUỐC BẢO THOA")
page = st.sidebar.radio("Chức năng", ["Nhập hàng (Excel)", "Bán hàng", "Tồn kho", "Lịch sử đơn hàng", "Cài đặt cửa hàng"])

st.sidebar.divider()
st.sidebar.caption("Tip: Dữ liệu lưu trong file sales.db (SQLite) ngay trong thư mục dự án.")

def money(x):
    try:
        return f"{float(x):,.0f}"
    except:
        return str(x)

# =========================
# 1) Nhập hàng (Excel)
# =========================
if page == "Nhập hàng (Excel)":
    st.title("Nhập danh mục hàng từ Excel (có tồn kho)")

    st.info("File Excel cần cột: MaHang, TenHang, DonVi, DonGia, TonKho (TonKho có thể để trống).")

    uploaded = st.file_uploader("Tải file Excel hàng hóa", type=["xlsx"])

    if uploaded:
        try:
            df = pd.read_excel(uploaded)
            required = ["MaHang", "TenHang", "DonVi", "DonGia"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                st.error(f"Thiếu cột: {missing}. Bắt buộc: {required}. (TonKho là tùy chọn)")
                st.stop()

            df["MaHang"] = df["MaHang"].astype(str).str.strip()
            df["TenHang"] = df["TenHang"].astype(str).str.strip()
            df["DonVi"] = df["DonVi"].astype(str).str.strip()
            df["DonGia"] = pd.to_numeric(df["DonGia"], errors="coerce").fillna(0)

            if "TonKho" not in df.columns:
                df["TonKho"] = 0
            df["TonKho"] = pd.to_numeric(df["TonKho"], errors="coerce").fillna(0).astype(int)

            st.dataframe(df, use_container_width=True)

            if st.button("💾 Lưu vào hệ thống"):
                rows = df.to_dict(orient="records")
                db.upsert_products(rows)
                st.success(f"Đã lưu/ cập nhật {len(rows)} mặt hàng.")
        except Exception as e:
            st.error(f"Lỗi đọc Excel: {e}")

# =========================
# 2) Bán hàng
# =========================
elif page == "Bán hàng":
    st.title("Bán hàng")

    products = db.get_products()
    if not products:
        st.warning("Chưa có hàng hóa. Vào 'Nhập hàng (Excel)' để nạp danh mục.")
        st.stop()

    # Chọn hàng
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.subheader("Chọn mặt hàng")
        dfp = pd.DataFrame(products)
        search = st.text_input("Tìm theo mã / tên", value="")
        if search.strip():
            s = search.strip().lower()
            dfp2 = dfp[dfp["MaHang"].str.lower().str.contains(s) | dfp["TenHang"].str.lower().str.contains(s)]
        else:
            dfp2 = dfp

        st.dataframe(dfp2, use_container_width=True, height=260)

        label_list = [f"{r['MaHang']} - {r['TenHang']} | {r['DonVi']} | {money(r['DonGia'])} | Tồn: {r['TonKho']}" for r in products]
        pick = st.selectbox("Chọn nhanh", label_list)
        qty = st.number_input("Số lượng", min_value=1, step=1, value=1)

        if st.button("➕ Thêm vào đơn", use_container_width=True):
            mahang = pick.split(" - ")[0].strip()
            p = next(x for x in products if x["MaHang"] == mahang)
            if int(qty) > int(p["TonKho"]):
                st.error(f"Tồn kho không đủ. Hiện có {p['TonKho']}, cần {qty}.")
            else:
                st.session_state.cart.append({
                    "MaHang": p["MaHang"],
                    "TenHang": p["TenHang"],
                    "DonVi": p["DonVi"],
                    "DonGia": float(p["DonGia"]),
                    "SoLuong": int(qty),
                    "ThanhTien": float(p["DonGia"]) * int(qty),
                })
                st.success("Đã thêm vào đơn.")

    with right:
        st.subheader("Thông tin đơn")
        ma_don = st.text_input("Mã đơn", value=f"DH{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        khach = st.text_input("Khách hàng", value="Khách lẻ")
        ghi_chu = st.text_area("Ghi chú", value="")

        st.divider()

        cart_df = pd.DataFrame(st.session_state.cart)
        if cart_df.empty:
            st.info("Chưa có mặt hàng trong đơn.")
        else:
            total = float(cart_df["ThanhTien"].sum())
            st.metric("Tổng tiền", f"{total:,.0f} VND")
            st.dataframe(cart_df, use_container_width=True, height=220)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🧹 Xóa đơn"):
                    st.session_state.cart = []
                    st.rerun()

            with c2:
                if st.button("✅ Chốt đơn & Lưu lịch sử"):
                    # Trừ kho trước
                    ok_all = True
                    for _, r in cart_df.iterrows():
                        ok, msg = db.adjust_stock_delta(r["MaHang"], -int(r["SoLuong"]))
                        if not ok:
                            ok_all = False
                            st.error(msg)
                            break

                    if ok_all:
                        order_id = db.create_order(
                            ma_don=ma_don,
                            khach_hang=khach,
                            ngay_tao=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            tong_tien=total,
                            ghi_chu=ghi_chu,
                            items=cart_df.to_dict(orient="records")
                        )
                        st.success(f"Đã lưu đơn #{order_id}. Tồn kho đã được trừ.")
                        st.session_state.cart = []
                        st.rerun()

# =========================
# 3) Tồn kho
# =========================
elif page == "Tồn kho":
    st.title("Quản lý tồn kho")

    products = db.get_products()
    if not products:
        st.warning("Chưa có hàng hóa.")
        st.stop()

    dfp = pd.DataFrame(products)
    st.dataframe(dfp, use_container_width=True)

    st.subheader("Cập nhật tồn kho nhanh")
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        mahang = st.selectbox("Chọn mã hàng", [p["MaHang"] for p in products])
    with col2:
        new_stock = st.number_input("Tồn kho mới", min_value=0, step=1, value=0)
    with col3:
        if st.button("💾 Cập nhật", use_container_width=True):
            db.update_stock(mahang, int(new_stock))
            st.success("Đã cập nhật tồn kho.")
            st.rerun()

    st.subheader("Cảnh báo sắp hết hàng")
    threshold = st.number_input("Ngưỡng cảnh báo", min_value=0, step=1, value=5)
    warn = dfp[dfp["TonKho"] <= int(threshold)]
    if warn.empty:
        st.success("Không có mặt hàng dưới ngưỡng.")
    else:
        st.warning("Các mặt hàng cần nhập thêm:")
        st.dataframe(warn, use_container_width=True)

# =========================
# 4) Lịch sử đơn hàng (tải lại Word/PDF)
# =========================
elif page == "Lịch sử đơn hàng":
    st.title("Lịch sử đơn hàng")

    kw = st.text_input("Tìm đơn theo mã / khách hàng", value="")
    orders = db.list_orders(kw)
    if not orders:
        st.info("Chưa có đơn hàng.")
        st.stop()

    df = pd.DataFrame(orders)
    st.dataframe(df, use_container_width=True, height=260)

    st.subheader("Xem chi tiết & xuất lại")
    order_id = st.selectbox("Chọn Order ID", [o["id"] for o in orders])

    selected = next(o for o in orders if o["id"] == order_id)
    items = db.get_order_items(order_id)

    st.write(f"**Mã đơn:** {selected['MaDon']}  |  **Khách:** {selected['KhachHang']}  |  **Ngày:** {selected['NgayTao']}  |  **Tổng:** {money(selected['TongTien'])} VND")
    st.dataframe(pd.DataFrame(items), use_container_width=True)

    shop = st.session_state.shop
    order_info = {
        "code": selected["MaDon"],
        "customer": selected["KhachHang"],
        "date": selected["NgayTao"],
        "note": selected["GhiChu"],
    }

    colA, colB = st.columns(2)
    with colA:
        docx_bytes = make_invoice_docx(shop, order_info, items)
        st.download_button(
            "⬇️ Tải hóa đơn Word",
            data=docx_bytes,
            file_name=f"{selected['MaDon']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    with colB:
        pdf_bytes = make_invoice_pdf(shop, order_info, items)
        st.download_button(
            "⬇️ Tải hóa đơn PDF",
            data=pdf_bytes,
            file_name=f"{selected['MaDon']}.pdf",
            mime="application/pdf"
        )

# =========================
# 5) Cài đặt cửa hàng
# =========================
elif page == "Cài đặt cửa hàng":
    st.title("Cài đặt cửa hàng (hiển thị trên hóa đơn)")

    shop = st.session_state.shop
    shop["name"] = st.text_input("Tên cửa hàng", value=shop.get("name", "CỬA HÀNG"))
    shop["phone"] = st.text_input("SĐT", value=shop.get("phone", ""))
    shop["address"] = st.text_input("Địa chỉ", value=shop.get("address", ""))

    # ✅ Nút lưu xuống file shop_config.json
    if st.button("💾 Lưu thông tin cửa hàng"):
        save_shop(st.session_state.shop)
        st.success("Đã lưu. Lần sau mở app sẽ tự điền sẵn.")

    st.caption("Thông tin này sẽ dùng khi xuất hóa đơn Word/PDF.")
