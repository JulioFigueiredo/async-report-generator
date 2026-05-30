import csv
import random
from datetime import date
import calendar


PRODUCTS = ["Widget A", "Widget B", "Gadget X", "Gadget Y", "Part Z"]
CITIES = {
    "north": ["Manaus", "Belém", "Macapá", "Porto Velho"],
    "northeast": ["Salvador", "Recife", "Fortaleza", "Natal"],
    "southeast": ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Vitória"],
    "south": ["Curitiba", "Porto Alegre", "Florianópolis"],
    "midwest": ["Brasília", "Goiânia", "Campo Grande", "Cuiabá"],
}
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}
SKU_PREFIX = "SKU"


def _random_date(month: int, year: int = 2024) -> str:
    last_day = calendar.monthrange(year, month)[1]
    day = random.randint(1, last_day)
    return date(year, month, day).isoformat()


def _build_sales(region: str, month: int, output_path: str) -> None:
    columns = ["date", "product", "quantity", "unit_price", "total"]
    rows = random.randint(30, 100)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for _ in range(rows):
            quantity = random.randint(1, 50)
            unit_price = round(random.uniform(10.0, 500.0), 2)
            writer.writerow({
                "date": _random_date(month),
                "product": random.choice(PRODUCTS),
                "quantity": quantity,
                "unit_price": unit_price,
                "total": round(quantity * unit_price, 2),
            })


def _build_inventory(month: int, output_path: str) -> None:
    columns = ["sku", "product", "stock", "min_stock", "status"]
    rows = random.randint(30, 100)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for i in range(rows):
            stock = random.randint(0, 200)
            min_stock = random.randint(10, 50)
            if stock == 0:
                status = "critical"
            elif stock < min_stock:
                status = "low"
            else:
                status = "ok"
            writer.writerow({
                "sku": f"{SKU_PREFIX}-{month:02d}-{i + 1:04d}",
                "product": random.choice(PRODUCTS),
                "stock": stock,
                "min_stock": min_stock,
                "status": status,
            })


def _build_customers(region: str, output_path: str) -> None:
    columns = ["id", "name", "city", "orders", "total_spent"]
    rows = random.randint(30, 100)
    cities = CITIES.get(region, ["Unknown"])
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for i in range(rows):
            orders = random.randint(1, 30)
            writer.writerow({
                "id": i + 1,
                "name": f"Customer {i + 1}",
                "city": random.choice(cities),
                "orders": orders,
                "total_spent": round(random.uniform(50.0, 5000.0), 2),
            })


def build_report(report_type: str, region: str, month: str, output_path: str) -> None:
    """
    Generates a synthetic CSV report and writes it to output_path.
    Data is randomly generated — no external dependencies.
    """
    month_number = MONTHS[month]
    if report_type == "sales":
        _build_sales(region, month_number, output_path)
    elif report_type == "inventory":
        _build_inventory(month_number, output_path)
    elif report_type == "customers":
        _build_customers(region, output_path)
    else:
        raise ValueError(f"Unknown report_type: {report_type!r}")
