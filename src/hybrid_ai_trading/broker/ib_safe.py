def ib_place_order_chokepoint(ib, *args):
    """
    Single chokepoint for raw IB placeOrder.

    Supported call styles:
      - ib_place_order_chokepoint(ib, contract, order)                  # order_id defaults to 0
      - ib_place_order_chokepoint(ib, order_id, contract, order)         # explicit order_id

    This stays intentionally minimal. It is a seam for future enforcement/logging.
    """
    if len(args) == 2:
        contract, order = args
        order_id = 0
    elif len(args) == 3:
        order_id, contract, order = args
    else:
        raise TypeError(f"ib_place_order_chokepoint expected 2 or 3 args after ib, got {len(args)}")
    return ib.placeOrder(order_id, contract, order)
    st = tr.orderStatus
    return st.status, st.filled, st.avgFillPrice
