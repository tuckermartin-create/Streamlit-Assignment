# Fairfield University Order Entry

A password-protected Streamlit order-entry app that reads customers and
products from Supabase, saves one-product orders, retrieves each saved order
again for verification, and displays order history.

## Application and repository links

- Deployed application: https://app-assignment-jt3fmvdhwrvwdf4hmvxfdr.streamlit.app/
- GitHub repository: https://github.com/tuckermartin-create/Streamlit-Assignment

## Supabase schema

The app expects these tables and columns. The classroom project was set up
with fictional customers and products:

- `customers`: `customer_id`, `customer_name`
- `products`: `product_id`, `product_name`, `category`, `price`
- `orders`: generated `order_id`, `customer_id`, `product_id`, `quantity`,
  `unit_price`, `order_date`

Sample rows are Jordan Lee, Casey Morgan, and Taylor Rivera; products are
Notebook, Fairfield Hoodie, Campus Mug, and Blue Pen Set.

If the existing tables use different column names, update the corresponding
queries in `database.py` and the matching column lookups in `app.py`. The
`orders` table must have a generated ID and customer/product ID columns.

## Run locally

1. Use the fictional classroom Supabase data and a Python version supported
   by Streamlit.
2. Install packages: `pip install -r requirements.txt`.
3. Copy `.streamlit/secrets.toml.example` to
   `.streamlit/secrets.toml` and replace the placeholders with the Supabase
   project URL, the privileged classroom API key, and a strong app password.
   Never commit the populated secrets file.
4. Start the app: `streamlit run app.py`.
5. In Streamlit, enter the app password before using the database-backed
   interface.

Environment variables named `SUPABASE_URL`, `SUPABASE_KEY`, and
`APP_PASSWORD` can be used instead of Streamlit secrets.

## Streamlit Community Cloud deployment

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create an app from this repository, select
   the deployment branch, and set `app.py` as the entry point.
3. Add `SUPABASE_URL`, `SUPABASE_KEY`, and `APP_PASSWORD` under the app's
   **Settings > Secrets**. Use only the fictional classroom database. Do not
   commit credentials or paste them into source files.
4. Deploy and test the hosted URL shown above.
5. Provide the instructor the app password privately through the course
   submission system, or configure private viewer access.

The password check runs before the app creates a Supabase client or makes any
database request. This is classroom access control, not a production
authentication system.

## How the order flow works

- `app.py` collects customer, product, and positive whole-number quantity
  using Streamlit widgets, then presents a review and confirmation checkbox.
- `database.py` uses the Supabase Python client to retrieve the current
  product price, insert the confirmed order with today's date, and fetch the
  generated order ID again with a separate API query.
- If the price differs from the displayed price at submission, the updated
  price is shown and the user must confirm again.
- Successful inserts refresh order history. A rerun or widget interaction
  alone never inserts an order.
- Verification and history totals use the order's stored `unit_price`.
- Order History includes a customer filter and displays the total value for
  the visible orders.

## Testing and screenshots

The hosted app has been tested with the fictional Supabase classroom data.
The order-flow case that does not insert without confirmation was exercised
locally with a mocked Supabase client; the deployed tests are recorded below.

| Test | Result |
|---|---|
| Open hosted app with authorized access | Passed |
| Customers and products load from Supabase | Passed; 3 customers and 4 products displayed |
| Invalid quantity is prevented or rejected | Passed; number input enforces minimum 1 and whole-number steps |
| Submit without confirmation creates no order | Passed locally with mocked Supabase; submission rejected |
| Confirmed order inserts exactly once | Passed on hosted app; order ID 1, Jordan Lee, one Notebook, $4.50 |
| New order is retrieved in the verification table | Passed; saved record displayed after a separate query by generated ID |
| Widget interaction does not insert a duplicate | Passed on hosted app; Refresh Data retained the order and $4.50 total |
| Refresh shows the saved order in history | Passed |
| Customer filter and stored-price total work | Passed; filtering to Jordan Lee displayed the stored-price total of $4.50 |

Screenshots are still required for submission. Save screenshots of the hosted
order-entry interface and the successfully verified order in this repository,
then link them here. Ensure they contain no credentials.

## Libraries and techniques

- [Streamlit](https://streamlit.io/) provides the web interface, widgets,
  session state, and Community Cloud deployment.
- [Supabase Python](https://supabase.com/docs/reference/python/introduction)
  makes the database API requests.
- Python's `Decimal` is used for reliable display and calculation of money.
- `hmac.compare_digest` checks the classroom access password.
