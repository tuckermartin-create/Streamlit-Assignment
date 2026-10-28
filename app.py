from __future__ import annotations

import hmac
import os
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import streamlit as st
from httpx import HTTPError
from postgrest.exceptions import APIError
from streamlit.errors import StreamlitSecretNotFoundError
from supabase import SupabaseException

import database


def setting(name: str) -> str | None:
    environment_value = os.getenv(name)
    if environment_value:
        return environment_value

    try:
        value = st.secrets.get(name)
    except StreamlitSecretNotFoundError:
        return None
    return str(value) if value else None


def value_from(record: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in record:
            return record[name]
    return default


def as_decimal(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ValueError("A database price was not a valid number.") from error
    if not result.is_finite():
        raise ValueError("A database price was not a finite number.")
    return result


def money(value: Decimal | Any) -> str:
    return f"${as_decimal(value):,.2f}"


def customer_id(customer: dict[str, Any]) -> Any:
    return value_from(customer, "customer_id", "id")


def customer_name(customer: dict[str, Any]) -> str:
    return str(value_from(customer, "customer_name", "name", default=""))


def product_id(product: dict[str, Any]) -> Any:
    return value_from(product, "product_id", "id")


def product_name(product: dict[str, Any]) -> str:
    return str(value_from(product, "product_name", "name", default=""))


def order_id_field(order: dict[str, Any]) -> tuple[str, Any] | None:
    for name in ("order_id", "id"):
        if name in order:
            return name, order[name]
    return None


def order_table(
    orders: list[dict[str, Any]],
    customers_by_id: dict[str, dict[str, Any]],
    products_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for order in orders:
        customer = customers_by_id.get(
            str(value_from(order, "customer_id")), {}
        )
        product = products_by_id.get(str(value_from(order, "product_id")), {})
        quantity = int(value_from(order, "quantity", default=0))
        unit_price = as_decimal(value_from(order, "unit_price", default=0))
        identifier = value_from(order, "order_id", "id", default="")
        rows.append(
            {
                "Order ID": identifier,
                "Customer": customer_name(customer)
                or value_from(order, "customer_id", default=""),
                "Product": product_name(product)
                or value_from(order, "product_id", default=""),
                "Quantity": quantity,
                "Unit Price": money(unit_price),
                "Total": money(unit_price * quantity),
                "Order Date": value_from(order, "order_date", default=""),
            }
        )
    return rows


def refresh_confirmation() -> None:
    st.session_state.confirmation_nonce = uuid.uuid4().hex
    st.session_state.pop("price_change_notice_for", None)


def load_data(client: Any) -> tuple[list[dict[str, Any]], ...]:
    return (
        database.fetch_customers(client),
        database.fetch_products(client),
        database.fetch_orders(client),
    )


st.set_page_config(page_title="Fairfield Order Entry", page_icon="🛒")
st.title("Fairfield University Order Entry")
st.write(
    "Select a customer and product, review the current price, and confirm "
    "the order before it is saved to Supabase."
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    app_password = setting("APP_PASSWORD")
    if not app_password:
        st.error(
            "The app is not configured. Add APP_PASSWORD to Streamlit secrets "
            "or the local environment before accessing the order system."
        )
        st.stop()

    with st.form("access_form"):
        entered_password = st.text_input("App password", type="password")
        access_submitted = st.form_submit_button("Continue")
    if access_submitted:
        if hmac.compare_digest(entered_password, app_password):
            st.session_state.authenticated = True
            st.rerun()
        st.error("Incorrect password. Please try again.")
    st.stop()

supabase_url = setting("SUPABASE_URL")
supabase_key = setting("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    st.error(
        "Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY in "
        "Streamlit secrets or the local environment."
    )
    st.stop()

try:
    client = database.create_supabase_client(supabase_url, supabase_key)
except (APIError, HTTPError, SupabaseException, ValueError) as error:
    st.error(f"Could not connect to Supabase: {error}")
    st.stop()

if "customers" not in st.session_state:
    try:
        (
            st.session_state.customers,
            st.session_state.products,
            st.session_state.orders,
        ) = load_data(client)
    except (APIError, HTTPError) as error:
        st.error(f"Could not load data from Supabase: {error}")
        st.stop()

if "confirmation_nonce" not in st.session_state:
    st.session_state.confirmation_nonce = uuid.uuid4().hex
if "price_overrides" not in st.session_state:
    st.session_state.price_overrides = {}

if st.button("Refresh Data"):
    try:
        (
            st.session_state.customers,
            st.session_state.products,
            st.session_state.orders,
        ) = load_data(client)
        st.session_state.price_overrides = {}
        st.session_state.history_error = None
        refresh_confirmation()
        st.success("Customer, product, and order data refreshed.")
    except (APIError, HTTPError) as error:
        st.error(f"Could not refresh data from Supabase: {error}")

customers = st.session_state.customers
products = st.session_state.products
orders = st.session_state.orders
customers_by_id = {str(customer_id(item)): item for item in customers}
products_by_id = {str(product_id(item)): item for item in products}
if not customers:
    st.warning("No customers were returned by Supabase.")
if not products:
    st.warning("No products were returned by Supabase.")

st.header("Customers")
st.dataframe(
    [
        {
            "Customer ID": customer_id(customer),
            "Customer Name": customer_name(customer),
        }
        for customer in customers
    ],
    width="stretch",
    hide_index=True,
)

st.header("Products")
st.dataframe(
    [
        {
            "Product ID": product_id(product),
            "Product Name": product_name(product),
            "Category": value_from(product, "category", default=""),
            "Price": money(value_from(product, "price", default=0)),
        }
        for product in products
    ],
    width="stretch",
    hide_index=True,
)

st.header("Create an Order")
if customers and products:
    selected_customer_id = st.selectbox(
        "Customer",
        options=[customer_id(item) for item in customers],
        format_func=lambda identifier: (
            f"{customer_name(customers_by_id[str(identifier)])} "
            f"(ID: {identifier})"
        ),
        key="selected_customer",
        on_change=refresh_confirmation,
    )
    selected_product_id = st.selectbox(
        "Product",
        options=[product_id(item) for item in products],
        format_func=lambda identifier: (
            f"{product_name(products_by_id[str(identifier)])} "
            f"(ID: {identifier})"
        ),
        key="selected_product",
        on_change=refresh_confirmation,
    )
    quantity = st.number_input(
        "Quantity",
        min_value=1,
        step=1,
        value=1,
        key="order_quantity",
        on_change=refresh_confirmation,
    )

    selected_customer = customers_by_id[str(selected_customer_id)]
    selected_product = products_by_id[str(selected_product_id)]
    override = st.session_state.price_overrides.get(str(selected_product_id))
    displayed_price = as_decimal(
        override
        if override is not None
        else value_from(selected_product, "price", default=0)
    )
    total = displayed_price * int(quantity)

    st.subheader("Review Order")
    st.write(f"**Customer:** {customer_name(selected_customer)}")
    st.write(f"**Product:** {product_name(selected_product)}")
    st.write(f"**Quantity:** {quantity}")
    st.write(f"**Unit price:** {money(displayed_price)}")
    st.write(f"**Total:** {money(total)}")
    if st.session_state.get("price_change_notice_for") == str(
        selected_product_id
    ):
        st.warning(
            "The product price changed. Review the updated total and confirm "
            "the order again."
        )

    confirmation_key = f"confirm_order_{st.session_state.confirmation_nonce}"
    confirmed = st.checkbox(
        "I have reviewed these details and confirm this order.",
        key=confirmation_key,
    )

    if st.button("Submit Order", type="primary"):
        if (
            not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or quantity < 1
        ):
            st.error("Quantity must be a positive whole number.")
        elif not confirmed:
            st.error("Confirm the reviewed order before submitting it.")
        else:
            try:
                latest_product = database.fetch_product(
                    client, selected_product_id
                )
                latest_price = as_decimal(
                    value_from(latest_product, "price", default=None)
                )
                if latest_price != displayed_price:
                    st.session_state.price_overrides[
                        str(selected_product_id)
                    ] = str(latest_price)
                    refresh_confirmation()
                    st.session_state.price_change_notice_for = str(
                        selected_product_id
                    )
                    st.rerun()

                inserted_order = database.insert_order(
                    client,
                    selected_customer_id,
                    selected_product_id,
                    quantity,
                    float(latest_price),
                    date.today().isoformat(),
                )
            except (APIError, HTTPError, RuntimeError, ValueError) as error:
                st.error(f"The order could not be saved: {error}")
            else:
                st.session_state.last_saved = True
                st.session_state.last_verification = None
                identifier = order_id_field(inserted_order)
                refresh_confirmation()

                try:
                    if identifier is None:
                        raise RuntimeError(
                            "Supabase saved the order but did not return its "
                            "generated order ID."
                        )
                    id_column, generated_id = identifier
                    saved_order = database.fetch_order_by_id(
                        client, id_column, generated_id
                    )
                    st.session_state.last_verification = saved_order
                    st.session_state.last_verification_error = None
                except (APIError, HTTPError, RuntimeError) as error:
                    st.session_state.last_verification_error = str(error)

                try:
                    st.session_state.orders = database.fetch_orders(client)
                except (APIError, HTTPError) as error:
                    st.session_state.history_error = str(error)
                else:
                    st.session_state.history_error = None

                st.rerun()
else:
    st.info("Add at least one customer and one product in Supabase to place orders.")

if st.session_state.get("last_saved"):
    st.success("Order saved successfully.")
    verification = st.session_state.get("last_verification")
    if verification:
        saved_customer = customers_by_id.get(
            str(value_from(verification, "customer_id")), {}
        )
        saved_product = products_by_id.get(
            str(value_from(verification, "product_id")), {}
        )
        saved_quantity = int(value_from(verification, "quantity", default=0))
        stored_unit_price = as_decimal(
            value_from(verification, "unit_price", default=0)
        )
        st.subheader("Saved Order Verification")
        st.dataframe(
            [
                {
                    "Order ID": value_from(
                        verification, "order_id", "id", default=""
                    ),
                    "Customer": customer_name(saved_customer)
                    or value_from(verification, "customer_id", default=""),
                    "Product": product_name(saved_product)
                    or value_from(verification, "product_id", default=""),
                    "Quantity": saved_quantity,
                    "Unit Price": money(stored_unit_price),
                    "Total": money(stored_unit_price * saved_quantity),
                    "Order Date": value_from(
                        verification, "order_date", default=""
                    ),
                }
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.warning(
            "The order was saved, but it could not be retrieved for "
            "verification. Do not submit it again."
        )
        if st.session_state.get("last_verification_error"):
            st.caption(st.session_state.last_verification_error)

st.header("Order History")
customer_filter_options = ["All customers"] + [
    customer_id(item) for item in customers
]
selected_history_customer = st.selectbox(
    "Filter by customer",
    options=customer_filter_options,
    format_func=lambda identifier: (
        "All customers"
        if identifier == "All customers"
        else (
            f"{customer_name(customers_by_id[str(identifier)])} "
            f"(ID: {identifier})"
        )
    ),
)

history_orders = orders
if selected_history_customer != "All customers":
    history_orders = [
        order
        for order in orders
        if str(value_from(order, "customer_id"))
        == str(selected_history_customer)
    ]

st.dataframe(
    order_table(history_orders, customers_by_id, products_by_id),
    width="stretch",
    hide_index=True,
)
history_total = sum(
    (
        as_decimal(value_from(order, "unit_price", default=0))
        * int(value_from(order, "quantity", default=0))
        for order in history_orders
    ),
    Decimal("0"),
)
st.write(f"**Order history total:** {money(history_total)}")
if st.session_state.get("history_error"):
    st.warning(
        "The order was saved, but order history could not be refreshed: "
        f"{st.session_state.history_error}"
    )
