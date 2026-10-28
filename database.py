"""Supabase queries used by the Streamlit order-entry application."""

from typing import Any

from supabase import Client, create_client


def create_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)


def fetch_customers(client: Client) -> list[dict[str, Any]]:
    response = client.table("customers").select("*").execute()
    return response.data or []


def fetch_products(client: Client) -> list[dict[str, Any]]:
    response = client.table("products").select("*").execute()
    return response.data or []


def fetch_orders(client: Client) -> list[dict[str, Any]]:
    response = client.table("orders").select("*").execute()
    return response.data or []


def fetch_product(client: Client, product_id: Any) -> dict[str, Any]:
    response = (
        client.table("products")
        .select("*")
        .eq("product_id", product_id)
        .single()
        .execute()
    )
    return response.data


def insert_order(
    client: Client,
    customer_id: Any,
    product_id: Any,
    quantity: int,
    unit_price: float,
    order_date: str,
) -> dict[str, Any]:
    response = (
        client.table("orders")
        .insert(
            {
                "customer_id": customer_id,
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": unit_price,
                "order_date": order_date,
            }
        )
        .execute()
    )
    if not response.data:
        raise RuntimeError("Supabase did not return the inserted order record.")
    return response.data[0]


def fetch_order_by_id(
    client: Client, order_id_column: str, order_id: Any
) -> dict[str, Any]:
    response = (
        client.table("orders")
        .select("*")
        .eq(order_id_column, order_id)
        .single()
        .execute()
    )
    return response.data
