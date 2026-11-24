from decimal import Decimal
from datetime import datetime


# ==========================================
# 1. pos.domain (Business Domain Layer)
# ==========================================
class ProductDescription:
    def __init__(self, item_id, description, price, category="general"):
        self.item_id = item_id
        self.description = description
        self.price = Decimal(str(price))
        self.category = category


class SalesLineItem:
    def __init__(self, product_description, quantity):
        self.product_description = product_description
        self.quantity = quantity

    def get_subtotal(self):
        return self.product_description.price * self.quantity


class ReturnLineItem:
    def __init__(self, product_description, quantity):
        self.product_description = product_description
        self.quantity = quantity

    def get_refund(self):
        return self.product_description.price * self.quantity


class CashPayment:
    def __init__(self, tendered):
        self.tendered = Decimal(str(tendered))
        self.change = Decimal('0.00')


class Sale:
    def __init__(self):
        self.date = datetime.now()
        self.status = "OPEN"
        self.line_items = []
        self.return_line_items = []
        self.payment = None

    def add_line_item(self, product_desc, qty):
        self.line_items.append(SalesLineItem(product_desc, qty))

    def add_return_line_item(self, product_desc, qty):
        self.return_line_items.append(ReturnLineItem(product_desc, qty))

    def get_total(self):
        sales_total = sum(item.get_subtotal() for item in self.line_items)
        return_total = sum(item.get_refund() for item in self.return_line_items)
        return sales_total - return_total

    def make_payment(self, tendered):
        self.payment = CashPayment(tendered)
        self.payment.change = self.payment.tendered - self.get_total()
        self.status = "CLOSED"


# ==========================================
# 2. pos.data (Data Management Layer)
# ==========================================
class ProductCatalog:
    def __init__(self):
        self.products = {
            "1001": ProductDescription("1001", "Coffee", 20.00),
            "1002": ProductDescription("1002", "Bread", 15.19),
            "1003": ProductDescription("1003", "Milk", 12.50),
        }

    def get_product(self, item_id):
        if item_id not in self.products:
            raise ValueError(f"Item ID {item_id} not in the catalogue.")
        return self.products[item_id]


class Store:
    def __init__(self):
        self.inventory = {"1001": 10, "1002": 10, "1003": 10}

    def update_inventory(self, item_id, qty_change):
        self.inventory[item_id] += qty_change


class Ledger:
    def __init__(self):
        self.records = []

    def record_sale(self, sale):
        self.records.append(sale)


# ==========================================
# 3. pos.external (Infrastructure Layer)
# ==========================================
class ReceiptPrinter:
    @staticmethod
    def print_receipt(sale):
        print("\n" + "=" * 40)
        print("            OFFICIAL RECEIPT")
        print("=" * 40)
        for item in sale.line_items:
            print(f"{item.quantity}x {item.product_description.description:<20} ${item.get_subtotal():.2f}")
        for item in sale.return_line_items:
            print(f"REF {item.quantity}x {item.product_description.description:<16} -${item.get_refund():.2f}")
        print("-" * 40)
        print(f"NET TOTAL: ${sale.get_total():.2f}")
        if sale.payment:
            print(f"CASH:      ${sale.payment.tendered:.2f}")
            print(f"CHANGE:    ${sale.payment.change:.2f}")
        print("=" * 40 + "\n")


# ==========================================
# 4. pos.services (Application Logic Layer)
# ==========================================
class PosFacade:
    def __init__(self):
        self.catalog = ProductCatalog()
        self.store = Store()
        self.ledger = Ledger()
        self.current_sale = None

    def start_sale(self):
        if self.current_sale:
            print("[!] Error: Please complete or cancel the current sale first.")
            return
        self.current_sale = Sale()
        print("[*] New sale started.")

    def enter_item(self, item_id, qty):
        if not self.current_sale:
            print("[!] Error: No active sale. Please type 'start' first.")
            return
        try:
            product = self.catalog.get_product(item_id)
            self.current_sale.add_line_item(product, qty)
            self.store.update_inventory(item_id, -qty)
            print(f"[*] Added: {qty}x {product.description}. Current total: ${self.current_sale.get_total():.2f}")
        except ValueError as e:
            print(f"[!] Error: {e}. Type 'show' to see available items.")

    def enter_return_item(self, item_id, qty):
        if not self.current_sale:
            print("[!] Error: No active sale. Please type 'start' first.")
            return
        try:
            product = self.catalog.get_product(item_id)

            purchased_qty = sum(
                item.quantity for item in self.current_sale.line_items if item.product_description.item_id == item_id)

            if purchased_qty == 0:
                print(f"[!] Error: Item {item_id} not sold here. Cannot return.")
                return
            if qty > purchased_qty:
                print(f"[!] Error: Return quantity ({qty}) exceeds purchased quantity ({purchased_qty}).")
                return
            # --------------------------------------------

            self.current_sale.add_return_line_item(product, qty)
            self.store.update_inventory(item_id, qty)
            print(f"[*] Returned: {qty}x {product.description}. Current total: ${self.current_sale.get_total():.2f}")
        except ValueError as e:
            print(f"[!] Error: {e}. Type 'show' to see available items.")

    def end_sale(self, tendered_amount):
        if not self.current_sale:
            print("[!] Error: No active sale to pay.")
            return
        try:
            tendered_decimal = Decimal(str(tendered_amount))
            if tendered_decimal < self.current_sale.get_total():
                print(f"[!] Error: Insufficient cash. Short by ${self.current_sale.get_total() - tendered_decimal:.2f}")
                return
            self.current_sale.make_payment(tendered_decimal)
            ReceiptPrinter.print_receipt(self.current_sale)
            self.ledger.record_sale(self.current_sale)
            self.current_sale = None
        except Exception:
            print("[!] Error: Invalid amount format.")


# ==========================================
# 5. Interactive Console (UI)
# ==========================================
def main():
    print("=" * 50)
    print("        POS System Interactive Demo")
    print("=" * 50)
    print("Available Commands:")
    print("  [1] show               - Show the product catalog")
    print("  [2] start              - Start a new sale")
    print("  [3] buy <ID> <Qty>     - Purchase items (e.g., buy 1002 2)")
    print("  [4] ref <ID> <Qty>     - Return items (e.g., ref 1002 1)")
    print("  [5] pay <Amount>       - Pay and print receipt (e.g., pay 50)")
    print("  [6] exit               - Exit the system")
    print("=" * 50)

    pos = PosFacade()

    while True:
        try:
            user_input = input("\nPOS> ").strip().split()
            if not user_input:
                continue

            cmd = user_input[0].lower()

            if cmd == "6" or cmd == "exit":
                print("System exiting. Goodbye!")
                break
            elif cmd == "1" or cmd == "show":
                print("\n--- Available Products ---")
                for item_id, prod in pos.catalog.products.items():
                    print(f"  ID: {item_id} | {prod.description:<10} | ${prod.price:.2f}")
                print("--------------------------")
            elif cmd == "2" or cmd == "start":
                pos.start_sale()
            elif cmd == "3" or cmd == "buy":
                if len(user_input) != 3:
                    print("[!] Invalid format. Use: buy <ID> <Qty>")
                    continue
                pos.enter_item(user_input[1], int(user_input[2]))
            elif cmd == "4" or cmd == "ref":
                if len(user_input) != 3:
                    print("[!] Invalid format. Use: ref <ID> <Qty>")
                    continue
                pos.enter_return_item(user_input[1], int(user_input[2]))
            elif cmd == "5" or cmd == "pay":
                if len(user_input) != 2:
                    print("[!] Invalid format. Use: pay <Amount>")
                    continue
                pos.end_sale(user_input[1])
            else:
                print("[!] Unknown command. Please try again.")

        except KeyboardInterrupt:
            print("\nSystem terminated.")
            break
        except Exception as e:
            print(f"[!] Exception occurred: {e}")


if __name__ == "__main__":
    main()