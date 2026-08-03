# Carts app contributor guide

## Responsibility

`carts` maintains both anonymous session carts and authenticated user carts. It
also merges a guest cart into the user's cart after OTP login.

## Module map

- `models.py`: cart ownership/token and product line items.
- `services.py`: cart lookup/creation, login merge, and response DTO calculation.
- `views.py`: read/add/update/delete endpoints.
- `admin.py`: basic operational inspection.
- `urls.py`: routes under `/api/`.

## Data model

`Cart.token` is a UUID used as the anonymous session reference. `Cart.user` is
nullable and one-to-one: a user can own at most one cart. A guest cart has no user.
The model timestamps creation/update for operational visibility.

`CartItem` links a cart and product with positive quantity. The unique constraint
on `(cart, product)` makes one line per product the database invariant. The views
still check/update an existing line for friendly behavior, but the constraint
protects races and future callers.

## Resolving a current cart

`SESSION_KEY = "cart_token"` is the only session pointer. `get_current_cart()`
prefers the authenticated user's cart, then tries the session token. It refuses
to expose a token-selected cart owned by a different user; possession of a stale
or copied session token must not bypass ownership.

`get_or_create_cart()` reuses that result or creates a user/guest cart and stores
its token in the session. Avoid creating a cart for read-only requests: `CartView`
returns an empty DTO when none exists.

## Guest-to-user merge

`merge_guest_cart_into_user()` runs after OTP authentication and is atomic. It
locks the user first so two different guest carts logging into the same account
cannot both create/claim conflicting one-to-one carts. It then locks cart and item
rows before mutation.

- If the guest cart is already the user's cart, nothing changes.
- If the token references someone else's cart, the unsafe session pointer is removed.
- If the user has no cart, ownership transfers without copying rows.
- If the user has a cart, quantities for matching products are added and other
  lines are moved by creation; the old guest cart is deleted.
- The session token is updated to the surviving user cart.

The login view deliberately catches merge database errors after successful OTP
authentication. A cart failure must not consume a valid login result or force the
user to request another OTP. Preserve that boundary when changing the flow.

## Cart DTO and pricing

`cart_dto()` returns a transport representation, not a model serializer. Each line
contains `id`, `qty`, and the canonical `product_dto()`. It calculates:

- `itemsCount`: sum of quantities.
- `itemsPrice`: sum using `oldPrice` when present, otherwise current price.
- `totalPrice`: sum using current price.
- `discount`: display-price total minus current total.

The queryset selects product/category and prefetches images to avoid N+1 queries.
These totals are suitable for cart display only. Checkout recalculates and locks
prices/stock in the orders app; never trust client totals or an earlier cart DTO.

## APIs

- `GET /api/cart`: current cart or an empty representation.
- `POST /api/cart/items`: validate `productId` and `qty`, ensure the product
  exists and requested total quantity does not exceed stock, then create/update.
- `PATCH /api/cart/items/<line-id>`: validate quantity and stock, scoped to the
  current cart.
- `DELETE /api/cart/items/<line-id>`: scoped deletion.

DRF serializers validate primitive input. Item lookup must always include the
current cart; looking up only by line ID would permit horizontal cart access.

## Contributing safely

1. Keep anonymous identity in the server session, never accept arbitrary cart
   ownership from request JSON.
2. Preserve the one-cart-per-user and one-line-per-product constraints.
3. Lock in a consistent order during merges to reduce deadlocks.
4. Treat cart stock checks as UX hints; checkout remains authoritative.
5. Keep cart response fields compatible with the frontend and `product_dto()`.
6. Add focused tests for cart endpoints/merge when changing this app (it currently
   relies heavily on account integration tests).
7. Run `./.venv/bin/python manage.py test carts accounts --verbosity 2`.

