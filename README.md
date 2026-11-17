# Flask Inventory Management System

Small retail inventory tool. Employees can list, add, edit, and delete products through a Flask API. Product details can also be pulled from [OpenFoodFacts](https://world.openfoodfacts.org/) by barcode or name and saved into the local inventory.

Inventory is stored in a Python list in `app/storage.py`. Each item has an `id`. Restarting the server puts the three sample products back.

## Setup

Use Python 3.10 or newer.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS or Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Start the API with debug mode on:

```bash
flask --app app run --debug
```

The server listens on `http://127.0.0.1:5000`.

In a second terminal, with the same virtual environment active:

```bash
python cli.py
```

Run the tests:

```bash
pytest
```

## Stored product

Each record in the inventory array looks like this:

```json
{
  "id": 1,
  "barcode": "0041220576924",
  "product_name": "Organic Almond Milk",
  "brands": "Silk",
  "ingredients_text": "Filtered water, almonds, cane sugar, ...",
  "categories": "Plant-based foods, Beverages, Plant milks",
  "image_url": "",
  "price": 3.49,
  "quantity": 24
}
```

`id` is assigned by the app. `price` and `quantity` are shop fields. The other fields match what OpenFoodFacts returns for a product.

## API routes

| Method | Path | Body / query | Result |
| --- | --- | --- | --- |
| GET | `/inventory` | none | All items. Does not change data. |
| GET | `/inventory/<id>` | none | One item, or 404. |
| POST | `/inventory` | JSON product | Appends an item and returns it with a new id. |
| PATCH | `/inventory/<id>` | JSON fields to change | Updates that item. Send `price` and/or `quantity` to change the shop values. |
| DELETE | `/inventory/<id>` | none | Removes that item from the array. |
| GET | `/lookup/barcode/<barcode>` | none | Reads OpenFoodFacts. Does not save anything. |
| GET | `/lookup/name?name=` | query `name` | Up to five OpenFoodFacts matches. Does not save anything. |
| POST | `/inventory/import` | barcode or name, plus price and quantity | Reads OpenFoodFacts, then appends the product. |

POST `/inventory` example:

```json
{
  "product_name": "Oat Milk",
  "brands": "Oatly",
  "barcode": "1234567890123",
  "ingredients_text": "Oat base, water",
  "price": 4.5,
  "quantity": 10
}
```

`product_name`, `price`, and `quantity` are required. Price cannot be negative. Quantity has to be a whole number.

PATCH `/inventory/1` example:

```json
{
  "price": 3.99,
  "quantity": 20
}
```

POST `/inventory/import` example:

```json
{
  "barcode": "0041220576924",
  "price": 3.49,
  "quantity": 12
}
```

Send `name` instead of `barcode` to import the first name match. Do not send both.

Failed lookups return 404. If OpenFoodFacts cannot be reached, the lookup and import routes return 502.

These same requests can be sent from Postman. Set the method and URL, choose Body → raw → JSON for POST and PATCH, and point at `http://127.0.0.1:5000`.

## CLI

The menu talks to the API above. Start the Flask server first.

```bash
python cli.py
```

| Menu option | Route it calls | When it runs |
| --- | --- | --- |
| 1. View all items | GET `/inventory` | Any time you want the current list |
| 2. View one item | GET `/inventory/<id>` | When you know the id |
| 3. Add item | POST `/inventory` | When the product is typed in by hand |
| 4. Update price or stock | PATCH `/inventory/<id>` | When price or quantity changes |
| 5. Delete item | DELETE `/inventory/<id>` | When a product should leave the list |
| 6. Find product | GET `/lookup/barcode/<barcode>` or GET `/lookup/name` | When you only want to read OpenFoodFacts |
| 7. Import product | lookup routes, then POST `/inventory/import` | When a found product should be saved, with a price and quantity |

The same actions work as commands:

```bash
python cli.py list
python cli.py view 1
python cli.py add --name "Oat Milk" --brand "Oatly" --price 4.50 --quantity 10
python cli.py update 1 --price 3.99 --quantity 20
python cli.py delete 3
python cli.py find --barcode 0041220576924
python cli.py find --name "almond milk"
python cli.py import --barcode 0041220576924 --price 3.49 --quantity 12
python cli.py import --name "almond milk" --price 3.49 --quantity 12
```

If the API is down, or the id is wrong, the CLI prints `Error:` and keeps going when you are in the menu. A bad command exits with status 1.

Set `INVENTORY_API_URL` if the API is not on `http://127.0.0.1:5000`.

## Tests

`tests/test_inventory.py` covers the CRUD routes.

`tests/test_openfoodfacts.py` covers barcode and name lookup, importing a product into the array, and a failed external call. `unittest.mock` is provided by pytest's `monkeypatch`, which replaces `requests.get` so the tests do not hit OpenFoodFacts.

`tests/test_cli.py` covers the list, add, update, delete, find, and import commands, plus the menu path that saves an OpenFoodFacts product.

## Project layout

```text
app/storage.py         sample inventory array and validation
app/inventory.py       CRUD routes
app/openfoodfacts.py   OpenFoodFacts client
app/lookup.py          lookup and import routes
cli.py                 menu and commands
tests/                 pytest suite
```
