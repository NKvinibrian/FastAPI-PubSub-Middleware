"""
Builders de mutations GraphQL para o Observer.

Cada action do Observer mapeia para uma mutation específica da VAN.
O payload já contém os dados prontos — os builders apenas formatam
como string GraphQL.
"""

from app.api.v1.schemas.vans.observer_message import ObserverAction


def build_graphql_mutation(action: ObserverAction, payload: dict) -> str:
    """
    Monta a mutation GraphQL a partir do action e payload.

    Cada action mapeia para uma mutation específica da VAN.
    """
    if action in (ObserverAction.ORDER_RETURN, ObserverAction.ORDER_RETURN_REJECTION):
        return _build_create_response_mutation(payload)
    elif action == ObserverAction.RETURN_INVOICES:
        return _build_create_invoice_mutation(payload)
    elif action == ObserverAction.RETURN_CANCELLATION:
        return _build_create_cancellation_mutation(payload)
    else:
        raise ValueError(f"Unsupported action for GraphQL: {action.value}")


def _gql_str(v) -> str:
    """Formata valor para GraphQL: string entre aspas, null se None."""
    return "null" if v is None else f'"{v}"'


def _gql_num(v) -> str:
    """Formata valor numérico para GraphQL."""
    return "null" if v is None else str(v)


def _build_create_response_mutation(payload: dict) -> str:
    """Monta mutation createResponse a partir do payload."""
    products_parts = []
    for p in payload.get("products", []):
        products_parts.append(
            "{"
            f'ean: "{p.get("ean", "")}", '
            f'response_amount: {_gql_num(p.get("response_amount"))}, '
            f'unit_discount_percentage: {_gql_num(p.get("unit_discount_percentage"))}, '
            f'unit_discount_value: {_gql_num(p.get("unit_discount_value"))}, '
            f'unit_net_value: {_gql_num(p.get("unit_net_value"))}, '
            f'monitored: {str(p.get("monitored", False)).lower()}, '
            f'industry_consideration: {_gql_str(p.get("industry_consideration"))}'
            "}"
        )
    products_block = ", ".join(products_parts)

    args = [
        f'industry_code: "{payload.get("industry_code", "")}"',
        f'order_code: {int(payload.get("order_code"))}',
        f'wholesaler_code: "{payload.get("wholesaler_code", "")}"',
        f'processed_at: "{payload.get("processed_at", "")}"',
        f'reason: {payload.get("reason")}',
    ]
    if payload.get("wholesaler_order_code"):
        args.append(f'wholesaler_order_code: "{payload["wholesaler_order_code"]}"')
    if payload.get("payment_term"):
        args.append(f'payment_term: "{payload["payment_term"]}"')
    if payload.get("invoice_at"):
        args.append(f'invoice_at: "{payload["invoice_at"]}"')
    if payload.get("delivery_forecast_at"):
        args.append(f'delivery_forecast_at: "{payload["delivery_forecast_at"]}"')
    args.append(f"products: [ {products_block} ]")

    return (
        "mutation createResponse {\n"
        "  createResponse(\n    " + ",\n    ".join(args) + "\n  ) {\n"
        "    id\n    content\n    imported_at\n    outcome\n"
        "  }\n}"
    )


def _build_create_invoice_mutation(payload: dict) -> str:
    """Monta mutation createInvoice a partir do payload."""
    products_parts = []
    for p in payload.get("products", []):
        products_parts.append(
            "{"
            f'ean: "{p.get("ean", "")}", '
            f'invoice_amount: {_gql_num(p.get("invoice_amount"))}, '
            f'unit_discount_percentage: {_gql_num(p.get("unit_discount_percentage"))}, '
            f'unit_discount_value: {_gql_num(p.get("unit_discount_value"))}, '
            f'unit_net_value: {_gql_num(p.get("unit_net_value"))}'
            "}"
        )
    products_block = ", ".join(products_parts)

    args = [
        f'industry_code: "{payload.get("industry_code", "")}"',
        f'order_code: {int(payload.get("order_code"))}',
        f'wholesaler_code: "{payload.get("wholesaler_code", "")}"',
        f'customer_code: "{payload.get("customer_code", "")}"',
        f'processed_at: "{payload.get("processed_at", "")}"',
        f'invoice_released_on: "{payload.get("invoice_released_on", "")}"',
        f'invoice_code: "{payload.get("invoice_code", "")}"',
        f'invoice_value: {float(payload.get("invoice_value", 0))}',
        f'invoice_discount: {float(payload.get("invoice_discount", 0))}',
        f'invoice_danfe_key: "{payload.get("invoice_danfe_key", "")}"',
        f"products: [ {products_block} ]",
    ]
    if payload.get("wholesaler_order_code"):
        args.append(f'wholesaler_order_code: "{payload["wholesaler_order_code"]}"')

    return (
        "mutation createInvoice {\n"
        "  createInvoice(\n    " + ",\n    ".join(args) + "\n  ) {\n"
        "    id\n    content\n    imported_at\n    outcome\n"
        "  }\n}"
    )


def _build_create_cancellation_mutation(payload: dict) -> str:
    """Monta mutation createCancellation a partir do payload."""
    products_parts = [
        f'{{ ean: "{p.get("ean", "")}" }}'
        for p in payload.get("products", [])
    ]
    args = [
        f'order_code: {int(payload.get("order_code"))}',
        f'industry_code: "{payload.get("industry_code", "")}"',
        f'wholesaler_branch_code: "{payload.get("wholesaler_branch_code", "")}"',
        f"products: [ {', '.join(products_parts)} ]",
    ]

    return (
        "mutation createCancellation {\n"
        "  createCancellation(\n    " + ",\n    ".join(args) + "\n  ) {\n"
        "    id\n    content\n    imported_at\n    outcome\n"
        "  }\n}"
    )
