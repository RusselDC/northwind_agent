# Building an AI Agent on the Northwind Dataset

A practical breakdown for building an AI agent on the Northwind dataset.

## Sample Questions Your Agent Should Handle

These are the kinds of natural language queries that make great agent demos:

### Sales & Orders

- "Which customers haven't ordered in the last 90 days?"
- "What are the top 5 products by revenue this year?"
- "Show me all orders that shipped late"
- "What's the average order value for customers in Germany?"

### Inventory

- "Which products are below their reorder level?"
- "Who supplies our top-selling products?"
- "What products have never been ordered?"

### Employees & Territories

- "Which sales rep has the highest revenue this quarter?"
- "Who manages customers in the Western region?"
- "How many orders did each employee handle last month?"

## Tools to Build

Think of each tool as a function your agent can call. These map directly to Northwind tables:

- `get_orders(customer_id, status, date_range)` — queries the Orders + Order Details tables
- `get_customers(country, city, active_only)` — filters the Customers table
- `get_low_stock_products(threshold)` — Products where UnitsInStock ≤ ReorderLevel
- `get_sales_summary(group_by, period)` — aggregates revenue by employee, category, or region
- `get_supplier_info(product_id, category)` — joins Products + Suppliers
- `get_employee_performance(employee_id, period)` — Orders grouped by employee
- `get_late_shipments()` — Orders where ShippedDate > RequiredDate or ShippedDate is null
- `search_products(keyword, category, min_price, max_price)` — full-text + filter on Products

## A Good Starter Architecture

1. **System prompt** — tell the agent it's a Northwind sales assistant, describe the schema briefly, and list available tools
2. **Tool router** — the agent picks which tool(s) to call based on the question
3. **SQL or ORM layer** — each tool executes a query and returns clean JSON
4. **Response formatter** — agent narrates the result in plain English + optional table

## Good Practice Challenges to Level Up

- **Multi-hop queries:** "Email all customers whose last order contained a product now out of stock" — requires chaining 3+ tools
- **Ambiguity handling:** "Show me recent orders" — agent should ask "How recent? Last 7 days, 30 days?"
- **Write actions:** add a `create_reorder_draft(supplier_id, items)` tool to practice agents that don't just read data

---

Want me to write the system prompt, the tool schemas (OpenAI/Anthropic format), or a working code scaffold for any of these?
